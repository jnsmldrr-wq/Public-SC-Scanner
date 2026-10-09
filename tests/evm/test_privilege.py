"""Regression test for the SolScan-EVM privilege filter (run: python3 tests/evm/test_privilege.py)."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solscan.evm.slither_runner import evm_python, ensure_solc, WORKER

EXPECT = {
    "adminViaOwnable(uint256)": "admin",
    "adminViaRole(uint256)": "admin",
    "adminViaOddModifier(uint256)": "admin",
    "adminViaInlineHasRole(uint256)": "admin",
    "adminViaPrivateCheck(uint256)": "admin",
    "adminCallsHelper(uint256)": "admin",
    "initialize(address)": "init",
    "constructor()": "constructor",
    "userAction()": "external",
    "userCallsBump()": "external",
    "userWithdraw(uint256)": "external",
    "userTransferFrom(address,uint256)": "external",
    "userClosePosition(uint256)": "external",
    "adminViaOperatorMap(uint256)": "admin",
    "acceptOwnershipLike()": "admin",
    "_setFeeHelper(uint256)": ("internal", False),   # internal, NOT reachable unprotected
    "_bump()": ("internal", True),                   # internal, reachable via userCallsBump
}

out = subprocess.run([evm_python(), WORKER, os.path.join(ROOT, "tests/evm/PrivilegeCases.sol"),
                      "--solc", ensure_solc("0.8.24"), "--solc-working-dir", ROOT,
                      "--solc-args", "--base-path . --allow-paths ."],
                     capture_output=True, text=True, cwd=ROOT)
data = json.loads(out.stdout.strip().splitlines()[-1])
assert not data["errors"], data["errors"]
acc = data["access"]["PrivilegeCases"]
fails = 0
for sig, want in EXPECT.items():
    rec = acc.get(sig)
    if rec is None:
        print(f"FAIL {sig}: not in access map"); fails += 1; continue
    if isinstance(want, tuple):
        ok = rec["kind"] == want[0] and bool(rec.get("reachable_unprotected")) == want[1]
        got = (rec["kind"], rec.get("reachable_unprotected"))
    else:
        ok, got = rec["kind"] == want, rec["kind"]
    print(f"{'ok  ' if ok else 'FAIL'} {sig:34} want={want!s:18} got={got!s:18} gates={rec['gates']}")
    fails += not ok
# library functions: reachability across contracts (library_calls)
lib = data["access"].get("LibA", {})
for sig, want in {"pubPath(uint256)": True, "adminPath(uint256)": False}.items():
    rec = lib.get(sig, {})
    ok = rec.get("kind") == "internal" and bool(rec.get("reachable_unprotected")) == want
    print(f"{'ok  ' if ok else 'FAIL'} LibA.{sig:29} want=reachable={want!s:6} got={rec.get('kind')},{rec.get('reachable_unprotected')} via={rec.get('reachable_via')}")
    fails += not ok
# a pure admin function must never be marked externally reachable
assert all(acc[s]["kind"] != "external" for s, w in EXPECT.items() if w == "admin"), "admin marked external!"
print("ALLE TESTS GESLAAGD" if not fails else f"{fails} TEST(S) GEFAALD")
sys.exit(1 if fails else 0)
