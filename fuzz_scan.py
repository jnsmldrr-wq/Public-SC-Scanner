#!/usr/bin/env python3
"""SolScan invariant fuzzing (Foundry) — stress a LIVE contract on a LOCAL mainnet fork.

    python3 fuzz_scan.py --address 0x... --name fira-usl                    # auto type + default invariants
    python3 fuzz_scan.py --address 0x... --name x --invariants solvency,no-free-withdraw --runs 64 --depth 50
    python3 fuzz_scan.py --address 0x... --name x --warp                    # let time pass (interest, liquidations)
    python3 fuzz_scan.py --rerun x                                          # rerun an existing project (keeps Custom.t.sol)

Read-only towards the chain: the fork is local (forge), actors are local test addresses funded with
`deal`, nothing is signed or broadcast. A broken invariant + Foundry's shrunk call sequence is the proof;
no exploit transaction is produced.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solscan.evm import etherscan                      # noqa: E402
from solscan.evm.fuzz import detect, generator         # noqa: E402
from solscan.evm.fuzz.chain import describe_rpc, fork_upstreams, rpc_url  # noqa: E402
import socket  # noqa: E402
import urllib.request  # noqa: E402

REPORTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fuzz-reports")

FIX_HINT = {
    "SOLVENCY": "Zorg dat elke uitbetaling (withdraw/borrow/redeem) tegen de werkelijk aanwezige assets wordt "
                "gecontroleerd en dat interne boekhouding (totalSupply/totalAssets/shares) in dezelfde stap wordt "
                "bijgewerkt als de token-overdracht; rond in het voordeel van het protocol af.",
    "NO-FREE-WITHDRAW": "Controleer de share↔asset-omrekening en afronding (deposit/mint naar beneden, withdraw/redeem "
                        "naar boven afronden voor de gebruiker) en dat een positie na opname correct wordt verlaagd.",
    "CONSERVATION": "Een token-overdracht en de interne boekhouding lopen uit elkaar: controleer fee-on-transfer/"
                    "rebasing-aannames en dat elke transfer precies één keer wordt geboekt.",
    "ACCESS": "Voeg de ontbrekende autorisatiecontrole (onlyOwner/onlyRole/msg.sender-check) toe aan de genoemde functie.",
    "K-MONOTONIC": "De invariant-check van de pair (k na swap >= k vóór swap, inclusief fee) wordt omzeild; "
                   "controleer de fee-correctie in swap() en de reserves-update.",
}


INFRA_MARKERS = ("failed to set up invariant testing environment", "database error", "http request failed",
                 "could not instantiate forked environment", "operation timed out", "error sending request")


def is_infra(reason: str) -> bool:
    r = (reason or "").lower()
    return any(m in r for m in INFRA_MARKERS)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LocalFork:
    """anvil as a local caching fork in front of the public RPC(s): retries, timeouts, load spreading.
    Pinned to the campaign block; nothing is ever sent upstream except read requests."""
    def __init__(self, upstreams: list[str], block: int, log_dir: str = "."):
        self.upstreams, self.block, self.proc = upstreams, block, None
        self.log = os.path.join(log_dir, "anvil.log")
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        for attempt in range(3):    # a flaky upstream can break anvil's genesis requests: retry the start
            try:
                return self._start()
            except RuntimeError:
                if attempt == 2:
                    raise
                self.port = _free_port()
                self.url = f"http://127.0.0.1:{self.port}"
                time.sleep(5)

    def _start(self):
        anvil = shutil.which("anvil") or os.path.expanduser("~/.foundry/bin/anvil")
        cmd = [anvil, "--port", str(self.port), "--fork-block-number", str(self.block),
               "--retries", "25", "--timeout", "120000", "--fork-retry-backoff", "1500", "--no-rate-limit"]
        for u in self.upstreams:
            cmd += ["--fork-url", u]
        self.logf = open(self.log, "w")
        self.proc = subprocess.Popen(cmd, stdout=self.logf, stderr=subprocess.STDOUT)
        body = b'{"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}'
        for _ in range(120):
            if self.proc.poll() is not None:
                break
            try:
                req = urllib.request.Request(self.url, body, {"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=2).read()
                return self
            except Exception:
                time.sleep(1)
        self.__exit__()
        raise RuntimeError(f"anvil-fork start niet — zie {self.log}")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def forge_bin() -> str:
    p = shutil.which("forge") or os.path.expanduser("~/.foundry/bin/forge")
    if not os.path.exists(p):
        sys.exit("forge niet gevonden — installeer Foundry (zie CLAUDE.md, sectie invariant-fuzzing)")
    return p


def run_forge(project: str, rpc: str, warp: bool, timeout: int) -> tuple[dict, str, float]:
    env = dict(os.environ, FUZZ_RPC_URL=rpc, FUZZ_WARP="true" if warp else "false")
    cov = os.path.join(project, "coverage.csv")
    if os.path.exists(cov):
        os.remove(cov)
    cmd = [forge_bin(), "test", "--match-contract", "FuzzCustom", "--json", "-vv"]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        took = time.time() - t0
        fake = {"timeout": {"test_results": {"invariant_campaign()": {
            "status": "Failure", "reason": f"operation timed out: campagne overschreed --timeout {timeout}s",
            "invariant_predicate_results": [{"name": "campagne", "status": "Failure"}]}}}}
        return fake, f"forge-tijdslimiet ({timeout}s) overschreden", took
    took = time.time() - t0
    out = r.stdout.strip()
    data = {}
    start = out.find("{")
    if start >= 0:
        try:
            data = json.loads(out[start:])
        except json.JSONDecodeError:
            data = {}
    return data, (r.stderr or "") + ("" if data else out), took


def run_controls(project: str, rpc: str) -> dict:
    """Positive controls (Control.t.sol): each must PASS, i.e. its invariant fired on corrupted state."""
    env = dict(os.environ, FUZZ_RPC_URL=rpc, FUZZ_WARP="false")
    r = subprocess.run([forge_bin(), "test", "--match-contract", "FuzzControl", "--match-test", "test_control", "--json"],
                       cwd=project, env=env, capture_output=True, text=True, timeout=1200)
    out = r.stdout[r.stdout.find("{"):] if "{" in r.stdout else "{}"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {}
    res = {}
    for suite in data.values():
        for test, t in (suite.get("test_results") or {}).items():
            res[test.split("(")[0]] = str(t.get("status", "")).lower() == "success"
    return res


def _kind(res: dict) -> dict:
    k = res.get("kind") or {}
    return k.get("Invariant") or k.get("invariant") or {}


def _sequence(res: dict) -> list[dict]:
    ce = res.get("counterexample") or {}
    seq = ce.get("Sequence") or ce.get("sequence") or []
    return seq if isinstance(seq, list) else []


def parse(data: dict) -> list[dict]:
    """One row per invariant. Foundry >= 1.x runs all invariants of a contract in one shared campaign:
    status per predicate is in invariant_predicate_results, runs/calls and the counterexample are shared."""
    rows = []
    for suite in data.values():
        for test, res in (suite.get("test_results") or {}).items():
            if not test.startswith("invariant_"):
                continue
            k = _kind(res)
            seq = _sequence(res)
            preds = res.get("invariant_predicate_results") or [{"name": test.split("(")[0], "status": res.get("status")}]
            for p in preds:
                failed = str(p.get("status", "")).lower() not in ("success", "pass")
                why = (p.get("reason") or res.get("reason") or "") if failed else ""
                rows.append({
                    "test": p.get("name", test),
                    "status": "INFRA-FOUT" if failed and is_infra(why) else p.get("status", "?"),
                    "reason": (p.get("reason") or (res.get("reason") if failed else "") or ""),
                    "runs": k.get("runs"), "calls": k.get("calls"), "reverts": k.get("reverts"),
                    "sequence": seq if failed else [],
                    "metrics": k.get("metrics") or {},
                })
    return rows


def coverage(project: str) -> dict:
    """Sum of (ok, tried) per action over all runs, from afterInvariant()'s coverage.csv."""
    tot = {}
    path = os.path.join(project, "coverage.csv")
    if not os.path.exists(path):
        return tot
    for line in open(path):
        parts = line.strip().split(",", 3)
        if len(parts) >= 3 and parts[1].isdigit():
            ok, tried, why = tot.get(parts[0], (0, 0, ""))
            tot[parts[0]] = (ok + int(parts[1]), tried + int(parts[2]), (parts[3] if len(parts) > 3 and parts[3] else why))
    return tot


def stored_sequence(project: str, test: str) -> list[dict]:
    """Foundry persists the shrunk counterexample in cache/invariant/failures/<contract>/invariants/<test>."""
    name = test.split("(")[0]
    for root, _, files in os.walk(os.path.join(project, "cache", "invariant", "failures")):
        if name in files:
            try:
                return json.load(open(os.path.join(root, name))).get("call_sequence") or []
            except (OSError, json.JSONDecodeError):
                return []
    return []


def _call_line(c: dict) -> str:
    fn = c.get("func_name") or (c.get("signature") or "?").split("(")[0]
    args = c.get("args") or c.get("raw_args") or ""
    sender = c.get("sender") or ""
    return f"`{fn}({args})`" + (f" — sender {sender}" if sender else "")


def _broken_rule(reason: str) -> str:
    for key in FIX_HINT:
        if key in reason.upper():
            return key
    return ""


def write_report(meta: dict, rows: list[dict], took: float, stderr: str) -> str:
    os.makedirs(REPORTS, exist_ok=True)
    path = os.path.join(REPORTS, f"{meta['name']}.md")
    broken = [r for r in rows if r["status"].lower() not in ("success", "pass", "infra-fout")]
    infra = [r for r in rows if r["status"] == "INFRA-FOUT"]
    total_calls = max([r["calls"] or 0 for r in rows] or [0])
    cov = coverage(meta["project"])
    L = [f"# Invariant-fuzzing — {meta['name']}", "",
         f"- Doel: `{meta['address']}` ({meta.get('contract') or '?'}, chain {meta['chain_id']})"
         + (f" — {meta['proxy']}" if meta.get("proxy") else ""),
         f"- Type: **{meta['type']}** · invarianten: {', '.join(meta['invariants'])}",
         f"- Fork: lokale anvil-fork, blok {meta['block']}, upstream {', '.join(meta.get('upstreams') or [describe_rpc(meta['rpc_url'])])} · actoren: {meta['actors']} lokale testadressen "
         f"(+ eventuele gesimuleerde whitelist-rol) · warp: {'aan' if meta['warp'] else 'uit'}",
         f"- Campagne: runs={meta['runs']} × depth={meta['depth']} (één gedeelde campagne; alle invarianten worden na élke call gecontroleerd) · {total_calls} fuzz-calls · {took:.0f}s",
         ]
    if meta.get("markets"):
        L.append(f"- Markten ({len(meta['markets'])}): " + "; ".join(
            f"`{m['id'][:10]}…` loan {m.get('loanToken','?')[:10]}… / coll {m.get('collateralToken','?')[:10]}…" for m in meta["markets"]))
    if meta.get("privileged"):
        L.append(f"- ACCESS-kandidaten (gated volgens bron): {', '.join(meta['privileged'])}")
    if meta.get("controls"):
        L.append("- Positieve controles (invariant vuurt bij opzettelijk gecorrumpeerde fork-state): " + ", ".join(
            f"{k.replace('test_control_', '')} {'✓' if v else '✗ (check werkt niet — resultaat onbetrouwbaar)'}"
            for k, v in meta["controls"].items()))
    L += ["", "## Resultaat", ""]
    if not rows:
        L += ["Forge leverde geen invariant-resultaten op (compile- of fork-fout). Uitvoer:", "", "```",
              stderr[-3000:], "```"]
    elif infra and not broken:
        L += ["**Campagne NIET voltooid — infrastructuurfout (fork/RPC), geen bevinding.** Opnieuw draaien met "
              "`--rerun`; zie de reden hieronder.", "", f"`{infra[0]['reason'][:300]}`"]
    elif not broken:
        L.append(f"**Geen invariant-schending gevonden in {meta['runs']} runs** ({total_calls} fuzz-calls, "
                 f"{len(rows)} invarianten na elke call gecontroleerd).")
    else:
        L.append(f"**{len(broken)} invariant(en) gebroken.**")
    L += ["", "| invariant | status | runs | calls | reverts |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['test']} | {r['status']} | {r['runs']} | {r['calls']} | {r['reverts']} |")
    for r in broken:
        if not r["sequence"]:
            r["sequence"] = stored_sequence(meta["project"], r["test"])
        rule = _broken_rule(r["reason"])
        L += ["", f"### Gebroken: {r['test']}", "", f"- Reden (assert): `{r['reason'][:400]}`",
              "- Reproducerende call-sequence (door Foundry gekrompen, in volgorde):"]
        for i, c in enumerate(r["sequence"], 1):
            L.append(f"  {i}. {_call_line(c)}")
        last = r["sequence"][-1] if r["sequence"] else {}
        if last:
            L.append(f"- Functie waarin de regel brak: laatste handler-actie `{last.get('func_name') or '?'}` "
                     "(de handler roept de gelijknamige doelfunctie aan).")
        if rule:
            L.append(f"- Fix-richting: {FIX_HINT[rule]}")
        L.append("- Reproduceren: `python3 fuzz_scan.py --rerun " + meta["name"] + "` (zelfde fork-blok; Foundry bewaart "
                 "de failure in `fuzz-work/" + meta["name"] + "/cache/invariant` en speelt die eerst opnieuw af).")
    if cov:
        L += ["", "## Dekking (opgeteld over alle runs)", "", "| handler-actie | geslaagd | geprobeerd | laatste revert-reden |", "|---|---|---|---|"]
        for name, (ok, tried, why) in sorted(cov.items()):
            L.append(f"| {name} | {ok} | {tried} | {why or '—'} |")
        dead = [n for n, (ok, _, _) in cov.items() if ok == 0]
        if dead:
            L.append("")
            L.append(f"Niet één keer geslaagd: {', '.join(sorted(dead))} — die paden zijn in deze campagne feitelijk niet getest"
                     + (" (tryPrivileged hoort altijd te falen: dat is de ACCESS-check)." if dead == ["tryPrivileged"] else "."))
    L += ["", "## Beperkingen", "",
          "- De fuzzer test alleen de acties in de handler en de gekozen invarianten; \"geen schending\" is geen bewijs van afwezigheid van bugs.",
          "- Acties die (bijna) altijd reverten (zie dekking) zijn feitelijk niet getest — pas dan de handler of het fork-blok aan.",
          "- Alleen lokale fork; er is niets op mainnet uitgevoerd of ondertekend."]
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser(description="SolScan invariant fuzzing (Foundry, lokale mainnet-fork)")
    ap.add_argument("--address")
    ap.add_argument("--name")
    ap.add_argument("--rerun", help="bestaand project opnieuw draaien (fuzz-work/<naam>)")
    ap.add_argument("--chain", default="eth")
    ap.add_argument("--rpc", help="JSON-RPC voor de fork (anders ETH_RPC_URL of een publieke node)")
    ap.add_argument("--type", default="auto", choices=["auto", "lender", "vault", "amm", "token", "wrapper", "mintredeem", "queuevault", "sir", "locktoken", "aavebook"])
    ap.add_argument("--invariants", help="komma-lijst: " + ",".join(sorted(detect.ALL_INVARIANTS)))
    ap.add_argument("--privileged", help="komma-lijst functienamen voor de ACCESS-invariant (overschrijft de heuristiek)")
    ap.add_argument("--actors", type=int, default=4)
    ap.add_argument("--runs", type=int, help="runs per campagne (standaard 32; bij --rerun: overschrijft het project)")
    ap.add_argument("--depth", type=int, help="calls per run (standaard 40; bij --rerun: overschrijft het project)")
    ap.add_argument("--block", type=int)
    ap.add_argument("--fund", type=float, default=1e24, help="startsaldo per actor per token (raw units)")
    ap.add_argument("--fee-bps", type=int, default=100, help="aangenomen swap-fee voor amm (conservatief)")
    ap.add_argument("--warp", action="store_true", help="tijd laten verstrijken (rente, liquidaties); schakelt NO-FREE-WITHDRAW uit")
    ap.add_argument("--timeout", type=int, default=3600)
    a = ap.parse_args()

    if a.rerun:
        proj = os.path.join(generator.WORK, a.rerun)
        meta = json.load(open(os.path.join(proj, "target.json")))
        meta["rpc_url"] = rpc_url(meta.get("chain_id", 1), a.rpc)
        meta["project"] = proj
        if a.runs or a.depth:   # resize the campaign of an existing project
            meta["runs"], meta["depth"] = a.runs or meta["runs"], a.depth or meta["depth"]
            with open(os.path.join(proj, "foundry.toml"), "w") as f:
                f.write(generator.foundry_toml(meta["runs"], meta["depth"]))
            with open(os.path.join(proj, "target.json"), "w") as f:
                json.dump({k: v for k, v in meta.items() if k not in ("rpc_url", "project")}, f, indent=1)
    else:
        if not (a.address and a.name):
            ap.error("--address en --name zijn verplicht (of --rerun <naam>)")
        try:
            meta = generator.generate(
                a.address, a.name, chain=a.chain, rpc=a.rpc, kind=a.type,
                invariants=[x.strip() for x in a.invariants.split(",")] if a.invariants else None,
                actors=a.actors, fund=int(a.fund), runs=a.runs or 32, depth=a.depth or 40, block=a.block,
                warp=a.warp, fee_bps=a.fee_bps,
                privileged=[x.strip() for x in a.privileged.split(",")] if a.privileged else None)
        except (generator.GenError, etherscan.ExplorerError) as e:
            sys.exit(f"[!] {e}")
    print(f"[i] doel {meta['address']} ({meta.get('contract')}) type={meta['type']} blok={meta['block']} "
          f"invarianten={','.join(meta['invariants'])} {meta.get('proxy') or ''}")
    print(f"[i] project: {meta['project']} · fork via {describe_rpc(meta['rpc_url'])} · runs={meta['runs']} depth={meta['depth']}")
    ups = fork_upstreams(meta.get("chain_id", 1), a.rpc)
    meta["rpc_url"] = ups[0]
    meta["upstreams"] = [describe_rpc(u) for u in ups]
    print(f"[i] lokale anvil-fork op blok {meta['block']} → upstream: {', '.join(meta['upstreams'])}")
    with LocalFork(ups, meta["block"], meta["project"]) as fork:
        meta["controls"] = run_controls(meta["project"], fork.url)
        for name, ok in meta["controls"].items():
            print(f"    controle {name:30} {'OK — invariant vuurt bij gemanipuleerde state' if ok else 'MISLUKT'}")
        if meta["controls"] and not all(meta["controls"].values()):
            print("[!] een positieve controle faalt — een schone uitkomst zou niets betekenen; campagne overgeslagen")
            data, stderr, took = {}, "positieve controle faalde", 0.0
        else:
            attempts = 0
            while True:     # an infra error (RPC/fork) is retried; forge's disk cache keeps the state fetched so far
                attempts += 1
                data, stderr, took = run_forge(meta["project"], fork.url, meta["warp"], a.timeout)
                rows_try = parse(data)
                if attempts >= 2 or not (rows_try and all(r["status"] == "INFRA-FOUT" for r in rows_try)):
                    break
                print(f"[!] infrastructuurfout (poging {attempts}) — opnieuw met warme cache")
            meta["attempts"] = attempts
    rows = parse(data)
    path = write_report(meta, rows, took, stderr)
    for r in rows:
        print(f"    {r['status']:8} {r['test']:32} runs={r['runs']} calls={r['calls']} reverts={r['reverts']}"
              + (f"  ← {r['reason'][:120]}" if r['status'].lower() not in ('success', 'pass') else ""))
    if not rows:
        print(stderr[-2500:])
    print(f"[+] rapport: {path}")
    if any(r["status"] == "INFRA-FOUT" for r in rows):
        sys.exit(2)
    sys.exit(1 if any(r["status"].lower() not in ("success", "pass") for r in rows) else (2 if not rows else 0))


if __name__ == "__main__":
    main()
