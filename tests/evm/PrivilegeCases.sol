// SPDX-License-Identifier: MIT
// Privilege-filter regression cases for SolScan-EVM. NOT for deployment.
pragma solidity ^0.8.24;

import {Ownable} from "../../samples/evm/lib/Ownable.sol";
import {AccessControl, Initializable} from "../../samples/evm/lib/AccessControl.sol";

// Modifier with a NON-descriptive name, defined in another (base) contract.
abstract contract GovBase {
    address internal gov;
    modifier checked() {
        require(msg.sender == gov, "not gov");
        _;
    }
    function _assertGov() internal view {
        if (msg.sender != gov) revert("not gov");
    }
}

library LibA {
    function pubPath(uint256 x) internal pure returns (uint256) { return x + 1; }
    function adminPath(uint256 x) internal pure returns (uint256) { return x * 2; }
}

abstract contract Pausable {
    bool internal paused;
    modifier whenNotPaused() { require(!paused, "paused"); _; }
}

abstract contract ReentrancyGuard {
    uint256 private _status = 1;
    modifier nonReentrant() { require(_status == 1, "reentrant"); _status = 2; _; _status = 1; }
}

contract PrivilegeCases is GovBase, Ownable, AccessControl, Initializable, Pausable, ReentrancyGuard {
    bytes32 public constant ADMIN = keccak256("ADMIN");
    uint256 public fee;
    uint256 public userCounter;

    constructor() Ownable(msg.sender) { gov = msg.sender; }

    // ---- must be ADMIN (not externally reachable) ----
    function adminViaOwnable(uint256 f) external onlyOwner { fee = f; }                      // inherited OZ Ownable
    function adminViaRole(uint256 f) external onlyRole(ADMIN) { fee = f; }                   // inherited OZ AccessControl
    function adminViaOddModifier(uint256 f) external checked { fee = f; }                    // custom modifier in base
    function adminViaInlineHasRole(uint256 f) external {                                     // inline role check
        require(hasRole(ADMIN, msg.sender), "no role");
        fee = f;
    }
    function adminViaPrivateCheck(uint256 f) external { _assertGov(); fee = f; }            // internal sender check
    function adminCallsHelper(uint256 f) external onlyOwner { _setFeeHelper(f); }

    // ---- must be INIT / CONSTRUCTOR ----
    function initialize(address g) external initializer { gov = g; }

    // ---- must be EXTERNAL (ordinary user) ----
    function userAction() external whenNotPaused nonReentrant { userCounter += 1; }         // non-access modifiers
    function userCallsBump() external { _bump(); }

    // ---- per-user checks: must stay EXTERNAL (not admin) ----
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowance;
    struct Position { address owner; uint256 size; }
    mapping(uint256 => Position) public positions;
    mapping(address => bool) public isOperator;
    address public pendingOwner;

    function userWithdraw(uint256 amt) external {
        require(balances[msg.sender] >= amt, "low");
        balances[msg.sender] -= amt;
    }
    function userTransferFrom(address from, uint256 amt) external {
        require(allowance[from][msg.sender] >= amt, "allowance");
        allowance[from][msg.sender] -= amt;
    }
    function userClosePosition(uint256 id) external {
        require(positions[id].owner == msg.sender, "not yours");
        delete positions[id];
    }
    // ---- authority mapping / pending owner: must be ADMIN ----
    function adminViaOperatorMap(uint256 f) external { require(isOperator[msg.sender], "op"); fee = f; }
    function acceptOwnershipLike() external { require(msg.sender == pendingOwner, "pending"); gov = msg.sender; }

    // ---- library calls ----
    function userUsesLib() external { userCounter = LibA.pubPath(userCounter); }          // -> LibA.pubPath reachable
    function adminUsesLib() external onlyOwner { fee = LibA.adminPath(fee); }             // -> LibA.adminPath admin-only

    // internal helpers
    function _setFeeHelper(uint256 f) internal { fee = f; }   // only reachable from admin -> internal-only
    function _bump() internal { userCounter += 1; }           // reachable from userCallsBump -> external
}
