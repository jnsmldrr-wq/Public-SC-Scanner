// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// TEST FIXTURE for the ATTACKER-PROFIT invariant (local test-suite only; never deployed).
// Each Vuln* contract lets an UNPRIVILEGED caller gain something it should not; the Safe* ones must stay clean.
// The invariant here is a self-contained copy of the three ATTACKER-PROFIT checks (value / allowance / role),
// so the test validates the checks directly without a full fork campaign.

interface IERC20Min {
    function balanceOf(address) external view returns (uint256);
    function allowance(address, address) external view returns (uint256);
    function approve(address, uint256) external returns (bool);
    function transfer(address, uint256) external returns (bool);
}

// A minimal ERC20 the vault holds, so allowance/balance checks are meaningful.
contract ToyToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    constructor(address to, uint256 amt) { balanceOf[to] = amt; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }
    function transfer(address to, uint256 a) external returns (bool) { balanceOf[msg.sender] -= a; balanceOf[to] += a; return true; }
    function transferFrom(address f, address to, uint256 a) external returns (bool) {
        allowance[f][msg.sender] -= a; balanceOf[f] -= a; balanceOf[to] += a; return true;
    }
}

/// BUG: an ungated function makes the vault approve the caller over the vault's own token balance.
contract VulnApprove {
    ToyToken public token;
    constructor(ToyToken t) { token = t; }
    function pullPermission() external { token.approve(msg.sender, type(uint256).max); }   // anyone -> allowance
}

/// BUG: an ungated function grants the caller DEFAULT_ADMIN_ROLE (role escalation).
contract VulnRole {
    mapping(bytes32 => mapping(address => bool)) public roles;
    function hasRole(bytes32 r, address a) external view returns (bool) { return roles[r][a]; }
    function claimAdmin() external { roles[bytes32(0)][msg.sender] = true; }               // anyone -> admin
}

/// BUG: an ungated function mints the caller free tokens (value out of nothing).
contract VulnFreeValue {
    ToyToken public token;
    constructor(ToyToken t) { token = t; }
    function freebie(uint256 amt) external { token.transfer(msg.sender, amt); }             // anyone -> free tokens
}

/// Safe: approvals/roles only via an owner gate; no free value.
contract SafeVault {
    address public owner;
    ToyToken public token;
    mapping(bytes32 => mapping(address => bool)) public roles;
    constructor(ToyToken t) { owner = msg.sender; token = t; }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function hasRole(bytes32 r, address a) external view returns (bool) { return roles[r][a]; }
    function approveSpender(address s, uint256 a) external onlyOwner { token.approve(s, a); }
    function grantAdmin(address a) external onlyOwner { roles[bytes32(0)][a] = true; }
}
