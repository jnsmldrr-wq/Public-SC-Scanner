"""Regression test for the `unprotected-sibling` detector (run: python3 tests/evm/test_sibling.py)."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solscan.evm.slither_runner import evm_python, ensure_solc, WORKER

out = subprocess.run([evm_python(), WORKER, os.path.join(ROOT, "tests/evm/sibling/SiblingCases.sol"),
                      "--solc", ensure_solc("0.8.24"), "--solc-working-dir", ROOT,
                      "--solc-args", "--base-path . --allow-paths ."],
                     capture_output=True, text=True, cwd=ROOT)
data = json.loads(out.stdout.strip().splitlines()[-1])
assert not data["errors"], data["errors"]
hits = {(c["contract"], c["function"].split("(")[0]): c for c in data["custom"] if c["check"] == "solscan-unprotected-sibling"}

# (contract, function) -> expected (impact, patterns) ; None = must NOT be flagged
EXPECT = {
    ("VulnerableVault", "execute"): ("High", {"low-level-call"}),
    ("VulnerableVault", "approveSpender"): ("High", {"approval"}),
    ("VulnerableVault", "delegateTo"): ("High", {"delegatecall"}),
    ("VulnerableVault", "deposit"): None,
    ("VulnerableVault", "withdraw"): None,
    ("VulnerableVault", "setFee"): None,
    ("SafeVault", "execute"): None,
    ("SafeVault", "approveSpender"): None,
    ("SafeVault", "delegateTo"): None,
    ("NoAuthForwarder", "forward"): None,
    ("BenignTokenVault", "deposit"): None,
    ("BenignTokenVault", "withdraw"): None,
    ("PerUserDelegate", "delegate"): None,
    ("CallbackNoValue", "notify"): ("Medium", {"callback"}),
    ("AllowlistedExecutor", "execute"): None,                               # target validated by an allowlist
    ("FixedSpenderApprover", "pay"): ("Medium", {"approval-token"}),        # fixed spender: never High
}
fails = 0
for key, want in EXPECT.items():
    got = hits.get(key)
    if want is None:
        ok = got is None
        print(f"{'ok  ' if ok else 'FAIL'} {key[0]}.{key[1]:16} niet gemeld {'' if ok else '-> ' + got['impact']}")
    else:
        ok = got is not None and got["impact"] == want[0] and set(got["patterns"]) == want[1]
        print(f"{'ok  ' if ok else 'FAIL'} {key[0]}.{key[1]:16} verwacht {want[0]}/{sorted(want[1])} kreeg "
              f"{(got['impact'], got['patterns']) if got else None}")
    fails += not ok
extra = [k for k in hits if k not in EXPECT]
if extra:
    print("FAIL onverwachte meldingen:", extra); fails += 1
print(f"\n{len(EXPECT) - fails}/{len(EXPECT)} checks ok" if not fails else f"\n{fails} FAIL")
sys.exit(1 if fails else 0)
