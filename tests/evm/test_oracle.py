"""Oracle-safety regression test (run: python3 tests/evm/test_oracle.py). Protected variants must NOT fire."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solscan.evm.slither_runner import run_slither, ensure_solc

EXPECT = {
    "UnprotectedSpotV2": {"EVM-ORACLE-SPOT", "EVM-ORACLE-SINGLE"},
    "ProtectedTwapV3": set(),
    "SwapOnlyRouterUse": set(),
    "UnprotectedLatestAnswer": {"EVM-ORACLE-FRESH", "EVM-ORACLE-SINGLE"},
    "UnprotectedRoundData": {"EVM-ORACLE-FRESH", "EVM-ORACLE-SINGLE"},
    "ProtectedChainlink": set(),
    "ProtectedChainlinkViaHelper": set(),
    "ProtectedTwoSources": set(),
    "IntervalOnlyChainlink": {"EVM-ORACLE-FRESH"},   # averaging window counts as time-averaging → no SINGLE
}
d = os.path.join(ROOT, "tests/evm/oracle")
raw = run_slither(os.path.join(d, "OracleCases.sol"), solc=ensure_solc("0.8.24"), working_dir=d,
                  solc_args="--base-path . --allow-paths .")
got = {}
for f, meta in raw.findings:
    if f.rule_id.startswith("EVM-ORACLE"):
        for c, _ in meta["functions"]:
            got.setdefault(c, set()).add(f.rule_id)
fails = 0
for c, want in EXPECT.items():
    ok = got.get(c, set()) == want
    fails += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {c:28} want={sorted(want)} got={sorted(got.get(c, set()))}")
raw2 = run_slither(os.path.join(d, "NoOracle.sol"), solc=ensure_solc("0.8.24"), working_dir=d)
ok = not raw2.oracle_coverage
fails += not ok
print(f"{'ok  ' if ok else 'FAIL'} NoOracle                     coverage leeg (oracle-checks n.v.t.)")
print("ALLE ORACLE-TESTS GESLAAGD" if not fails else f"{fails} GEFAALD")
sys.exit(1 if fails else 0)
