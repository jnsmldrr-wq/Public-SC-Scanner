"""Positive-control test for the ATTACKER-PROFIT checks (run: python3 tests/evm/test_attacker_profit.py).

Deploys the fixture with Foundry's forge `script`-free unit runner via a tiny harness .sol compiled on the fly,
then asserts: the three Vuln* contracts each trip exactly the check they should, and the Safe* one trips none.
"""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solscan.evm.slither_runner import evm_python  # noqa
import shutil

FORGE = shutil.which("forge") or os.path.expanduser("~/.foundry/bin/forge")
WORK = os.path.join(ROOT, "fuzz-work", "_attacker_selftest")
os.makedirs(os.path.join(WORK, "test"), exist_ok=True)
STD = os.path.join(ROOT, "fuzz-work", "_lib", "forge-std")

open(os.path.join(WORK, "foundry.toml"), "w").write(
    '[profile.default]\nsrc="test"\ntest="test"\nlibs=["../_lib"]\nremappings=["forge-std/=../_lib/forge-std/src/"]\n')
shutil.copy(os.path.join(ROOT, "tests/evm/attacker/AttackerProfitCases.sol"), os.path.join(WORK, "test", "Cases.sol"))

open(os.path.join(WORK, "test", "SelfTest.t.sol"), "w").write(r'''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import {Test} from "forge-std/Test.sol";
import "./Cases.sol";

contract SelfTest is Test {
    // the three ATTACKER-PROFIT checks, applied to an arbitrary target + token + unprivileged actor
    function _allowanceClean(address target, address token, address a) internal view returns (bool) {
        return IERC20Min(token).allowance(target, a) == 0;
    }
    function _roleClean(address target, address a) internal view returns (bool) {
        (bool ok, bytes memory d) = target.staticcall(abi.encodeWithSignature("owner()"));
        if (ok && d.length == 32 && abi.decode(d,(address)) == a) return false;
        (ok, d) = target.staticcall(abi.encodeWithSignature("hasRole(bytes32,address)", bytes32(0), a));
        if (ok && d.length == 32 && abi.decode(d,(bool))) return false;
        return true;
    }

    function test_vuln_approve_trips_allowance() public {
        ToyToken tok = new ToyToken(address(0), 0);
        VulnApprove v = new VulnApprove(tok);
        tok = v.token();
        // give the vault some balance so an allowance is meaningful
        ToyToken t2 = new ToyToken(address(v), 1000 ether); v = new VulnApprove(t2);
        address actor = makeAddr("actor");
        assertTrue(_allowanceClean(address(v), address(t2), actor), "clean before");
        vm.prank(actor); v.pullPermission();
        assertFalse(_allowanceClean(address(v), address(t2), actor), "CHECK FAILED: allowance not detected");
    }
    function test_vuln_role_trips_role() public {
        VulnRole v = new VulnRole();
        address actor = makeAddr("actor");
        assertTrue(_roleClean(address(v), actor), "clean before");
        vm.prank(actor); v.claimAdmin();
        assertFalse(_roleClean(address(v), actor), "CHECK FAILED: role escalation not detected");
    }
    function test_vuln_free_value_trips_value() public {
        ToyToken t = new ToyToken(address(this), 1000 ether);
        VulnFreeValue v = new VulnFreeValue(t);
        t.transfer(address(v), 1000 ether);
        address actor = makeAddr("actor");
        uint256 before = t.balanceOf(actor);           // valueIn = 0 for this actor
        vm.prank(actor); v.freebie(5 ether);
        assertGt(t.balanceOf(actor) - before, 0, "CHECK FAILED: free value not observed");  // out > in(0)
    }
    function test_safe_vault_clean() public {
        ToyToken t = new ToyToken(address(this), 1000 ether);
        SafeVault s = new SafeVault(t);
        t.transfer(address(s), 1000 ether);
        address actor = makeAddr("actor");
        // an unprivileged actor cannot gain allowance or role, and the gated calls revert for it
        vm.prank(actor); (bool ok1,) = address(s).call(abi.encodeWithSignature("approveSpender(address,uint256)", actor, 1e18));
        vm.prank(actor); (bool ok2,) = address(s).call(abi.encodeWithSignature("grantAdmin(address)", actor));
        assertFalse(ok1, "safe approve should be gated");
        assertFalse(ok2, "safe grant should be gated");
        assertTrue(_allowanceClean(address(s), address(t), actor) && _roleClean(address(s), actor), "safe must stay clean");
    }
}
''')
env = dict(os.environ, FUZZ_RPC_URL="x")
r = subprocess.run([FORGE, "test", "--match-contract", "SelfTest", "-vv"], cwd=WORK, capture_output=True, text=True)
print(r.stdout[-1600:])
sys.exit(0 if r.returncode == 0 else 1)
