# Project context for Claude Code — SolScan

This repo is **SolScan**, a static vulnerability scanner for Solana (Anchor)
programs. When working here, your job is usually one of two things: (1) run the
scanner on a target, or (2) triage its output down to the findings that
actually matter. Read this before doing either.

## Step 0 — livecheck + source check before scanning

**Always run `livecheck.py` on the repo path first.** Only scan or triage a
target if at least one of its own programs is **live on mainnet AND has
"VOLLEDIGE BRON"**. Two lessons are built in:
- **Reflect fork:** a `declare_id!` that doesn't exist on-chain → skip.
- **Larix:** a repo can be only a shell (state layouts + instruction builders)
  while the live program is built from private source → skip.

```bash
python3 livecheck.py <repo-path>                        # live check + source check per crate
python3 livecheck.py <program-id> [<program-id> ...]    # live check only (no repo to compare)
python3 livecheck.py <repo-path> --devnet               # also show devnet status
python3 sourcecheck.py <repo-path>                      # source check on its own
```

For a repo path, every own live program gets a source check (`sourcecheck.py`):

| Verdict | Meaning | Scan? |
|---|---|---|
| **VOLLEDIGE BRON** | entrypoint/`#[program]` dispatches, real handlers exist, and no own source file in the live bytecode is missing from the repo | **yes** |
| **SHELL (geen logica)** | no entrypoint, a stub entrypoint (only `Ok(())`, dispatch commented out), or no non-trivial handlers | no |
| **LIVE = PRIVAAT** | the live bytecode references own source files that are not in the repo (e.g. `src/processors/*`, `programs/<crate>/src/...`) → built from private/unpublished source | no (or only the public part, stated explicitly) |

How it works:
- The bytecode check reads the program via `getAccountInfo` and compares the
  embedded panic paths with the repo.
- Bare `src/...` paths can be dependency files (newer toolchains trim registry
  paths). Only these count as evidence of private source:
  - workspace-prefixed paths for this crate;
  - files in a `src/<subdir>/` that exists in the crate.
- Other bare paths are listed as "onduidelijk" (unclear), not as evidence.

Exit code 0 = at least one own program is live on mainnet and (for repo paths)
VOLLEDIGE BRON; 1 = skip. Read-only (`getAccountInfo` only).
- "ONBEKEND / RPC-FOUT" means unknown, not dead: retry, or use `--rpc`.
- IDs from vendored modules (not a crate's `lib.rs`) don't count.
- `--no-source-check` skips the source check (not recommended).

## How to run the scanner

```bash
# a cloned/local program folder
python3 scan.py <path-to-program>

# clone + scan a public GitHub repo
python3 scan.py --github https://github.com/<org>/<repo>

# save reports
python3 scan.py <path> --json report.json --md report.md
```

The scanner already filters test/reference/duplicate findings by default.
`--include-tests` turns that off.

## What the rule IDs mean

- **SOL-AUTH-001** — an authority account isn't required to sign (critical if real).
- **SOL-OWNER-002** — a raw `AccountInfo` with no owner/address check (noisy, often fine).
- **SOL-TYPE-003** — manual deserialization without a discriminator (type confusion).
- **SOL-CPI-004** — a CPI whose target program id isn't validated.
- **SOL-PDA-005** — non-canonical PDA via `create_program_address`.
- **SOL-ARITH-101** — unchecked `+ * /` on a value-bearing field.
- **SOL-ARITH-102** — subtraction that can underflow.
- **SOL-ARITH-103** — division before multiplication (precision loss).
- **SOL-ARITH-104** — truncating numeric cast.
- **SOL-ARITH-105** — implicit rounding direction on a payout/share.
- **SOL-CFG-201** — release profile missing `overflow-checks = true`.

## Triage recipe — the important part

The raw list is NOT the product. A real audit finding has to survive judgment.

### Privilege filter — apply FIRST to every candidate

Before doing any deep analysis of a candidate, decide **who can abuse it**:

| Who can trigger it | Priority | What to do |
|---|---|---|
| **External attacker** (no rights needed) | **GOUD** (gold) | Always work it out fully. |
| **Ordinary user** (only their own deposit/account) | **GOUD** (gold) | Always work it out fully. |
| **Manager / admin / authority only** | **LAAG** (low) | Note it in 1–3 lines and move on. Do NOT work it out fully. |
| **Requires a trusted co-signer / backend key** | **LAAG** (low) | Unless that protection can be bypassed; then re-rate it as above. |

The only question that matters for a reportable bug:
**"Can someone WITHOUT privileges use this to take someone else's money?"**
If not → low priority. Don't spend deep triage time on manager-only or admin-only
findings.

Edge cases. Check these before labelling something LOW:
- **Privilege escalation counts as GOLD.** If an ordinary user can *obtain* the role
  (e.g. creating their own vault makes them its "manager", permissionlessly,
  and other users can then deposit into it), or can bypass a role check, rate it
  as an ordinary-user bug.
- **Bypassable co-signers count as GOLD.** If the co-signer check can be bypassed
  (a missing signer check, a different instruction without the co-sign that
  reaches the same effect), rate it by who can reach it without the co-sign.

For a LOW finding, write one line: *who* can do it, *what* it does, and that it is privileged.

### Then work in this order, and be skeptical

1. **Drop off-chain code.** Anything under `cli/`, `client/`, `sdk/`, `scripts/`
   or a `main.rs` that is a command-line tool is not deployed on-chain. The
   scanner already drops `tests/`, `reference/`, examples and `assert_eq!`
   lines; also discount CLI/SDK paths yourself.
2. **Focus on `program/src/` and `instructions/`** — the handlers that move
   value or change state. That is where a real bug lives.
3. **For each surviving ARITH/CPI/TYPE finding, read the code in context and
   ask:** can this value realistically overflow/underflow or be attacker-
   controlled, AND is money or authority attached? If yes → real candidate. If
   it's a timestamp add, a constant, or a bounded loop counter → discount it.
4. **Confirm the cheap ones.** `SOL-CFG-201` (overflow-checks off) is a real,
   easily-verified finding and it makes every ARITH finding more dangerous.
5. Produce a short list. For each real candidate give:
   - its **privilege level** (GOUD/LAAG + who);
   - file:line;
   - why it's exploitable;
   - a concrete bad input, if you can construct one.

   Put GOLD candidates first. LOW ones go in a one-line-each tail.

A good result is 1–3 solid GOLD candidates, not 50 maybes. "Niks GOUD gevonden"
(no gold found) is a valid and common result.

## EVM / Solidity — `evm_scan.py` (Slither engine + SolScan triage)

Same rules as for Solana: detect and explain only, read-only, privilege filter first.

### Setup (once)

Slither needs a newer Python than the system Python 3.12.0, because crytic-compile
excludes 3.12.0. It therefore lives in its own venv on Homebrew Python 3.13.
`evm_scan.py` itself runs on plain `python3` and calls Slither as a subprocess.

```bash
brew install python@3.13
/opt/homebrew/bin/python3.13 -m venv .venv-evm
.venv-evm/bin/pip install slither-analyzer solc-select
```

Compilers are fetched automatically per contract via solc-select (`~/.solc-select`).
Overrides: `SOLSCAN_EVM_PYTHON`, `SOLSCAN_SOLC_SELECT`, `SOLSCAN_EVM_WORKDIR`.

### Running it

```bash
python3 evm_scan.py --address 0x... --chain eth --api-key KEY        # verified source via Etherscan v2
python3 evm_scan.py --address 0x... --chain base                     # no key: Blockscout fallback
python3 evm_scan.py contracts/                                       # local folder / foundry / hardhat
python3 evm_scan.py Token.sol --json r.json --md r.md --min-severity Medium --include-info
python3 tests/evm/test_privilege.py                                  # privilege-filter regression test
```

The API key can also come from `ETHERSCAN_API_KEY`. Chains: `eth`, `base`,
`arbitrum`, `optimism`, `bsc`, `polygon`, `avalanche`, `linea`, `scroll`, …,
or a chain id.

Exit code 1 = a GOUD finding of severity High/Critical remains; 2 = tool or explorer error.

### What each step does

1. **Fetch source** (`solscan/evm/etherscan.py`).
   - Uses Etherscan API v2 (one endpoint, `chainid=`). Without a key it falls back
     to Blockscout's Etherscan-compatible API.
   - Parses all three source formats: single file, multi-file JSON, and
     standard-JSON `{{…}}`.
   - **Verified source = the explorer recompiled it and matched the deployed
     bytecode → you know it is the live code. No sourcecheck/livecheck is needed
     (unlike Solana).**
2. **Reproduce the build.**
   - The exact solc version, optimizer (runs) and EVM version come from the
     explorer metadata.
   - `--base-path` is only used from solc 0.8.8: older solc crashes with it.
3. **Proxy.** If the explorer reports an implementation address, it is fetched and
   scanned too. Its findings are prefixed `[impl]`.
   - **Verification via storage slot.** With a key, the implementation is confirmed
     with a read-only `eth_getStorageAt` on the EIP-1967, ZeppelinOS-legacy or
     EIP-1822 slot. If the slot disagrees with the explorer, the slot wins.
   - **Only one level is followed.** Etherscan sometimes marks an implementation as
     a proxy as well: on USDC it points `FiatTokenV2_2` to the linked library
     `SignatureChecker`. Without a proxy slot this is reported as a misdetection
     and not followed.
   - **The API key comes only from `ETHERSCAN_API_KEY` (or `--api-key`).** It is
     never printed. The output shows only where the key came from:
     `key: ETHERSCAN_API_KEY (env)`.
   - **Flattened single files** contain OpenZeppelin code inline. The path-based
     dependency filter can't remove that, so judge those findings yourself (they
     are often dead library code and therefore LAAG).
4. **Slither** (`solscan/evm/slither_worker.py`, runs inside the venv).
   - Runs all Slither detectors.
   - Builds an **access map** per function.
   - Runs SolScan's own detector **missing access control**: an ungated
     public/external function that writes authority state (vars that are really
     compared with `msg.sender`, or address vars named owner/admin/…).
5. **Triage** (`solscan/evm/triage.py`).
   - Removes dependency/test noise (`node_modules`, `lib/`, `@openzeppelin`,
     `forge-std`, tests, mocks, scripts).
   - Deduplicates, and hides Info unless `--include-info`.
   - Applies the **privilege filter**:
     - **GOUD**: reachable without a gate (also an internal function reachable
       from an ungated entry point).
     - **LAAG**: admin/role-gated, initializer-only or constructor-only. The
       severity is lowered one step and the original stays in the detail.
     - `tx-origin` and the missing-access-control detectors are never lowered,
       because there the gate *is* the bug.

### Oracle-safety checks (`solscan/evm/oracle_checks.py`)

These are defensive checks. They point out a price read **without the usual
protection** and say how to add it. Every finding is "verify manually" and states
only which protection is missing, never an attack path or a feasibility estimate.

They are relevant only for protocols that work with prices (lending, perps, CDP,
vaults), **not** for plain DEX, bridge or staking contracts.

| Rule | When it is flagged | Fix advice |
|---|---|---|
| `EVM-ORACLE-SPOT` (High, conf. Medium) | `getReserves`/`slot0`/`getAmountOut(s)` is used as price/valuation (not in a function that swaps), and there is no time-averaging (`observe`/`consult`/TWAP/cumulative) in the contract | use a TWAP or a robust oracle instead of a momentary pool price |
| `EVM-ORACLE-FRESH` (Medium/High, conf. Medium) | `latestAnswer()` (no timestamp), or `latestRoundData()` without an `updatedAt`-age check and/or `answer > 0` | check `updatedAt` against a max age and `answer > 0` before using the value |
| `EVM-ORACLE-SINGLE` (Medium, conf. Low) | exactly one price-source kind, no TWAP, no second source or sanity bound | add a second source or a reasonableness bound |

- **Report line:** "Oracle-dekking: ja/nee". If no external price source is found,
  the report says the oracle checks do not apply.
- **Input:** the per-function export from the worker (calls from Slither's IR,
  function source). Without Slither data a coarse regex fallback is used
  (confidence Low).
- **Where checks are searched for:** checks in internal helpers and `try … returns`
  are recognised. If a check is missing at function level, the whole contract is
  searched (validation often lives in a separate function, as in Liquity's
  `PriceFeed`).

  **Limitation:** one protected function in a contract can hide an unprotected
  function in the same contract.
- **Test:** `python3 tests/evm/test_oracle.py`. The protected variants must not
  fire. The real-world check is Liquity `PriceFeed`: 0 oracle findings.

### `unprotected-sibling` (static detector)

An **ungated** public/external function that does one of the following, in a contract
where **other functions are gated**:

- `delegatecall` or a low-level `call` to an address the caller supplies;
- makes the *contract* approve a caller-chosen spender, or approve on a caller-chosen
  token (`approve`, `safeApprove`, `forceApprove`, `increaseAllowance`,
  `setApprovalForAll`);
- calls privilege-granting functions (`grantRole`, `transferOwnership`, `setOperator`, …)
  with caller-controlled values;
- calls a state-changing function on a caller-chosen address (a callback). This is
  Medium and Low confidence.

How it works:
- Slither's data-dependency analysis decides whether the call target or spender derives
  from a function **parameter**.
- One level of internal calls is followed.
- The gated siblings show the authors knew the entry points need protection, so the
  ungated one is likely an oversight.

Severity:
- **HIGH** when the contract can move value (payable, ETH transfer, or token
  `transfer`/`approve` calls).
- Otherwise Medium.
- Never lowered by the privilege filter (`AUTHZ_DETECTORS`).

Deliberately **not** flagged:
- the normal deposit pattern (`transferFrom` on a caller-chosen token);
- per-user delegation (`delegates[msg.sender] = to`);
- contracts without any gated function, where there is no sibling to compare with.

Test: `python3 tests/evm/test_sibling.py` runs the detector on a reconstructed example
(`tests/evm/sibling/SiblingCases.sol`: a flawed toy vault plus negative controls) and
checks 14 expectations. The rule is "verify manually": it points at a function and a
missing check, nothing more.

### How the access map decides "gated"

**Counts as gated:**
- **Modifiers**, also when inherited or defined in another contract:
  - recognised by name (`onlyOwner`, `onlyRole`, `auth`, …);
  - or by what they do (a `msg.sender` check inside a custom-named modifier).
- **OpenZeppelin `Ownable`/`AccessControl`** (v4 and v5): `_checkOwner`,
  `_checkRole`, `hasRole`.
- **An inline `require(msg.sender == authority)`**, or a check inside an internal
  helper.
- **An authority mapping** (`isOperator[msg.sender]`).
- **`if (owner() != _msgSender()) revert`.**

**Does NOT count as gated:**
- per-user checks (`balances[msg.sender] >= x`, `allowance[from][msg.sender]`,
  `positions[id].owner == msg.sender`);
- `require(msg.sender != admin)` (that excludes the admin);
- `whenNotPaused`, `nonReentrant`;
- `tx.origin`.

**Init-only:** the OpenZeppelin `initializer`/`reinitializer` modifiers, or an
`initialize*` function with its own one-time flag (`require(!initialized)`,
`_initializedVersion`).

The access map is a **heuristic**. A GOUD label means "no gate found": confirm it
by reading the code before treating it as exploitable.

## Invariant fuzzing — `fuzz_scan.py` (Foundry, local mainnet fork)

This finds dynamic bugs that static analysis misses. A live contract is driven by
thousands of fuzzed actor calls on a **local fork**, and after **every** call the
safety rules (invariants) are checked.

The proof of a bug is a broken invariant plus Foundry's shrunk call sequence. It is
never an exploit transaction: nothing is signed, broadcast or sent to mainnet.

### Setup (once)

Foundry is installed in `~/.foundry/bin`. It is the official prebuilt release
(v1.8.4, checksum-verified); Homebrew compiles it from source on macOS 13, which takes
hours. forge-std is cloned automatically into `fuzz-work/_lib/forge-std`.

### Choosing an RPC

The fork stays pinned to one block for the whole run, so the RPC must serve
**historical state**. The order of preference is:
1. `--rpc`;
2. `ETH_RPC_URL`;
3. the public `eth.drpc.org`.

Not every node works:
- `ethereum-rpc.publicnode.com` refuses archive requests.
- `1rpc.io` and `rpc.flashbots.net` fail anvil's genesis requests.
- Logs come through Etherscan v2 (`ETHERSCAN_API_KEY`).

**Local anvil fork.** `fuzz_scan.py` starts its own local **anvil** at the pinned block
and points forge at it. Anvil spreads requests over drpc, mevblocker and blastapi, with
retries and a 120 s timeout. Forge itself gets `eth_rpc_timeout = 600`.

**Infrastructure errors.** A fork or RPC error gets the status **INFRA-FOUT**: it is
never a finding and never counts as "geen schending". The campaign is retried once
automatically, and forge's disk cache keeps the state fetched so far.

**Always pin the fuzz sender** (`targetSender`, already in the templates). Without it,
Foundry invents a random `msg.sender` for every call, and each new address costs an
upstream account lookup on the fork. On Lista that caused 504s and aborted campaigns.
With a fixed sender the same campaign (12,800 calls) ran in 5 minutes. The handler
impersonates its own actors (`vm.prank`), so the sender doesn't matter. The
anvil log is in `fuzz-work/<naam>/anvil.log`.

### Running it

```bash
python3 fuzz_scan.py --address 0x... --name <naam>                       # auto type + default invariants
python3 fuzz_scan.py --address 0x... --name <naam> --invariants solvency,no-free-withdraw --runs 256 --depth 50
python3 fuzz_scan.py --address 0x... --name <naam> --warp                # time passes: interest/liquidations
python3 fuzz_scan.py --rerun <naam>                                      # rerun (keeps Custom.t.sol)
```

Output goes to `fuzz-reports/<naam>.md`. It lists:
- the invariants with their status;
- runs and calls;
- for a broken invariant: the reproducing call sequence and the function where it
  broke, plus a fix direction;
- coverage: how often each handler action actually succeeded;
- the positive controls.

Exit code 1 means an invariant broke; 2 means no results (a compile or fork error).

### How it works (`solscan/evm/fuzz/`)

1. **Target.** The generator fetches the verified source and ABI. If the address is a
   proxy, the ABI comes from the implementation (confirmed via the slot), and calls go
   to the proxy.
2. **Type.** `detect.classify` picks the type from the ABI:
   - `lender`: Morpho-Blue style (`supply`/`borrow`/`supplyCollateral` with a `MarketParams` tuple);
   - `vault`: ERC-4626;
   - `amm`: Uniswap-V2 pair;
   - `token`: ERC-20;
   - `wrapper`: a Convex-style 1:1 staking wrapper;
   - `mintredeem`: a collateral-backed stable with mint/redeem/queue and an MCT collateral book (NaraUSD);
   - `queuevault`: mint plus an async withdrawal queue with a rebasing oToken (Origin OUSD/OETH).

   You can override it with `--type`. For a lender, the markets come from the
   `CreateMarket` logs, and the struct is generated from the ABI. That means forks with
   extra fields work too, such as Fira's `ltv`/`whitelist`.
3. **Generated project (`fuzz-work/<naam>/`).**
   - **`Invariants.t.sol`** contains:
     - `vm.createSelectFork` at the pinned block;
     - a **Handler** with local test actors (`makeAddr`, funded with `deal`), whose
       calls are wrapped in try/catch;
     - ghost accounting: value in and out per actor;
     - the chosen invariants.
   - **`Control.t.sol`** holds **positive controls**: it deliberately corrupts the fork
     state and expects the invariant to fire. A ✗ there means the check doesn't work
     and the result can't be trusted.
   - **`Custom.t.sol`** holds your own invariants and is **never overwritten**.
4. **Run.** Foundry ≥ 1.x runs all invariants of a contract in **one shared campaign**
   and checks them after every call. `afterInvariant()` writes `coverage.csv`.

### Standard invariants (`--invariants`)

| Invariant | Rule | Types |
|---|---|---|
| `solvency` | lender: borrow ≤ supply per market; token balance ≥ Σ(supply − borrow), absolute for loan tokens and as a delta for collateral. vault: `convertToAssets(totalSupply) ≤ totalAssets`. amm: balances ≥ reserves | lender, vault, amm |
| `no-free-withdraw` | no actor ever takes out more value than it put in (collateral valued at the market oracle; tolerance 10 wei per operation). **Off with `--warp`**, because yield and liquidation profit are intended there | lender, vault, token |
| `conservation` | per token, Σ(actor balances) + target balance stays exactly constant (on the fork only the actors and the target move tokens) | lender, amm, token, vault (as a group) |
| `access` | functions gated according to the source, called by an unauthorized actor with fuzzed static arguments, must revert. Override the list with `--privileged f1,f2` | all |
| `solvency` (queuevault) | Δ totalValue ≥ net oToken minted by the actors (a 1:1 mint at a ratio > 1 lowers the *ratio* by arithmetic alone, so the ratio is not the invariant) | queuevault |
| `k-monotonic` | √k per LP share (protocol LP included) never decreases, except for exactly the dilution from V2 `_mintFee`: `allowed = lastKps·T_prev/(T_prev+d)`. Tolerance = 1 base unit of the smaller reserve | amm |

### Pointing the harness at a new contract

1. Check that the type is detected. If you get "niet ondersteund", pass `--type`, or
   add a template to `templates.py`: a handler, invariants and a test, in the style of
   the existing ones.
2. Start small (`--runs 4 --depth 10`). Check two things in the report:
   - **both controls are ✓**;
   - the **coverage table** shows that the core actions really succeed.

   An action that is never "geslaagd" (succeeded) has not been tested. Typical causes
   are `deal` not finding the token's balance slot (`fundingFailed`), a whitelist or
   role on the action, or a wrong bound.
3. Then scale up (`--runs 256 --depth 50` or more). Then run separately with `--warp`
   for the time-dependent paths.
4. Contract-specific rules go in `fuzz-work/<naam>/test/Custom.t.sol` as
   `invariant_<naam>()`. They run automatically, because FuzzCustom inherits from
   FuzzInvariants.
5. **Privilege filter, here too.** A role that the handler simulates is privileged. A
   break that only occurs through that role is LAAG; unauthorized actors are what count.
   The generator detects these roles itself, and they appear in `target.json`:
   - the supplier role: Fira's `whitelist` field, or the first entry of Moolah's
     `getWhiteList(id)`;
   - the collateral provider: Moolah's `providers(id, token)`. The provider is
     simulated as a pass-through: the actor sends tokens to the provider, which deposits
     them on the actor's behalf and has itself approved the target.
6. **Fork-specific rules.** The handler uses the target's own `getPrice(MarketParams)`
   (if it has one) and `minLoan(MarketParams)` (minimum position size). Partial
   withdraw/repay close the position fully half the time, so no dust below the minimum
   is left. Borrowing is capped by the market's free liquidity.
7. **Coverage table.** For each action it shows the **last revert reason**, which tells
   you right away which fork rule blocks an action (for example "not provider", "not
   broker", "remain borrow too low").

"Geen invariant-schending in N runs" (no invariant violation in N runs) means exactly
that, not "bug-free". Always state N, the calls and the coverage.
8. **ACCESS heuristic.** A function only counts as gated if **every** definition with
   that name and arity in the source is gated. `msg.sender == <parameter>` is a
   per-user check, not a gate. The body is determined by matching braces. Before these
   fixes there were false positives on ERC-4626 `mint` (Idle) and Convex `getReward`
   (Abracadabra).
9. **Funding and gas.** If `deal` can't write a token's balance (stETH, rebasing share
   tokens), the Funder falls back to Lido `submit()`. `foundry.toml` lifts the fork's
   block gas limit for setUp.
10. **Same-block checks.** The vault handler rolls forward 1 block before every exit,
    because users withdraw in a later block. Without that, IdleCDO blocks every exit.

11. **Never fund the target's own receipt tokens with `deal`.** On SIR, vault 19 uses
    vault 6's APE token as its collateral. Funding the actors with `deal` wrote unbacked
    APE balances into storage, and burning them paid out real collateral. That showed up
    as a NO-FREE-WITHDRAW violation (88,185,033 withdrawn against 0 deposited) and was a
    harness artifact. The SIR template now skips every vault whose collateral is one of
    its own APE tokens. **Before reporting any NO-FREE-WITHDRAW break, check in the
    replay trace that the actor's starting balances were not created by `deal`.**
12. **Replay a break before you believe it.** Run it with
    `forge test --match-test invariant_<x> -vvvv` (Foundry replays the stored
    counterexample first), and write down which function in the *target* misbehaves. A
    panic inside the target's own view function (SFI `getUserBalance`) is a finding about
    that function, not automatically a broken invariant. Test whether it heals when time
    advances. The invariants then skip states the target itself cannot answer, and count
    them.
13. **Tolerances.** Share maths on 1e24-scale amounts rounds by ±1e5 wei. Use a relative
    tolerance (1e-12 of the amount) next to the absolute one, or every large-amount
    template reports rounding noise as a violation.
14. **A control that cannot fire invalidates a clean result.** If the invariant skips
    states it cannot measure, corrupt the *measured* quantity (the obligations or the
    reserve), not the thing the contract itself reads. Make the control setup assert
    that its precondition holds.

## Hard rules (do not break these)

- **Detect and explain only. Never write an exploit, a drain script, or a
  malicious transaction**, even as a "proof". A finding is "there is a bug
  here and here's why", never a working attack.
- **Only ever analyze publicly available source.** Never test anything against
  mainnet.
- **Before anyone is contacted, verify the repo is the actually-deployed code**
  (the `declare_id!` program id should match a live program on-chain). Reporting
  bugs in code that isn't deployed destroys credibility.
- **Disclosure is free and non-coercive.** Report findings to the project's
  security contact at no cost. Never tie a fix to a purchase. A monitoring
  service may be offered separately and optionally, never as leverage.
