"""
Deterministic triage on top of Slither (SolScan EVM layer).

1. Drop noise: findings that live only in dependencies (node_modules, lib/, @openzeppelin,
   forge-std, solmate, …) or test/mock/script code.
2. Deduplicate (same check, file, line).
3. Hide Informational/Optimization unless include_info.
4. Privilege filter (CLAUDE.md): who can reach the code a finding sits in?
     GOUD  — reachable by an external attacker / ordinary user (ungated public/external,
             or an internal function reachable from such an entry point)
     LAAG  — only admin/role-gated, initializer-only or constructor code
   LAAG findings are lowered one severity step; the original severity stays in the detail.
   Detectors that are *about* broken authorisation (tx-origin, missing access control,
   unprotected upgrade, suicidal, …) are never lowered: the "gate" is the bug.
"""
from __future__ import annotations

import re

from ..report import Finding, SEVERITY_ORDER

DEPENDENCY_RE = re.compile(
    r"(^|/)(node_modules|lib/forge-std|lib/openzeppelin[^/]*|lib/solmate|lib/solady|"
    r"@openzeppelin|openzeppelin-contracts[^/]*|forge-std|solmate|solady|@chainlink|"
    r"@uniswap|dependencies|\.deps)(/|$)|(^|/)lib/",
    re.I,
)
TEST_RE = re.compile(r"(^|/)(test|tests|mock|mocks|script|scripts)(/|$)|\.t\.sol$|\.s\.sol$|Mock\w*\.sol$", re.I)

# Detectors whose subject IS the authorisation check itself: never downgrade on privilege.
# (tx-origin: the "gate" is the bug. Detectors like arbitrary-send/suicidal ARE lowered when our
#  access map finds a real gate — Slither's own is_protected() misses e.g. OZ onlyRole/_checkRole.)
AUTHZ_DETECTORS = {"tx-origin", "solscan-missing-access-control", "solscan-unguarded-privileged-name",
                   "solscan-unprotected-sibling"}
LOWER = {"Critical": "High", "High": "Medium", "Medium": "Low", "Low": "Info", "Info": "Info"}


def is_noise_path(path: str) -> bool:
    p = path.replace("\\", "/")
    return bool(DEPENDENCY_RE.search(p) or TEST_RE.search(p))


def classify(meta: dict, access: dict) -> tuple[str, str]:
    """Return (label, reason) for one finding: GOUD / LAAG / n.v.t."""
    refs = meta.get("functions") or []
    if not refs:
        return "n.v.t.", "contract-niveau (geen functie)"
    kinds = []
    for contract, sig in refs:
        rec = (access.get(contract) or {}).get(sig)
        if rec is None:
            # inherited function referenced via the declaring contract: search all contracts
            rec = next((fs[sig] for fs in access.values() if sig in fs), None)
        if rec is None:
            kinds.append(("unknown", sig, []))
            continue
        kind = rec["kind"]
        if kind == "modifier":
            kinds.append(("modifier", sig, []))
            continue
        if kind == "internal":
            kind = "external" if rec.get("reachable_unprotected") else "internal-only"
            via = rec.get("reachable_via")
            kinds.append((kind, sig + (f" via {via}" if via else ""), rec.get("gates", [])))
        else:
            kinds.append((kind, sig, rec.get("gates", [])))

    if kinds and all(k[0] == "modifier" for k in kinds):
        return "n.v.t.", f"modifier {kinds[0][1]} (beoordeel via de functies die hem gebruiken)"
    kinds = [k for k in kinds if k[0] != "modifier"] or kinds
    ext = [k for k in kinds if k[0] in ("external", "unknown")]
    if ext:
        k = ext[0]
        if k[0] == "unknown":
            return "GOUD?", f"functie {k[1]} niet in access-map (handmatig controleren)"
        return "GOUD", f"extern bereikbaar zonder gate: {k[1]}"
    k = kinds[0]
    why = {
        "admin": "admin/rol-gated",
        "init": "alleen initializer (eenmalig)",
        "constructor": "alleen constructor",
        "internal-only": "intern, niet bereikbaar vanaf een ongegate entry point (alleen via gated functies, of dode code)",
    }.get(k[0], k[0])
    gates = f" [{'; '.join(k[2])}]" if k[2] else ""
    return "LAAG", f"{why}: {k[1]}{gates}"


def triage(raw_findings: list, access: dict, include_info: bool = False,
           include_deps: bool = False) -> tuple[list[Finding], dict]:
    stats = {"noise": 0, "dupes": 0, "info_hidden": 0, "lowered": 0}
    out, seen = [], set()
    for f, meta in raw_findings:
        files = meta.get("files") or [f.file]
        if not include_deps and files and all(is_noise_path(p) for p in files):
            stats["noise"] += 1
            continue
        key = (f.rule_id, f.file, f.line)
        if key in seen:
            stats["dupes"] += 1
            continue
        seen.add(key)

        label, reason = classify(meta, access)
        if label == "LAAG" and meta.get("check") not in AUTHZ_DETECTORS:
            if f.severity != LOWER[f.severity]:
                f.detail += f"\n[privilege-filter: verlaagd van {f.severity} → {LOWER[f.severity]}]"
                f.severity = LOWER[f.severity]
                stats["lowered"] += 1
        elif label == "LAAG":
            reason += " — niet verlaagd: de detector gaat over de autorisatie zelf"
        f.privilege = f"{label} ({reason})"

        if f.severity == "Info" and not include_info:
            stats["info_hidden"] += 1
            continue
        out.append(f)

    # GOUD first, then severity
    rank = {"GOUD": 0, "GOUD?": 1, "n.v.t.": 2, "LAAG": 3}
    out.sort(key=lambda x: (rank.get(x.privilege.split(" ")[0], 9), SEVERITY_ORDER.get(x.severity, 9), x.file, x.line))
    return out, stats
