#!/usr/bin/env python3
"""fuzz_scan.py - campagne-runner voor de dynamische fase van SolScan.

Per doelwit:  invariant-project genereren  ->  forge invariant-run op een gepinde fork  ->  bewijs.
Een gebroken invariant = een bewezen bug.  Breekt `attacker-profit`, dan is de aanval ook winstgevend.

Gebruik:
    python -m solscan.evm.fuzz.fuzz_scan --targets targets.yaml
    python -m solscan.evm.fuzz.fuzz_scan --address 0x... --name morpho --chain eth
    python -m solscan.evm.fuzz.fuzz_scan --targets targets.yaml --gen-only
    python -m solscan.evm.fuzz.fuzz_scan --targets targets.yaml --jobs 2 --controls

Doelwitbestand (yaml of json):
    targets:
      - name: morpho-blue
        address: "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
        chain: eth
        type: auto
        invariants: [solvency, attacker-profit]
        runs: 64
        depth: 50
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "poc_output"
LOGS = REPO / "fuzz-logs"

from solscan.evm.fuzz import generator      # noqa: E402
from solscan.evm import etherscan           # noqa: E402

log = logging.getLogger("fuzz_scan")

FAIL_RE = re.compile(r"\[FAIL")
NAME_RE = re.compile(r"(invariant_\w+)")
SEED_RE = re.compile(r"\bseed:\s*(\d+)")
CANON = {re.sub(r"[^a-z0-9]", "", i.lower()): i for i in
         ("solvency", "no-free-withdraw", "conservation", "access", "k-monotonic",
          "attacker-profit", "attacker-profit-warp")}


def canonical(test: str) -> str:
    """invariant_no_free_withdraw -> no-free-withdraw (forge vervangt '-' door '_')."""
    return CANON.get(re.sub(r"[^a-z0-9]", "", test.lower()), test)


@dataclass
class Target:
    name: str
    address: str
    chain: str = "eth"
    type: str = "auto"
    invariants: list[str] | None = None
    runs: int = 64
    depth: int = 50
    actors: int = 4
    warp: bool = False
    block: int | None = None


@dataclass
class Hit:
    invariant: str
    test: str
    seed: int | None
    profitable: bool
    repro: str


@dataclass
class Outcome:
    name: str
    kind: str = ""
    block: int = 0
    project: str = ""
    generated: bool = False
    passed: bool | None = None
    hits: list[Hit] = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0


def load_targets(path: Path) -> list[Target]:
    text = path.read_text()
    data = json.loads(text) if path.suffix == ".json" else __import__("yaml").safe_load(text)
    rows = data["targets"] if isinstance(data, dict) else data
    out = []
    for r in rows:
        out.append(Target(r["name"], r["address"], r.get("chain", "eth"), r.get("type", "auto"),
                          r.get("invariants"), int(r.get("runs", 64)), int(r.get("depth", 50)),
                          int(r.get("actors", 4)), bool(r.get("warp", False)), r.get("block")))
    return out


def run_forge(project: Path, rpc: str, block: int, runs: int, depth: int,
              timeout: int, controls: bool) -> subprocess.CompletedProcess:
    cmd = ["forge", "test", "-vvvv", "--fork-url", rpc, "--fork-block-number", str(block),
           ]
    if not controls:                       # Control.t.sol zijn de negatieve controles
        cmd += ["--no-match-path", "test/Control.t.sol"]
    return subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=timeout, env={**os.environ, "FUZZ_RPC_URL": rpc})


def parse_hits(out: str, block: int, rpc: str, project: Path) -> list[Hit]:
    lines = out.splitlines()
    seed = next((int(m.group(1)) for l in lines if (m := SEED_RE.search(l))), None)
    hits, seen = [], set()
    for i, line in enumerate(lines):
        if not FAIL_RE.search(line):
            continue
        window = " ".join(lines[i:i + 4])
        found = NAME_RE.findall(window) or NAME_RE.findall(line)
        if not found:
            continue
        test = found[0]
        inv = canonical(test.removeprefix("invariant_"))
        if inv in seen:
            continue
        seen.add(inv)
        hits.append(Hit(inv, test, seed, inv.startswith("attacker-profit"),
                        f"cd {project}\nforge test --match-test {test} --fuzz-seed {seed or 0} "
                        f"--fork-url {rpc} --fork-block-number {block} -vvvv"))
    return hits


def counterexample(out: str) -> str:
    """De call-sequentie die forge als tegenvoorbeeld print, letterlijk overgenomen."""
    lines = out.splitlines()
    for i, l in enumerate(lines):
        if "[Sequence]" in l:
            block = []
            for n in lines[i + 1:i + 31]:
                if not n.strip():
                    break
                block.append(n.rstrip())
            return "\n".join(block)
    return ""


def write_poc(t: Target, meta: dict, oc: Outcome, out: str) -> None:
    d = OUT / t.name
    d.mkdir(parents=True, exist_ok=True)
    for h in oc.hits:
        (d / f"{h.invariant}.md").write_text(
            f"# {t.name} - invariant `{h.invariant}` gebroken\n\n"
            f"- doelwit: `{t.address}` ({t.chain})\n"
            f"- contracttype: {meta['type']}\n"
            f"- fork block: {meta['block']}\n"
            f"- seed: {h.seed}\n"
            f"- winstgevend: {'ja' if h.profitable else 'onbekend'}\n"
            f"- log: fuzz-logs/{t.name}.log\n\n"
            f"## Reproduceer\n```\n{h.repro}\n```\n\n"
            f"## Counterexample\n```\n{counterexample(out) or '(zie log)'}\n```\n")
    src = Path(meta["project"]) / "test" / "Invariants.t.sol"
    if src.exists():
        shutil.copy(src, d / "Invariants.t.sol")


def run_one(t: Target, a) -> Outcome:
    t0 = time.time()
    oc = Outcome(name=t.name)
    try:
        etherscan.chain_id(t.chain)                      # faal snel bij een onbekende chain
        meta = generator.generate(t.address, t.name, chain=t.chain, rpc=a.rpc, kind=t.type,
                                  invariants=t.invariants, runs=t.runs, depth=t.depth,
                                  actors=t.actors, warp=t.warp, block=t.block,
                                  fee_bps=a.fee_bps, tol=a.tol)
        oc.generated, oc.kind, oc.block, oc.project = True, meta["type"], meta["block"], meta["project"]
    except Exception as e:
        oc.error = f"genereren: {type(e).__name__}: {e}"
        oc.seconds = time.time() - t0
        return oc

    if a.gen_only:
        oc.seconds = time.time() - t0
        return oc

    LOGS.mkdir(exist_ok=True)
    try:
        r = run_forge(Path(meta["project"]), meta["rpc_url"], meta["block"],
                      t.runs, t.depth, a.timeout, a.controls)
    except subprocess.TimeoutExpired:
        oc.error = f"forge timeout na {a.timeout}s"
        oc.seconds = time.time() - t0
        return oc

    out = r.stdout + "\n" + r.stderr
    (LOGS / f"{t.name}.log").write_text(out)
    oc.passed = r.returncode == 0
    oc.hits = parse_hits(out, meta["block"], meta["rpc_url"], Path(meta["project"]))
    if not oc.hits and r.returncode != 0:
        oc.error = f"forge faalde (setUp/compile?) - zie fuzz-logs/{t.name}.log"
    if oc.hits:
        write_poc(t, meta, oc, out)
    oc.seconds = time.time() - t0
    return oc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fuzz_scan", description="SolScan dynamische campagne-runner")
    ap.add_argument("--targets", type=Path)
    ap.add_argument("--address")
    ap.add_argument("--name")
    ap.add_argument("--chain", default="eth")
    ap.add_argument("--type", default="auto")
    ap.add_argument("--invariants", help="komma-lijst, bv. solvency,attacker-profit")
    ap.add_argument("--rpc", default=None)
    ap.add_argument("--runs", type=int, default=64)
    ap.add_argument("--depth", type=int, default=50)
    ap.add_argument("--actors", type=int, default=4)
    ap.add_argument("--warp", action="store_true")
    ap.add_argument("--block", type=int, default=None)
    ap.add_argument("--fee-bps", type=int, default=100, dest="fee_bps")
    ap.add_argument("--tol", type=int, default=1000)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--gen-only", action="store_true", help="alleen projecten bouwen, niet draaien")
    ap.add_argument("--controls", action="store_true", help="draai ook test/Control.t.sol")
    ap.add_argument("--json", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO, format="%(levelname)s %(message)s")

    if not a.gen_only and not shutil.which("forge"):
        log.error("forge niet gevonden - installeer Foundry: https://getfoundry.sh")
        return 2

    if a.targets:
        targets = load_targets(a.targets)
    elif a.address:
        targets = [Target(a.name or a.address[:10], a.address, a.chain, a.type, None,
                          a.runs, a.depth, a.actors, a.warp, a.block)]
    else:
        ap.error("geef --targets of --address")

    if a.invariants:
        inv = [i.strip() for i in a.invariants.split(",") if i.strip()]
        for t in targets:
            t.invariants = t.invariants or inv

    log.info("%d doelwit(ten), jobs=%d", len(targets), a.jobs)
    outcomes = []
    with cf.ThreadPoolExecutor(max_workers=max(1, a.jobs)) as ex:
        for oc in ex.map(lambda t: run_one(t, a), targets):
            outcomes.append(oc)
            log.info("%-24s %-4s %s", oc.name, "FOUT" if oc.error else ("HIT" if oc.hits else "ok"),
                     oc.error or f"{len(oc.hits)} hit(s) in {oc.seconds:.0f}s")
            for h in oc.hits:
                log.info("    -> %s%s", h.invariant, "   (WINST)" if h.profitable else "")

    hits = [h for oc in outcomes for h in oc.hits]
    if a.json:
        a.json.write_text(json.dumps([asdict(o) for o in outcomes], indent=2))
    log.info("klaar: %d doelwit(ten), %d gebroken invariant(en)", len(outcomes), len(hits))
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())

