# SolScan — static vulnerability scanner for Solana programs

Prototype static analyzer for **Solana (Anchor) programs** — the on-chain Rust
logic, not SPL token mints. It reads public program source, flags likely
vulnerabilities with a concrete reason + suggested fix, extracts the project's
responsible-disclosure contact, and drafts a neutral outreach note.

No external dependencies — pure Python 3.10+ standard library.

## Run it

```bash
# scan the bundled vulnerable sample
python scan.py samples/

# scan a local Anchor program folder
python scan.py path/to/program/

# clone + scan a public repo
python scan.py --github https://github.com/org/repo --ref main

# write machine + human reports and a disclosure draft
python scan.py samples/ --json report.json --md report.md --draft-outreach

# only show serious stuff
python scan.py samples/ --min-severity High
```

Exit code is `1` when anything Critical/High is found (handy for CI).

## What it detects

**Known vulnerability classes**
| Rule | Issue |
|------|-------|
| SOL-AUTH-001  | Authority account not required to sign |
| SOL-OWNER-002 | Raw account used without owner/address check |
| SOL-TYPE-003  | Manual deserialization without discriminator (type confusion) |
| SOL-CPI-004   | CPI without validating the target program id |
| SOL-PDA-005   | Non-canonical PDA (`create_program_address`) |
| SOL-INIT-006  | `init_if_needed` re-initialization risk |
| SOL-REMACC-007| `remaining_accounts` used without validation |
| SOL-CLOSE-008 | Manual lamport move without zeroing source |
| SOL-PANIC-009 | `unwrap`/`expect` on the instruction path |

**Arithmetic / precision — the differentiating module**
| Rule | Issue |
|------|-------|
| SOL-ARITH-101 | Unchecked `+ * /` on value-bearing fields |
| SOL-ARITH-102 | Subtraction that can underflow |
| SOL-ARITH-103 | Division before multiplication (precision loss) |
| SOL-ARITH-104 | Truncating numeric cast (`as u64` etc.) |
| SOL-ARITH-105 | Implicit rounding direction on a payout/share |

**Project config**
| Rule | Issue |
|------|-------|
| SOL-CFG-201 | Release profile missing `overflow-checks = true` |

Every finding carries a **severity** and a **confidence**, and most are flagged
`verify manually`. Static analysis is high-recall / lower-precision by nature:
triage before you contact anyone — one false alarm costs you credibility.

## How the outreach is framed (on purpose)

`--draft-outreach` never ties the fix to a purchase. It reports the findings
for free via the program's `security_txt` contact and mentions the monitoring
service separately as optional. Coupling disclosure to payment ("pay or I
publish/exploit") is treated as extortion in many jurisdictions — and converts
worse. Report free, sell the ongoing monitoring.

Also: this tool **only detects and reports**. It does not generate exploits or
transactions. Never test an exploit against mainnet, and never disclose
publicly before a fix. Check a bug-bounty program (e.g. Immunefi) first — you
may simply get paid.

## Turning this into the SaaS — upgrade path

The container this was built in can't reach Solana RPC, so the live
on-chain discovery step is stubbed. To productionise:

1. **Find targets on-chain.** Use `solana-verify` + the OtterSec verified-builds
   API to map program IDs → source repos, and read embedded `security_txt`
   straight from deployed binaries. Feed those repos into `clone_and_scan`.
2. **Cut false positives.** Replace the regex core in `rustsrc.py` with real
   AST analysis (`syn` via a small Rust sidecar, or Semgrep's Rust mode). The
   detector interface in `detectors.py` / `arithmetic.py` stays identical.
3. **Add fuzzing for arithmetic.** Wire in **Trident** (Anchor fuzzer) to turn
   suspected overflow/underflow findings into reproducible failing inputs —
   that "here's the exact input that breaks it" is what makes a report
   undeniable.
4. **Add an LLM review layer.** `api.anthropic.com` is reachable; send each
   flagged function to a model and require a concrete counterexample before a
   finding is promoted to High confidence. This is where recall on *novel*
   logic bugs comes from — but keep a human in the loop, because fully
   automatic discovery of protocol-logic exploits is not solved by anyone.

## Layout

```
scan.py                     CLI
solscan/rustsrc.py          lightweight Rust block parser
solscan/detectors.py        known-class detectors
solscan/arithmetic.py       arithmetic / rounding / precision
solscan/securitytxt.py      disclosure contact + Cargo overflow-checks
solscan/report.py           Finding model + JSON/console/markdown
solscan/scanner.py          orchestration (path / dir / github)
samples/                    deliberately vulnerable test program
```
