"""Positive-control test for Module 4 (time): the over-release bug is only reachable after time advances."""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FORGE = shutil.which("forge") or os.path.expanduser("~/.foundry/bin/forge")
WORK = os.path.join(ROOT, "fuzz-work", "_time_selftest"); os.makedirs(os.path.join(WORK, "test"), exist_ok=True)
open(os.path.join(WORK, "foundry.toml"), "w").write('[profile.default]\nsrc="test"\ntest="test"\nlibs=["../_lib"]\nremappings=["forge-std/=../_lib/forge-std/src/"]\n')
shutil.copy(os.path.join(ROOT, "tests/evm/time/TimeCases.sol"), os.path.join(WORK, "test", "Cases.sol"))
open(os.path.join(WORK, "test", "SelfTest.t.sol"), "w").write(r'''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Test} from "forge-std/Test.sol";
import "./Cases.sol";
contract SelfTest is Test {
    BuggyVesting bug; SafeVesting safe;
    function setUp() public { vm.warp(1_000_000); bug = new BuggyVesting(1 ether, 100 ether); safe = new SafeVesting(1 ether, 100 ether); }
    // invariant: claimable must never exceed the allocation
    function test_no_time_no_bug() public view {
        assertLe(bug.claimable(), bug.allocation(), "at t0 nothing is over-released");
    }
    function test_timeTravel_reaches_overrelease() public {
        vm.warp(block.timestamp + 365 days);                 // the time fuzz action
        assertGt(bug.claimable(), bug.allocation(), "TIME: over-release reachable only after warp (finding)");
        assertEq(safe.claimable(), safe.allocation(), "safe vesting stays capped");
    }
}
''')
r = subprocess.run([FORGE, "test", "--match-contract", "SelfTest", "-vv"], cwd=WORK, capture_output=True, text=True)
print(r.stdout[-1200:]); print(r.stderr[-300:] if r.returncode else "")
sys.exit(0 if r.returncode == 0 else 1)
