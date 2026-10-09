"""Positive-control test for Module 3 ORACLE-GUARD (run: python3 tests/evm/test_oracle_guard.py).

Mechanism: a Chainlink-shaped feed is forced to {fresh, stale, zero}. The ORACLE-GUARD rule is:
on a clearly-invalid reading (zero answer, or stale beyond MAX_AGE), a price read that a value action depends on
MUST revert. The guarded consumer reverts; the unguarded one returns a usable price -> finding.
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORGE = shutil.which("forge") or os.path.expanduser("~/.foundry/bin/forge")
WORK = os.path.join(ROOT, "fuzz-work", "_oracle_guard_selftest")
os.makedirs(os.path.join(WORK, "test"), exist_ok=True)
open(os.path.join(WORK, "foundry.toml"), "w").write(
    '[profile.default]\nsrc="test"\ntest="test"\nlibs=["../_lib"]\nremappings=["forge-std/=../_lib/forge-std/src/"]\n')
shutil.copy(os.path.join(ROOT, "tests/evm/oracle_guard/OracleGuardCases.sol"), os.path.join(WORK, "test", "Cases.sol"))
open(os.path.join(WORK, "test", "SelfTest.t.sol"), "w").write(r'''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Test} from "forge-std/Test.sol";
import "./Cases.sol";

contract SelfTest is Test {
    ToyFeed feed; UnguardedConsumer unguarded; GuardedConsumer guarded;
    function setUp() public {
        vm.warp(1_000_000);
        feed = new ToyFeed();
        feed.set(2000e8, block.timestamp, 1);          // a fresh, valid reading
        unguarded = new UnguardedConsumer(feed);
        guarded = new GuardedConsumer(feed);
    }
    function _reads(address c) internal view returns (bool ok, uint256 p) {
        (bool s, bytes memory d) = c.staticcall(abi.encodeWithSignature("price()"));
        ok = s; if (s && d.length >= 32) p = abi.decode(d, (uint256));
    }
    function test_fresh_both_ok() public view {
        (bool u,) = _reads(address(unguarded)); (bool g,) = _reads(address(guarded));
        assertTrue(u && g, "fresh feed must be accepted by both");
    }
    function test_stale_unguarded_flagged_guarded_safe() public {
        feed.set(2000e8, block.timestamp - 2 hours, 1);   // stale beyond MAX_AGE
        (bool u, uint256 p) = _reads(address(unguarded));
        (bool g,) = _reads(address(guarded));
        assertTrue(u && p == 2000e8, "ORACLE-GUARD: unguarded consumed a STALE price (finding)");
        assertFalse(g, "guarded consumer must revert on stale");
    }
    function test_zero_unguarded_flagged_guarded_safe() public {
        feed.set(0, block.timestamp, 1);                  // zero/invalid answer
        (bool u, uint256 p) = _reads(address(unguarded));
        (bool g,) = _reads(address(guarded));
        assertTrue(u && p == 0, "ORACLE-GUARD: unguarded consumed a ZERO price (finding)");
        assertFalse(g, "guarded consumer must revert on zero");
    }
}
''')
r = subprocess.run([FORGE, "test", "--match-contract", "SelfTest", "-vv"], cwd=WORK, capture_output=True, text=True)
print(r.stdout[-1500:]); print(r.stderr[-400:] if r.returncode else "")
sys.exit(0 if r.returncode == 0 else 1)
