// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// BENCHMARK (reconstruction, local only). Models the real-world "missing access control on a mint path" class —
// e.g. the TSURU (2024) incident where an unprotected callback minted tokens to the caller (OpenZeppelin, "Web3
// Security Auditor's 2024 Rewind"). This is a faithful RECONSTRUCTION of the pattern, not the live bytecode:
// it validates that the scanner's access-control detector and the ATTACKER-PROFIT invariant catch this hack class.
// No attack is carried out; the mint simply credits the caller, which the detector/invariant then flags.

contract FreeMintToken {
    string public name = "Recon";
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;
    address public owner;
    constructor() { owner = msg.sender; }

    function transfer(address to, uint256 a) external returns (bool) { balanceOf[msg.sender]-=a; balanceOf[to]+=a; return true; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s]=a; return true; }
    function transferFrom(address f, address t, uint256 a) external returns (bool) { allowance[f][msg.sender]-=a; balanceOf[f]-=a; balanceOf[t]+=a; return true; }

    // Intended to be called only by the wrapper during a legitimate deposit, but left PUBLIC with no caller check:
    // an unprivileged account can mint itself unlimited tokens. This is the access-control gap the scanner targets.
    function onDepositReceived(address to, uint256 amount) public returns (bytes4) {
        balanceOf[to] += amount;        // writes value state, no onlyOwner / no msg.sender == wrapper check
        totalSupply += amount;
        return this.onDepositReceived.selector;
    }

    // a correctly-gated admin function exists alongside it -> there IS an authority model, so the ungated
    // mint path is an oversight (this is also what the `unprotected-sibling` detector keys on).
    function setOwner(address o) external { require(msg.sender == owner, "owner"); owner = o; }
}
