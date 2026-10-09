# SolScan — handover

A handover for a developer who has **never seen this project** and must run and
extend it independently, without access to the original machine or chat session.

Read this top to bottom once; then §Setup and §Running are the day-to-day
reference. Everything here is **detect-and-explain-only, read-only, public source
only** — that discipline is a hard product rule, not a style choice (see
[CLAUDE.md](CLAUDE.md) "Hard rules"). Never write an exploit or a transaction;
never test against mainnet (the fuzzer uses a *local* fork).

---

## 1. What SolScan is

SolScan is a **defensive vulnerability scanner for DeFi**, sold to small protocols
that cannot afford a full audit. It finds weaknesses and reports them via
responsible disclosure so they get fixed before exploitation. Three engines:

1. **Solana / Anchor static scanner** — custom Rust-source detectors (`scan.py`).
2. **EVM / Solidity static scanner** — Slither as the engine + SolScan's own
   triage, privilege-filter and oracle-safety layer (`evm_scan.py`).
3. **EVM invariant fuzzer** — Foundry invariant campaigns against a *live* contract
   on a *local* mainnet fork (`fuzz_scan.py`).

The deliverable is never a raw tool dump. It is a **triaged** short list of the
findings that survive judgment (the privilege filter first of all), each written
as "there is a bug here and here is why", with a fix direction.

---

## 2. Where it lives / repository status

- Clone the repo anywhere; all paths in this document are relative to the repo root.
- It is now a **git repository** (initialised during this handover; see the first
  commit). A fresh `git clone` + this file is enough to set up — see §8.
- **Secrets are not in the repo.** The Etherscan key lives only in the environment
  (`ETHERSCAN_API_KEY`). Copy [`.env.example`](.env.example) → `.env` and fill it,
  or export the vars in your shell. `.gitignore` excludes `.env`, venvs, caches,
  cloned target repos, compiled `*.so`, and large generated scan outputs.

---

## 3. Repository tree (tracked files, what each does)

```
solscan 2/
├── CLAUDE.md                  Operating manual + hard rules + triage recipe (READ FIRST, authoritative)
├── README.md / TUTORIAL.md / SETUP-CLAUDE-CODE.md   Intro / walkthrough / Claude-Code setup notes
├── HANDOVER.md                This file
├── .env.example               Env-var template (no real keys)
├── .gitignore
│
│  ── Solana static scanner ──────────────────────────────────────────────
├── scan.py                    CLI: scan a local Anchor program folder or --github <repo>
├── livecheck.py               STEP 0: is a Solana program actually live on mainnet? (getAccountInfo)
├── sourcecheck.py             STEP 0: does a repo hold the REAL logic or only a shell / private source?
│
│  ── EVM static scanner ────────────────────────────────────────────────
├── evm_scan.py                CLI: scan a verified EVM contract (--address) or local folder
│
│  ── EVM invariant fuzzer ──────────────────────────────────────────────
├── fuzz_scan.py               CLI: generate + run a Foundry invariant campaign on a local fork
│
│  ── shared python package ─────────────────────────────────────────────
├── solscan/
│   ├── scanner.py             Orchestration: run every Solana detector over a file/dir/repo
│   ├── detectors.py           Known-class Solana/Anchor detectors (SOL-AUTH/OWNER/TYPE/CPI/PDA)
│   ├── arithmetic.py          Arithmetic / rounding / precision detectors (SOL-ARITH-1xx)
│   ├── semantic.py            Type-B semantic / context-sensitive Solana detectors
│   ├── rustsrc.py             Lightweight brace-matched Rust/Anchor source parser (not a full parser)
│   ├── securitytxt.py         Extract disclosure contact (Neodyme security_txt!) + Cargo overflow-checks
│   ├── report.py              Finding model + console / markdown / JSON rendering
│   └── evm/
│       ├── etherscan.py       Fetch verified source per address (Etherscan v2; Blockscout fallback)
│       ├── slither_runner.py  Run the Slither worker (in .venv-evm) and map output → SolScan Findings
│       ├── slither_worker.py  Runs INSIDE .venv-evm (py3.13): Slither + access-map + custom detectors
│       ├── triage.py          Deterministic triage: drop dep/test noise, dedupe, privilege-filter
│       ├── oracle_checks.py   Oracle-safety checks (spot/freshness/single-source) — "verify manually"
│       └── fuzz/
│           ├── chain.py       Read-only chain access (ABI, eth_call, logs, block, getCode) — never a tx
│           ├── detect.py      Classify a contract from its ABI → template type + privileged fns
│           ├── generator.py   Generate a Foundry invariant project per target (fuzz-work/<name>/)
│           └── templates.py   Solidity handler/invariant/control templates (10 types)
│
│  ── tests (tracked; the reproducible proofs) ──────────────────────────
├── tests/evm/
│   ├── test_privilege.py + PrivilegeCases.sol       privilege-filter regression
│   ├── test_sibling.py   + sibling/SiblingCases.sol unprotected-sibling detector
│   ├── test_oracle.py    + oracle/*.sol             oracle-safety checks (Liquity PriceFeed = 0)
│   ├── test_oracle_guard.py + oracle_guard/*.sol    fuzz module 3 (forced-oracle) positive control
│   ├── test_attacker_profit.py + attacker/*.sol     fuzz module 1 (ATTACKER-PROFIT) positive control + free-mint reconstruction
│   ├── test_time.py      + time/TimeCases.sol        fuzz module 4 (time/warp) positive control
│   └── test_fuzz_gen.py                              generator render regression
│
│  ── EVM Ethereum inventory (candidate selection) ──────────────────────
├── shortlist/evm-eth/
│   ├── inventory.py           Build/resume the inventory: own-code vs fork/standard, + on-chain live flag
│   ├── make_table.py          Render results.json → evm-inventaris-ethereum.md
│   ├── list.json              Input: 278 Ethereum protocols ($1M–$20M TVL) from DeFiLlama
│   ├── adapter_addrs.json     Input: candidate addresses per protocol (from DeFiLlama adapters)
│   ├── results.json           Output: classification + live flag per protocol (278/278, A–Z complete)
│   ├── llama.json             Raw DeFiLlama protocol dump (input)
│   └── run.log / todo_remaining.json   Run progress / leftover queue
│
│  ── bookkeeping + deliverables (tracked markdown) ─────────────────────
├── evm-inventaris-ethereum.md Generated inventory table (278 protocols; 108 own-code)
├── scan-voortgang.md          EVM scan bookkeeping: one row per protocol, batch + status + triage link
├── fuzz-voortgang.md          Fuzz bookkeeping: one row per campaign (addr, invariants, runs, result)
├── modules-status.md          Fuzz-harness extension modules (1 ATTACKER-PROFIT, 3 oracle, 4 time) + benchmarks
├── fuzz-kandidaten.md / fuzz-kandidaten-nieuw.md   Fuzz target shortlists
├── shortlist*.md              Earlier Solana candidate shortlists
├── brickken-oracle-onderbouwing.md                  Supporting note for the Brickken oracle finding
└── triage-*.md                Curated per-target triage deliverables (aave-v1, angle, opyn-gamma,
                               byreal, larix, orderly, quarry, starke, privacycash, payy-network, …)
```

**Not tracked** (git-ignored, recreated on demand — see §8):
`.venv-evm/`, `fuzz-work/`, `evm-reports/`, `fuzz-reports/`, `targets/`,
`samples/`, the heavy `shortlist/` sub-dirs (`repos*`, `s20`, `s500`, `next`,
`bulk`, `quarry-v5.2.0`, `llama.json`), all `*.so`, and the root raw scan outputs
(`*-report.json`, `*-report.md`, `*-scan.txt`).

---

## 4. Setup

### 4.1 Base (all engines)
- **Python 3** for the CLIs themselves (`scan.py`, `evm_scan.py`, `fuzz_scan.py`
  run on plain `python3`; standard library only for the Solana scanner).
- Copy env: `cp .env.example .env` and fill `ETHERSCAN_API_KEY` (or export it).

### 4.2 EVM static scanner (Slither)
Slither needs a newer Python than system 3.12.0 (crytic-compile excludes 3.12.0),
so it lives in its own venv on Homebrew Python 3.13:
```bash
brew install python@3.13
/opt/homebrew/bin/python3.13 -m venv .venv-evm
.venv-evm/bin/pip install slither-analyzer solc-select
```
`evm_scan.py` runs on plain `python3` and calls the worker inside `.venv-evm` as a
subprocess. solc versions are fetched automatically per contract via solc-select
(`~/.solc-select`). Overrides: `SOLSCAN_EVM_PYTHON`, `SOLSCAN_SOLC_SELECT`,
`SOLSCAN_EVM_WORKDIR`.

### 4.3 EVM fuzzer (Foundry)
- Install Foundry (official prebuilt release) into `~/.foundry/bin`:
  `curl -L https://foundry.paradigm.xyz | bash && foundryup`
  (Do **not** `brew install` it on older macOS — it compiles from source for hours.)
- `forge-std` is cloned automatically into `fuzz-work/_lib/forge-std` on first run.
- An **archive** JSON-RPC that serves historical state is required for the pinned
  fork. Order of preference: `--rpc` → `ETH_RPC_URL` → public `eth.drpc.org`.
  `fuzz_scan.py` starts its own local **anvil** at the pinned block and points forge
  at it (spreading upstream requests over drpc/mevblocker/blastapi with retries).

### 4.4 Environment variables
| var | needed by | purpose |
|---|---|---|
| `ETHERSCAN_API_KEY` | evm_scan, inventory, fuzz keyless-fallback | verified source + logs (read-only). Never printed. Without it: Blockscout fallback. |
| `ETH_RPC_URL` | fuzz_scan (optional) | archive RPC for the local fork; else public nodes. |
| `SOLSCAN_EVM_PYTHON` / `SOLSCAN_SOLC_SELECT` / `SOLSCAN_EVM_WORKDIR` | evm_scan (optional) | override venv python / solc-select / workdir. |

---

## 5. Running it

### 5.1 Solana (always do STEP 0 first)
```bash
python3 livecheck.py <repo-path>            # live on mainnet AND "VOLLEDIGE BRON"? exit 0 = scan, 1 = skip
python3 sourcecheck.py <repo-path>          # own logic vs shell / private source
python3 scan.py <path-to-program>           # scan a local Anchor program
python3 scan.py --github https://github.com/<org>/<repo>
python3 scan.py <path> --json r.json --md r.md
```
Only scan a target whose own program is **live on mainnet AND VOLLEDIGE BRON**
(full source). Lessons baked in: a `declare_id!` that is not on-chain → skip
(Reflect); a repo that is only a shell while the live program is private → skip
(Larix). Rule IDs and the triage recipe are in CLAUDE.md.

### 5.2 EVM static
```bash
python3 evm_scan.py --address 0x... --chain eth --json r.json --md r.md
python3 evm_scan.py --address 0x... --chain base          # no key → Blockscout fallback
python3 evm_scan.py contracts/                            # local folder / foundry / hardhat
python3 tests/evm/test_privilege.py                       # regression (run the others the same way)
```
Verified source means the explorer recompiled it and matched the deployed
bytecode — so (unlike Solana) no separate live/source check is needed. Proxies are
followed one level to the implementation, confirmed via the EIP-1967/1822/legacy
storage slot. Exit 1 = a gold High/Critical finding remains; 2 = tool/explorer error.

### 5.3 EVM fuzz
```bash
python3 fuzz_scan.py --address 0x... --name <name>                       # auto type + default invariants
python3 fuzz_scan.py --address 0x... --name <name> --invariants solvency,no-free-withdraw --runs 256 --depth 50
python3 fuzz_scan.py --address 0x... --name <name> --warp                # let time pass (interest/liquidations)
python3 fuzz_scan.py --rerun <name>                                      # rerun (keeps Custom.t.sol)
```
Report → `fuzz-reports/<name>.md`. The proof of a bug is a broken invariant plus
Foundry's shrunk call sequence — never an exploit tx. Always start small
(`--runs 4 --depth 10`), confirm **both positive controls are ✓** and the coverage
table shows the core actions actually succeed, then scale up. CLAUDE.md
"Invariant fuzzing" has the full per-contract checklist (funding, tolerances,
same-block exits, replaying a break before believing it).

### 5.4 Rebuild the EVM Ethereum inventory
```bash
python3 shortlist/evm-eth/inventory.py        # resumable; appends to results.json per protocol
python3 shortlist/evm-eth/make_table.py       # render → evm-inventaris-ethereum.md
```

---

## 6. Report formats & batch bookkeeping

- **`scan-voortgang.md`** — one row per EVM protocol: `# | protocol | batch | status
  | adres (scan) | triage`. `status` is `gescand — niks (...)`, `gescand — <finding>`,
  or `N.V.T. — <reason>`. A protocol gets a **separate `triage-<slug>.md`** only when
  there is a real finding or an active oracle gap; otherwise the one-line disposition
  lives inline in the row. Scope rule: only **EIGEN CODE** (own-code) protocols from
  `shortlist/evm-eth/results.json` get a row; forks/standard/ADRES-ONBEKEND are
  excluded up front.
- **`fuzz-voortgang.md`** — one row per campaign: `# | protocol | adres | invarianten
  | status | runs/calls | rapport`. "COMPLEET — geen schending" must always state N
  runs, the call count and the coverage; an infra error is `NIET VOLTOOID` /
  `INFRA-FOUT`, never "clean".
- **`modules-status.md`** — the fuzz-harness extension modules, each with a positive
  control and (where possible) a detection-only historical-hack benchmark.
- A `triage-<slug>.md` states: date, read-only method, the privilege filter outcome,
  and for each surviving candidate: privilege level (GOUD/LAAG + who), file:line, why
  exploitable, and a concrete bad input if constructible. Gold first, low-priority in
  a one-line tail. "Niks GOUD gevonden" is a valid, common result.

---

## 7. Known limitations & open tooling fixes (honest)

- **viaIR / `COMPILE_FAILED` (half-silent compile failure) — OPEN.** If a contract
  needs `viaIR` and the explorer metadata omits it, crytic-compile can hit
  "stack too deep". Today a *hard* compile exception is caught
  (`slither_worker.py` → appends a `compilatie/parse mislukt` error and returns
  exit 2), **but** `slither_runner.py` reads the worker JSON regardless of exit code,
  so a failure surfaces only as "0 findings + an error line in the footer" — not a
  distinct terminal state — and a *successful-but-empty* compilation (0 contracts, no
  exception) is unguarded and reads as clean. **To do (2 parts):** (a) make compile
  failure / degenerate compilation a hard `COMPILE_FAILED` terminal state that refuses
  to emit a findings report; (b) auto-retry once with `--via-ir` before failing, then
  hard-fail loudly. Add a regression: a viaIR-only contract must go
  `COMPILE_FAILED → retry → analyzed`; a broken one must stay `COMPILE_FAILED`.
  (Batch 8 was checked and is *not* affected — every scan compiled real units with
  many findings — but any future "0 findings" verdict is untrustworthy until this is
  fixed.)
- **Keyless proxy→impl resolution — PARTIAL.** With a key, the implementation is
  confirmed via a read-only `eth_getStorageAt` on the EIP-1967/1822/legacy slot. The
  Blockscout (keyless) path has weaker proxy handling and may miss or mis-resolve an
  implementation; prefer running with `ETHERSCAN_API_KEY`.
- **Fuzzer "unknown"/unsupported classification.** `detect.classify` only knows 10
  template types (lender/vault/amm/token/wrapper/mintredeem/queuevault/sir/locktoken/
  aavebook). Anything else returns "niet ondersteund" and is skipped (see the
  `OVERGESLAGEN – geen template` rows in fuzz-voortgang.md: Convex-booster staking,
  Geyser/Visor, Curve stableswap, basket-AMM). Extending coverage = adding a template.
- **Adapter-address mismatches.** A DeFiLlama adapter address can point at *another*
  protocol's contract (batch 8: Superform→Notional, Symbiosis→Puffer). Always confirm
  the scanned contract actually belongs to the named protocol before reporting; mark
  mismatches `N.V.T.`.
- **Vyper is out of scope** for the Slither pipeline (e.g. Uniswap V1, Curve) — skip
  or add Vyper compile support separately.
- **Flattened single-file sources** inline OpenZeppelin; the path-based dependency
  filter cannot remove it, so judge those findings by hand (often dead library code).
- The **static free-mint detector was built and dropped** (≈25% false-positive on the
  62-protocol set — it flagged standard ERC20 `transfer`). The free-mint class is
  covered dynamically by the ATTACKER-PROFIT invariant instead.

---

## 8. Planned fuzzer extensions (concrete to-dos, all fork-based, detect-only)

Discipline for every item: **local fork only, never a mainnet tx; a broken invariant
becomes "missing protection + fix", never a ready-made attack script; each module
needs a positive control and, where possible, a detection-only historical-hack
benchmark (fork the block before the incident, show the invariant/detector fires on
pre-patch code — a regression test, not a drain replay).**

- **Coverage-guided fuzzing via Medusa / Echidna.** Drive the handlers with a
  coverage-guided engine instead of (or alongside) Foundry's random invariant runner,
  to reach deeper states. Keep the same invariants and detect-only reporting.
- **Flash-loan as a handler action (resistance form only).** borrow → actions → repay
  within one call, feeding SOLVENCY / ATTACKER-PROFIT. **Explicitly NOT** the
  weaponized form (flash-loan + live pool-swaps to move price + cross-protocol
  chaining) — that was declined as an attack recipe and must stay out.
- **`vm.warp` / `vm.roll` as fuzz actions — DONE (module 4).** `warpTime` is wired into
  every template and fuzzed under `--warp`; under warp the value-conservation
  invariants are dropped (yield legitimately moves value) and a role/allowance-only
  ATTACKER-PROFIT variant is used. Positive control + Lista reachability benchmark green.
- **Extra invariants.** Beyond solvency / no-free-withdraw / conservation / k-monotonic
  / access / attacker-profit: e.g. share-price monotonicity under deposits, per-user
  accounting conservation, liquidation health bounds.
- **Realistic seeding.** Seed handlers with realistic balances/positions (whale funding
  within the fork, realistic bounds) so core actions succeed instead of reverting — the
  coverage table is the signal for whether an action was really tested.
- **Oracle module (module 3) — DONE (forced-value form).** mock a Chainlink answer
  (stale/0/deviated) via `vm.mockCall` and check the consumer rejects it. The
  live-pool-manipulation form was deliberately not built.

See `modules-status.md` for the full state of modules 1/3/4 (built, with positive
controls and benchmarks) and the declined weaponized drain generator.

---

## 9. Results so far & ground-truth tests

- **EVM inventory:** 278/278 Ethereum protocols classified (A–Z). 108 own-code; the
  rest fork/standard, token-only, CEX, or address-unknown. Every own-code entry carries
  an on-chain `live` flag (`eth_getCode`).
- **EVM scan batches 1–8** recorded in `scan-voortgang.md`. **Batch 8** (Sierra →
  The Idols, 15 protocols): **0 gold after real triage** — all High findings were
  verified false positives (proxy-fallback delegatecall, `nonReentrant` reentrancy,
  ERC-7540 silo `arbitrary-from`, delegatecall-library `msg.value`, permissionless
  deposit) or adapter mismatches. "0 gold" is a normal outcome, not a failure.
- **Fuzz campaigns** in `fuzz-voortgang.md`: several COMPLETE with no violation
  (Lista, PancakeSwap, Idle, Abracadabra, NaraUSD, Origin Dollar, Decentralized Euro),
  each with passing positive controls; others skipped for missing templates.
- **Two ground-truth tests** (does the tool catch real, known bugs?):
  1. **Payy Network** (`triage-payy-network.md`) — a real 2026 bridge hack. **Neither
     engine flags it, correctly out of scope:** the bug is a **soundness fault in the
     ZK proof system** (a Noir aggregation circuit), not in the Solidity bridge. Honest
     negative — documents the tool's boundary.
  2. **Batch 8** — a blind run over 15 fresh protocols: **0 gold** after reading the
     source behind every High finding. Confirms the triage/privilege filter suppresses
     the known false-positive classes rather than rubber-stamping raw Slither output.

---

## 10. What is NOT in the repo (must be supplied separately)

- **`ETHERSCAN_API_KEY`** — real value supplied out-of-band; put it in `.env` or export
  it. The repo ships only `.env.example` with an empty placeholder.
- **`.venv-evm/`** — recreate per §4.2 (`python3.13 -m venv` + pip install).
- **Foundry** (`~/.foundry/bin`) and **solc** versions (`~/.solc-select`) — install per
  §4.3 / §4.2; fetched on demand.
- **`fuzz-work/`** incl. the auto-cloned `forge-std` — regenerated by `fuzz_scan.py`.
- **Cloned target repos & large candidate data** (`targets/`, `samples/`, the heavy
  `shortlist/` sub-dirs, `*.so`) — re-cloned / re-fetched on demand; not part of the tool.
- **Generated outputs** (`evm-reports/`, `fuzz-reports/`, root `*-report.*` / `*-scan.txt`)
  — regenerated by re-running the relevant command.

A fresh `git clone`, then §4 (venv + Foundry + key) and §5 (run a command), is enough
to stand the project up and extend it. Nothing else from the original machine is needed.
