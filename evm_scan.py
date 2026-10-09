#!/usr/bin/env python3
"""
SolScan EVM — Slither as the engine, SolScan's triage layer on top.

Detect and explain only (CLAUDE.md): no exploits, no transactions. Read-only.

Examples
--------
  python3 evm_scan.py --address 0x... --chain eth --api-key KEY   # verified source, scan
  python3 evm_scan.py --address 0x... --chain base                # no key: Blockscout fallback
  python3 evm_scan.py path/to/contracts/                          # local folder (or foundry/hardhat project)
  python3 evm_scan.py Token.sol --json r.json --md r.md --min-severity Medium --include-info

Exit code: 1 if a GOUD finding of severity High/Critical remains, else 0.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile

from solscan.report import ScanResult, SEVERITY_ORDER
from solscan.evm import etherscan
from solscan.evm.slither_runner import EvmToolError, ensure_solc, run_slither, solc_for_source
from solscan.evm.triage import is_noise_path, triage
from solscan.evm.oracle_checks import coverage_line

FRAMEWORK_FILES = ("foundry.toml", "hardhat.config.js", "hardhat.config.ts", "truffle-config.js", "brownie-config.yaml")
SCRATCH = os.environ.get("SOLSCAN_EVM_WORKDIR") or tempfile.gettempdir()


def _sol_files(root: str) -> list[str]:
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "out", "cache", "artifacts", "lib")]
        for f in files:
            p = os.path.join(d, f)
            if f.endswith(".sol") and not is_noise_path(os.path.relpath(p, root)):
                out.append(p)
    return sorted(out)


def _entry_files(files: list[str]) -> list[str]:
    """Files that no other file imports: compiling those compiles everything once."""
    imported = set()
    for p in files:
        text = open(p, encoding="utf-8", errors="ignore").read()
        for imp in re.findall(r'import\s+(?:[^"\']*from\s+)?["\']([^"\']+)["\']', text):
            imported.add(os.path.normpath(os.path.join(os.path.dirname(p), imp)))
    roots = [p for p in files if os.path.normpath(p) not in imported]
    return roots or files


def scan_local(target: str, args) -> tuple[list, dict, list, int]:
    target = os.path.abspath(target)
    raws, access, errors = [], {}, []
    args._oracle_cov = {}
    if os.path.isdir(target) and any(os.path.exists(os.path.join(target, f)) for f in FRAMEWORK_FILES):
        # framework project: let crytic-compile drive forge/hardhat (they must be installed)
        r = run_slither(target, working_dir=target)
        args._oracle_cov.update(r.oracle_coverage)
        return r.findings, r.access, r.errors, len(_sol_files(target))
    files = _sol_files(target) if os.path.isdir(target) else [target]
    base = target if os.path.isdir(target) else os.path.dirname(target)
    for entry in _entry_files(files):
        ver = solc_for_source(open(entry, encoding="utf-8", errors="ignore").read())
        try:
            r = run_slither(entry, solc=ensure_solc(ver), working_dir=base,
                            solc_args=" ".join(etherscan.base_path_args(ver)))
        except EvmToolError as e:
            errors.append(f"{os.path.relpath(entry, base)}: {e}")
            continue
        raws += r.findings
        args._oracle_cov.update(r.oracle_coverage)
        errors += [f"{os.path.relpath(entry, base)}: {x}" for x in r.errors]
        for c, fs in r.access.items():
            access.setdefault(c, {}).update(fs)
    return raws, access, errors, len(files)


def scan_address(address: str, chain: str, api_key: str | None, args, label: str = "") -> tuple:
    src = etherscan.fetch_source(address, chain, api_key)
    notes = [f"{label}{address}: {src.contract_name} · {src.language} {src.compiler_raw or '?'} · "
             f"optimizer {'aan (' + str(src.optimizer_runs) + ' runs)' if src.optimizer else 'uit'}"
             f"{' · evm ' + src.evm_version if src.evm_version else ''} · "
             f"bron: {src.source_api} (key: {src.key_source or 'geen'}) · {len(src.files)} bestand(en)"
             + (f" · PROXY → implementation {src.implementation}" if src.is_proxy and src.implementation else "")]
    if src.language != "Solidity" or not src.compiler:
        return [], {}, [f"{address}: taal/compiler '{src.compiler_raw}' wordt (nog) niet ondersteund"], 0, src, notes
    if args.keep_sources:
        os.makedirs(args.keep_sources, exist_ok=True)
    workdir = tempfile.mkdtemp(prefix=f"evm_{address[:10]}_", dir=args.keep_sources or SCRATCH)
    main = etherscan.write_tree(src, workdir)
    solc = ensure_solc(src.compiler)  # exact version from the explorer metadata
    remaps = " ".join(src.remappings) if src.remappings else None
    r = run_slither(main, solc=solc, working_dir=workdir,
                    solc_args=etherscan.solc_args_for(src), remaps=remaps)
    args._oracle_cov = {**getattr(args, "_oracle_cov", {}), **{f"{label}{k}": v for k, v in r.oracle_coverage.items()}}
    if label:
        for f, meta in r.findings:
            f.file = f"{label}{f.file}"
    notes.append(f"{label}bronbestanden: {workdir}")
    return r.findings, r.access, r.errors, len(src.files), src, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="SolScan EVM — Slither + SolScan triage (read-only)")
    ap.add_argument("target", nargs="?", help="local folder or .sol file")
    ap.add_argument("--address", help="contract address (verified source is fetched)")
    ap.add_argument("--chain", default="eth", help="chain name or id (eth, base, arbitrum, bsc, ...)")
    ap.add_argument("--api-key", help="Etherscan API key (v2, all chains). Without key: Blockscout fallback")
    ap.add_argument("--no-proxy", action="store_true", help="do not follow proxy → implementation")
    ap.add_argument("--json")
    ap.add_argument("--md")
    ap.add_argument("--min-severity", default="Low", choices=list(SEVERITY_ORDER))
    ap.add_argument("--include-info", action="store_true", help="show Informational/Optimization findings")
    ap.add_argument("--include-deps", action="store_true", help="keep findings that are only in dependencies/tests")
    ap.add_argument("--keep-sources", help="directory to write fetched sources into (default: temp dir)")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args(argv)
    if not args.target and not args.address:
        ap.error("geef een lokale map/.sol of --address")

    notes, errors = [], []
    try:
        if args.address:
            raws, access, errs, nfiles, src, n = scan_address(args.address, args.chain, args.api_key, args)
            notes += n
            errors += errs
            name = f"{src.contract_name} ({args.address}, chain {src.chain_id})"
            impl_addr = src.implementation
            if src.is_proxy and not args.no_proxy:
                slot_impl, slot = etherscan.read_impl_slot(args.address, args.chain, args.api_key)
                if slot_impl and impl_addr and slot_impl.lower() != impl_addr.lower():
                    notes.append(f"proxy-slot {slot} → {slot_impl} wijkt af van explorer ({impl_addr}); slot gevolgd")
                    impl_addr = slot_impl
                elif slot_impl:
                    notes.append(f"implementation bevestigd via storage-slot {slot}")
                    impl_addr = slot_impl
                elif impl_addr:
                    notes.append("implementation alleen volgens explorer (geen proxy-slot gevonden of geen key)")
                src.implementation = impl_addr
            if src.is_proxy and src.implementation and not args.no_proxy:
                r2, a2, e2, nf2, impl, n2 = scan_address(src.implementation, args.chain, args.api_key, args,
                                                         label="[impl] ")
                raws += r2
                errors += e2
                notes += n2
                nfiles += nf2
                for c, fs in a2.items():
                    access.setdefault(c, {}).update(fs)
                name += f" → impl {impl.contract_name} ({src.implementation})"
                if impl.is_proxy and impl.implementation:
                    nested, nslot = etherscan.read_impl_slot(src.implementation, args.chain, args.api_key)
                    notes.append(f"[impl] explorer meldt óók 'proxy → {impl.implementation}', maar "
                                 + (f"storage-slot {nslot} bevestigt {nested}; niet automatisch gevolgd (1 niveau)"
                                    if nested else "geen proxy-slot in de implementation: waarschijnlijk een gelinkte "
                                    "library/misdetectie van de explorer — niet gevolgd"))
            target = args.address
        else:
            raws, access, errors, nfiles = scan_local(args.target, args)
            name, target = os.path.basename(os.path.abspath(args.target)), args.target
    except (EvmToolError, etherscan.ExplorerError) as e:
        print(f"[!] {e}")
        return 2

    findings, stats = triage(raws, access, include_info=args.include_info, include_deps=args.include_deps)
    cutoff = SEVERITY_ORDER[args.min_severity if not args.include_info else "Info"]
    findings = [f for f in findings if SEVERITY_ORDER.get(f.severity, 9) <= cutoff]

    result = ScanResult(target=target, program_name=name, findings=findings, files_scanned=nfiles,
                        noise_removed=stats["noise"] + stats["dupes"], errors=errors, language="solidity",
                        summary_lines=[coverage_line(getattr(args, "_oracle_cov", {}))])
    for n in notes:
        print(f"[i] {n}")
    print(f"[i] triage: {stats['noise']} dependency/test-ruis weg, {stats['dupes']} dubbel, "
          f"{stats['info_hidden']} info verborgen, {stats['lowered']} verlaagd door privilege-filter")
    for e in errors:
        print(f"[!] {e.splitlines()[0]}")
    print(result.to_console(color=not args.no_color))
    if args.json:
        open(args.json, "w").write(result.to_json())
        print(f"\n[+] JSON written to {args.json}")
    if args.md:
        open(args.md, "w").write(result.to_markdown())
        print(f"[+] Markdown written to {args.md}")
    gold_high = [f for f in findings if f.privilege.startswith("GOUD") and SEVERITY_ORDER.get(f.severity, 9) <= 1]
    return 1 if gold_high else 0


if __name__ == "__main__":
    sys.exit(main())
