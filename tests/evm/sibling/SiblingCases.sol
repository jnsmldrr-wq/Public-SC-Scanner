// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// TEST FIXTURE for the `unprotected-sibling` detector and the ATTACKER-PROFIT invariant.
// Deliberately flawed toy contracts; they exist only inside the SolScan test-suite (local, never deployed).
// "Vulnerable*" must be flagged; "Safe*" / "Benign*" / "NoAuth*" / "PerUser*" must NOT be.

interface IERC20T {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address a) external view returns (uint256);
}

interface ICallback { function ping() external; }

/// Gated sibling (setFee) + ungated functions that make the contract itself call / approve / delegatecall
/// whatever address the caller passes in. The contract holds user deposits, so value is reachable.
contract VulnerableVault {
    address public owner;
    uint256 public fee;
    IERC20T public immutable token;
    mapping(address => uint256) public deposits;

    constructor(address t) { owner = msg.sender; token = IERC20T(t); }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }

    function setFee(uint256 f) external onlyOwner { fee = f; }

    function deposit(uint256 amt) external {
        token.transferFrom(msg.sender, address(this), amt);
        deposits[msg.sender] += amt;
    }
    function withdraw(uint256 amt) external {
        deposits[msg.sender] -= amt;
        token.transfer(msg.sender, amt);
    }

    // (a) arbitrary call with the vault as msg.sender
    function execute(address target, bytes calldata data) external returns (bytes memory r) {
        (bool ok, bytes memory ret) = target.call(data);
        require(ok, "call failed");
        r = ret;
    }
    // (b) the vault approves a caller-chosen spender on a caller-chosen token
    function approveSpender(address tok, address spender, uint256 amount) external {
        IERC20T(tok).approve(spender, amount);
    }
    // (c) delegatecall into a caller-chosen implementation
    function delegateTo(address impl, bytes calldata data) external {
        (bool ok, ) = impl.delegatecall(data);
        require(ok, "delegatecall failed");
    }
}

/// Same functions, all gated: nothing to report.
contract SafeVault {
    address public owner;
    IERC20T public immutable token;
    mapping(address => uint256) public deposits;
    constructor(address t) { owner = msg.sender; token = IERC20T(t); }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setFee(uint256) external onlyOwner {}
    function deposit(uint256 amt) external { token.transferFrom(msg.sender, address(this), amt); deposits[msg.sender] += amt; }
    function execute(address target, bytes calldata data) external onlyOwner returns (bytes memory r) {
        (bool ok, bytes memory ret) = target.call(data); require(ok); r = ret;
    }
    function approveSpender(address tok, address spender, uint256 amount) external onlyOwner { IERC20T(tok).approve(spender, amount); }
    function delegateTo(address impl, bytes calldata data) external onlyOwner { (bool ok, ) = impl.delegatecall(data); require(ok); }
}

/// No gated function at all (a plain forwarder): there is no "sibling" to compare with -> not flagged.
contract NoAuthForwarder {
    function forward(address target, bytes calldata data) external returns (bytes memory r) {
        (bool ok, bytes memory ret) = target.call(data); require(ok); r = ret;
    }
}

/// Gated sibling + the normal deposit pattern with a caller-chosen token (transferFrom from msg.sender): benign.
contract BenignTokenVault {
    address public owner;
    mapping(address => mapping(address => uint256)) public balances;
    constructor() { owner = msg.sender; }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setOwner(address o) external onlyOwner { owner = o; }
    function deposit(address tok, uint256 amt) external {
        IERC20T(tok).transferFrom(msg.sender, address(this), amt);
        balances[tok][msg.sender] += amt;
    }
    function withdraw(address tok, uint256 amt) external {
        balances[tok][msg.sender] -= amt;
        IERC20T(tok).transfer(msg.sender, amt);
    }
}

/// Per-user delegation (like ERC20Votes.delegate): only writes the caller's own slot -> not flagged.
contract PerUserDelegate {
    address public owner;
    mapping(address => address) public delegates;
    constructor() { owner = msg.sender; }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setOwner(address o) external onlyOwner { owner = o; }
    function delegate(address to) external { delegates[msg.sender] = to; }
}

/// Gated sibling + an ungated callback to a caller-chosen address, in a contract that moves NO value:
/// reported (callback surface) but only Medium / Low-confidence, never High.
contract CallbackNoValue {
    address public owner;
    uint256 public pings;
    constructor() { owner = msg.sender; }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setOwner(address o) external onlyOwner { owner = o; }
    function notify(address target) external { ICallback(target).ping(); pings++; }
}

/// Caller-supplied target must be on an owner-maintained allowlist (require on a mapping): validated -> not flagged.
contract AllowlistedExecutor {
    address public owner;
    mapping(address => bool) public allowedTarget;
    constructor() { owner = msg.sender; }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setAllowed(address t, bool a) external onlyOwner { allowedTarget[t] = a; }
    function execute(address target, bytes calldata data) external {
        require(allowedTarget[target], "not allowed");
        (bool ok, ) = target.call(data); require(ok);
    }
}

/// The contract approves a FIXED protocol-owned spender on a caller-chosen token: reported, but only as
/// "approval-token" (Medium / Low confidence), never High.
contract FixedSpenderApprover {
    address public owner;
    address public immutable feeSink;
    IERC20T public immutable base;
    constructor(address s, address b) { owner = msg.sender; feeSink = s; base = IERC20T(b); }
    modifier onlyOwner() { require(msg.sender == owner, "owner"); _; }
    function setOwner(address o) external onlyOwner { owner = o; }
    function deposit(uint256 a) external { base.transferFrom(msg.sender, address(this), a); }
    function pay(address tok, uint256 a) external { IERC20T(tok).approve(feeSink, a); }
}
