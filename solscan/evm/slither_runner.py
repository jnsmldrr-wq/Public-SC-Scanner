"""
Run Slither (via the isolated worker in .venv-evm) and map its output to SolScan Findings.

The rest of SolScan runs on any Python. Slither needs a newer interpreter than the
system Python 3.12.0 (crytic-compile excludes 3.12.0), so it lives in `.venv-evm`
(Homebrew Python 3.13) and is called as a subprocess. Override the locations with
SOLSCAN_EVM_PYTHON / SOLSCAN_SOLC_SELECT if needed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field

from ..report import Finding
from . import oracle_checks

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slither_worker.py")

IMPACT_TO_SEVERITY = {
    "High": "High", "Medium": "Medium", "Low": "Low",
    "Informational": "Info", "Optimization": "Info",
}


class EvmToolError(RuntimeError):
    pass


def evm_python() -> str:
    cand = [os.environ.get("SOLSCAN_EVM_PYTHON"),
            os.path.join(ROOT, ".venv-evm", "bin", "python")]
    for c in cand:
        if c and os.path.exists(c):
            return c
    raise EvmToolError("EVM-venv niet gevonden. Maak 'm aan: "
                       "python3.13 -m venv .venv-evm && .venv-evm/bin/pip install slither-analyzer solc-select")


def _solc_select() -> str:
    cand = [os.environ.get("SOLSCAN_SOLC_SELECT"),
            os.path.join(ROOT, ".venv-evm", "bin", "solc-select"),
            shutil.which("solc-select")]
    for c in cand:
        if c and os.path.exists(c):
            return c
    raise EvmToolError("solc-select niet gevonden (installeer in .venv-evm)")


def ensure_solc(version: str) -> str:
    """Install (if needed) and return the path of a specific solc version, e.g. '0.8.24'."""
    path = os.path.expanduser(f"~/.solc-select/artifacts/solc-{version}/solc-{version}")
    if os.path.exists(path):
        return path
    env = dict(os.environ)
    if os.path.exists("/etc/ssl/cert.pem"):
        env.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")
    r = subprocess.run([_solc_select(), "install", version], capture_output=True, text=True, env=env)
    if not os.path.exists(path):
        raise EvmToolError(f"solc {version} kon niet geïnstalleerd worden: {r.stderr.strip() or r.stdout.strip()}")
    return path


def solc_for_source(text: str, default: str = "0.8.24") -> str:
    """Pick a solc version for local code from its `pragma solidity` line (best effort)."""
    import re
    m = re.search(r"pragma\s+solidity\s+([^;]+);", text)
    if not m:
        return default
    spec = m.group(1)
    exact = re.search(r"(?<![>^~])=?\s*(\d+\.\d+\.\d+)", spec)
    if re.fullmatch(r"\s*=?\s*\d+\.\d+\.\d+\s*", spec) and exact:
        return exact.group(1)
    # caret/range: use the newest patch we know for that minor, else the default
    minor = re.search(r"(\d+)\.(\d+)\.\d+", spec)
    if minor and (minor.group(1), minor.group(2)) != ("0", "8"):
        return {"7": "0.7.6", "6": "0.6.12", "5": "0.5.17", "4": "0.4.26"}.get(minor.group(2), default)
    return default


@dataclass
class EvmRaw:
    findings: list = field(default_factory=list)   # list[(Finding, meta)]
    access: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    oracle_coverage: dict = field(default_factory=dict)


def _source_line(path: str, line: int) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            lines = fh.read().splitlines()
        return lines[line - 1].strip() if 0 < line <= len(lines) else ""
    except OSError:
        return ""


def _function_refs(elements: list) -> list:
    """(contract, signature) pairs for every function an element belongs to."""
    refs = []
    for el in elements:
        tsf = el.get("type_specific_fields") or {}
        if el.get("type") == "function":
            parent = (tsf.get("parent") or {}).get("name")
            refs.append((parent, tsf.get("signature") or el.get("name")))
        else:
            p = tsf.get("parent") or {}
            if p.get("type") == "function":
                pp = ((p.get("type_specific_fields") or {}).get("parent") or {}).get("name")
                refs.append((pp, (p.get("type_specific_fields") or {}).get("signature") or p.get("name")))
    return [r for r in refs if r[0] and r[1]]


def run_slither(target: str, solc: str | None = None, working_dir: str | None = None,
                solc_args: str | None = None, remaps: str | None = None,
                timeout: int = 900) -> EvmRaw:
    # Pass the target RELATIVE to the working dir: solc's --base-path/--allow-paths otherwise
    # reject imports when the absolute path goes through a symlink (macOS /var -> /private/var).
    if working_dir:
        working_dir = os.path.realpath(working_dir)
        real_target = os.path.realpath(target)
        if real_target.startswith(working_dir + os.sep) or real_target == working_dir:
            target = os.path.relpath(real_target, working_dir) or "."
    cmd = [evm_python(), WORKER, target]
    if solc:
        cmd += ["--solc", solc]
    if working_dir:
        cmd += ["--solc-working-dir", working_dir]
    if solc_args:
        cmd += ["--solc-args", solc_args]
    if remaps:
        cmd += ["--solc-remaps", remaps]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          cwd=working_dir or None)
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        raise EvmToolError(f"Slither-worker gaf geen JSON (exit {proc.returncode}): "
                           f"{(proc.stderr or proc.stdout)[-1500:]}")

    raw = EvmRaw(access=data.get("access", {}), errors=list(data.get("errors", [])))
    meta_det = data.get("detectors", {})
    base = working_dir or os.path.dirname(os.path.abspath(target))

    for r in data.get("results", []):
        els = r.get("elements") or []
        primary = next((e for e in els if e.get("source_mapping", {}).get("lines")), None)
        sm = (primary or {}).get("source_mapping", {})
        rel = sm.get("filename_relative") or sm.get("filename_short") or ""
        absf = sm.get("filename_absolute") or os.path.join(base, rel)
        line = (sm.get("lines") or [0])[0]
        det = meta_det.get(r.get("check"), {})
        f = Finding(
            rule_id=f"EVM-{r.get('check')}",
            title=det.get("title") or r.get("check", ""),
            severity=IMPACT_TO_SEVERITY.get(r.get("impact"), "Info"),
            confidence=r.get("confidence", "Medium") if r.get("confidence") in ("High", "Medium", "Low") else "Medium",
            file=rel, line=line,
            snippet=_source_line(absf, line),
            detail=(r.get("description") or "").strip(),
            recommendation=(det.get("recommendation") or "").strip() + (f" ({det['wiki']})" if det.get("wiki") else ""),
        )
        meta = {
            "check": r.get("check"),
            "functions": _function_refs(els),
            "files": sorted({(e.get("source_mapping") or {}).get("filename_relative") or "" for e in els} - {""}),
        }
        raw.findings.append((f, meta))

    for c in data.get("custom", []):
        rel = c.get("file") or ""
        absf = rel if os.path.isabs(rel) else os.path.join(base, rel)
        title = {"solscan-missing-access-control": "Ontbrekende access control op autoriteits-state",
                 "solscan-unprotected-sibling": "Ongegate functie naast gegate functies (delegeert rechten / approval / call naar caller-adres)",
                 }.get(c["check"], "Beheerdersfunctie zonder access-gate (controleren)")
        f = Finding(
            rule_id=f"EVM-{c['check']}",
            title=title,
            severity=c.get("impact", "Medium"),
            confidence=c.get("confidence", "Low"),
            file=os.path.relpath(absf, base) if os.path.isabs(absf) else rel,
            line=c.get("line", 0),
            snippet=_source_line(absf, c.get("line", 0)),
            detail=c.get("description", ""),
            recommendation="Voeg een access-gate toe (bijv. onlyOwner / onlyRole) of maak de functie internal.",
        )
        raw.findings.append((f, {"check": c["check"], "functions": [(c["contract"], c["function"])],
                                 "files": [f.file]}))
    # defensive oracle-safety checks (own layer); regex fallback when Slither produced no function data
    functions = data.get("functions") or []
    if functions:
        ofs, cov = oracle_checks.check_functions(functions)
    else:
        ofs, cov = oracle_checks.check_sources(base)
    raw.findings.extend(ofs)
    raw.oracle_coverage = cov
    return raw
