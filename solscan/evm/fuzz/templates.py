"""Solidity templates for the generated Foundry invariant suite.

Placeholders are __NAME__ and are filled by generator.py. Every handler:
  * uses local test actors (makeAddr) funded with forge-std `deal` on the fork — no real keys;
  * wraps each target call in try/catch so a revert is just "action not possible";
  * keeps ghost accounting (value in / value out per actor) and success counters per action;
  * offers tryPrivileged(): calls a function meant to be gated as an unauthorized actor.
"""

COMMON = r"""
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import {Test} from "forge-std/Test.sol";
import {Vm} from "forge-std/Vm.sol";

interface IERC20Min {
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function allowance(address owner, address spender) external view returns (uint256);
}

/// forge-std `deal` behind an external call, so a token whose balance slot cannot be found
/// shows up as a caught failure instead of aborting setUp.
contract Funder is Test {
    function fund(address token, address to, uint256 amount) external {
        try this.dealExt(token, to, amount) {} catch {
            // Rebasing share tokens (Lido stETH) have no plain balance slot: get them the way a user does,
            // by staking ETH via submit(); capped to stay under Lido's staking rate limit.
            uint256 eth = amount > 1000 ether ? 1000 ether : amount;
            vm.deal(to, eth);
            vm.prank(to);
            (bool ok, ) = token.call{value: eth}(abi.encodeWithSignature("submit(address)", address(0)));
            require(ok, "fund: deal and submit() both failed");
        }
    }

    function dealExt(address token, address to, uint256 amount) external {
        deal(token, to, amount);
    }
}

abstract contract HandlerBase is Test {
    address public immutable TARGET;
    Funder internal funder;
    address[] public actors;
    address internal actor;
    mapping(address => uint256) public valueIn;     // value the actor put into the target
    mapping(address => uint256) public valueOut;    // value the actor took out of the target
    mapping(address => uint256) public opsOf;       // successful value-moving calls per actor
    mapping(string => uint256) public okCalls;      // successful calls per action
    mapping(string => uint256) public tryCalls;     // attempted calls per action
    string[] public actionNames;
    mapping(address => bool) public fundingFailed;
    mapping(string => string) public lastRevert;    // last revert reason per action (coverage diagnostics)

    // ACCESS invariant bookkeeping
    bytes4[] internal privSelectors;
    uint8[] internal privArgTypes;   // per selector: number of static words in the low byte
    string[] internal privNames;
    bool public accessViolation;
    string public accessViolationFn;
    address public accessViolationActor;

    constructor(address target, uint256 nActors) {
        TARGET = target;
        funder = new Funder();
        for (uint256 i = 0; i < nActors; i++) {
            actors.push(makeAddr(string(abi.encodePacked("actor", vm.toString(i)))));
        }
    }

    function _pick(uint256 seed) internal returns (address) {
        actor = actors[seed % actors.length];
        return actor;
    }

    function _fund(address token, address to, uint256 amount) internal {
        try funder.fund{gas: 8_000_000}(token, to, amount) {} catch { fundingFailed[token] = true; }
    }

    function _approve(address token, address spender) internal {
        (bool ok,) = token.call(abi.encodeWithSignature("approve(address,uint256)", spender, type(uint256).max));
        ok;
    }

    function _bal(address token, address who) internal view returns (uint256) {
        return IERC20Min(token).balanceOf(who);
    }

    function _count(string memory name, bool ok) internal {
        if (tryCalls[name] == 0 && okCalls[name] == 0) actionNames.push(name);
        tryCalls[name]++;
        if (ok) okCalls[name]++;
    }

    function _fail(string memory name, bytes memory r) internal {
        _count(name, false);
        lastRevert[name] = _reason(r);
    }

    function _reason(bytes memory r) internal pure returns (string memory) {
        if (r.length >= 68 && bytes4(r) == 0x08c379a0) {
            assembly { r := add(r, 4) }
            return abi.decode(r, (string));
        }
        if (r.length >= 4) return vm.toString(bytes4(r));
        return "revert-zonder-reden";
    }

    /// 1e9 whole tokens per actor, scaled to the token's decimals (fallback 18).
    function _fundAmount(address token) internal view returns (uint256) {
        (bool ok, bytes memory d) = token.staticcall(abi.encodeWithSignature("decimals()"));
        uint256 dec = ok && d.length >= 32 ? abi.decode(d, (uint256)) : 18;
        if (dec > 30) dec = 18;
        return 1e9 * 10 ** dec;
    }

    /// test hook for positive controls of ledger-based invariants (never in targetSelector, so never fuzzed)
    function ctlBumpOut(address a, uint256 x) external { valueOut[a] += x; }

    /// Module 4 (time): advance block time and number as a fuzz action, so interest, liquidations, bad debt,
    /// vesting and claim-delays become reachable. Bounded to 90 days per step. Enabled under --warp.
    function warpTime(uint256 seed) external {
        uint256 dt = bound(seed, 1, 90 days);
        vm.warp(block.timestamp + dt);
        vm.roll(block.number + dt / 12);
        _count("warpTime", true);
    }

    function actorCount() external view returns (uint256) { return actors.length; }
    function actionCount() external view returns (uint256) { return actionNames.length; }

    /// Call a function that is meant to be owner/role-only, as an unauthorized test actor,
    /// with fuzzed static arguments. Success = ACCESS violation.
    function tryPrivileged(uint256 actorSeed, uint256 which, bytes32 w0, bytes32 w1, bytes32 w2, bytes32 w3) external {
        if (privSelectors.length == 0) return;
        uint256 i = which % privSelectors.length;
        address a = _pick(actorSeed);
        uint256 n = privArgTypes[i];
        bytes32[4] memory w = [w0, w1, w2, w3];
        bytes memory data = abi.encodePacked(privSelectors[i]);
        for (uint256 k = 0; k < n && k < 4; k++) data = abi.encodePacked(data, w[k]);
        for (uint256 k = 4; k < n; k++) data = abi.encodePacked(data, bytes32(0));
        vm.prank(a);
        (bool ok,) = TARGET.call(data);
        _count("tryPrivileged", ok);
        if (ok && !accessViolation) {
            accessViolation = true;
            accessViolationFn = privNames[i];
            accessViolationActor = a;
        }
    }
}
"""

# --------------------------------------------------------------------------- lender (Morpho-Blue style)
LENDER_HANDLER = r"""
interface ILender {
__STRUCT__
    function supply(MarketParams memory, uint256, uint256, address, bytes memory) external returns (uint256, uint256);
    function withdraw(MarketParams memory, uint256, uint256, address, address) external returns (uint256, uint256);
    function borrow(MarketParams memory, uint256, uint256, address, address) external returns (uint256, uint256);
    function repay(MarketParams memory, uint256, uint256, address, bytes memory) external returns (uint256, uint256);
    function supplyCollateral(MarketParams memory, uint256, address, bytes memory) external;
    function withdrawCollateral(MarketParams memory, uint256, address, address) external;
    function liquidate(MarketParams memory, address, uint256, uint256, bytes memory) external returns (uint256, uint256);
__EXTRA_IFACE__
    function market(bytes32) external view returns (uint128, uint128, uint128, uint128, uint128, uint128);
    function position(bytes32, address) external view returns (uint256, uint128, uint128);
}

interface IPriceOracle {
    function price() external view returns (uint256);
}

contract Handler is HandlerBase {
    ILender internal immutable T;
    ILender.MarketParams[] internal mkts;
    bytes32[] public ids;
    address[] public supplierRole;    // per market: who may supply (0 = anyone); a simulated privileged role
    address[] public collateralRole;  // per market: provider that must deposit collateral on behalf (0 = the user)
    address[] public tokens;          // distinct loan + collateral tokens
    bool public immutable WARP;
    uint256 internal constant SCALE = 1e36;   // Morpho oracle price scale
    uint256 internal constant FUND = __FUND__;

    constructor(address target, uint256 nActors, bool warp_) HandlerBase(target, nActors) {
        T = ILender(target);
        WARP = warp_;
__MARKETS__
        for (uint256 m = 0; m < mkts.length; m++) {
            _addToken(mkts[m].loanToken);
            _addToken(mkts[m].collateralToken);
            address wl = supplierRole[m];
            if (wl != address(0) && !_isActor(wl)) actors.push(wl);   // whitelisted supplier (simulated role)
        }
        for (uint256 m = 0; m < mkts.length; m++) {          // a simulated provider approves the target itself
            if (collateralRole[m] != address(0)) {
                vm.prank(collateralRole[m]);
                _approve(mkts[m].collateralToken, target);
            }
        }
        for (uint256 a = 0; a < actors.length; a++) {
            for (uint256 t = 0; t < tokens.length; t++) {
                _fund(tokens[t], actors[a], _fundAmount(tokens[t]));
                vm.prank(actors[a]);
                _approve(tokens[t], target);
            }
        }
__PRIV__
    }

    function _addToken(address t) internal {
        for (uint256 i = 0; i < tokens.length; i++) if (tokens[i] == t) return;
        tokens.push(t);
    }

    function _isActor(address x) internal view returns (bool) {
        for (uint256 i = 0; i < actors.length; i++) if (actors[i] == x) return true;
        return false;
    }

    function _price(ILender.MarketParams memory mp) internal view returns (uint256 p) {
        __PRICE_EXPR__
    }

    /// Minimum position size in loan-token units (Moolah: minLoan(MarketParams)); 1 if the fork has none.
    function _minLoan(ILender.MarketParams memory mp) internal view returns (uint256 v) {
        __MINLOAN_EXPR__
        if (v == 0) v = 1;
    }

    function _m(uint256 seed) internal view returns (ILender.MarketParams memory mp, bytes32 id) {
        uint256 i = seed % mkts.length;
        return (mkts[i], ids[i]);
    }

    function _role(uint256 seed) internal view returns (address) {
        return supplierRole[seed % mkts.length];
    }

    /// Market index (starting at seed) where `who` has a position of the given kind:
    /// 0 = supply shares, 1 = borrow shares, 2 = collateral. Returns false if none.
    function _withPosition(address who, uint256 seed, uint8 kind)
        internal view returns (bool found, ILender.MarketParams memory mp, bytes32 id, uint256 idx)
    {
        uint256 n = mkts.length;
        for (uint256 k = 0; k < n; k++) {
            uint256 i = (seed + k) % n;
            (uint256 s, uint128 b, uint128 c) = T.position(ids[i], who);
            if ((kind == 0 && s > 0) || (kind == 1 && b > 0) || (kind == 2 && c > 0)) return (true, mkts[i], ids[i], i);
        }
        return (false, mp, id, 0);
    }

    function marketCount() external view returns (uint256) { return mkts.length; }
    function marketAt(uint256 i) external view returns (address loan, address coll, bytes32 id) {
        return (mkts[i].loanToken, mkts[i].collateralToken, ids[i]);
    }
    function tokenCount() external view returns (uint256) { return tokens.length; }

    // ---- actions -------------------------------------------------------------------------------

    function supply(uint256 actorSeed, uint256 mSeed, uint256 amount) external {
        (ILender.MarketParams memory mp, ) = _m(mSeed);
        address wl = _role(mSeed);
        address a = wl != address(0) ? wl : _pick(actorSeed);   // only the whitelist may supply there
        uint256 bal = _bal(mp.loanToken, a);
        if (bal == 0) return;
        uint256 lo = _minLoan(mp);
        amount = bound(amount, lo < bal ? lo : 1, bal);
        vm.prank(a);
        try T.supply(mp, amount, 0, a, "") returns (uint256 assets, uint256) {
            valueIn[a] += assets; opsOf[a]++; _count("supply", true);
        } catch (bytes memory r) { _fail("supply", r); }
    }

    function withdraw(uint256 actorSeed, uint256 mSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        (bool found, ILender.MarketParams memory mp, bytes32 id, uint256 i) = _withPosition(a, mSeed, 0);
        if (!found) {   // the whitelisted supplier role holds the supply positions in restricted markets
            address wl = _role(mSeed);
            if (wl == address(0)) return;
            a = wl;
            (found, mp, id, i) = _withPosition(a, mSeed, 0);
            if (!found) return;
        }
        i;
        (uint256 shares,,) = T.position(id, a);
        if (bps % 2 == 0) bps = 10_000;                          // half the time: close fully (no dust below minimums)
        shares = shares * bound(bps, 1, 10_000) / 10_000;
        if (shares == 0) return;
        vm.prank(a);
        try T.withdraw(mp, 0, shares, a, a) returns (uint256 assets, uint256) {
            valueOut[a] += assets; opsOf[a]++; _count("withdraw", true);
        } catch (bytes memory r) { _fail("withdraw", r); }
    }

    function supplyCollateral(uint256 actorSeed, uint256 mSeed, uint256 amount) external {
        (ILender.MarketParams memory mp, ) = _m(mSeed);
        address a = _pick(actorSeed);
        address prov = collateralRole[mSeed % mkts.length];     // provider deposits on behalf (simulated role)
        address payer = prov != address(0) ? prov : a;
        uint256 bal = _bal(mp.collateralToken, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        if (prov != address(0)) {                                  // move the actor's tokens to the provider first
            vm.prank(a);
            (bool okT, ) = mp.collateralToken.call(abi.encodeWithSignature("transfer(address,uint256)", prov, amount));
            if (!okT) return;
        }
        uint256 p = _price(mp);
        vm.prank(payer);
        try T.supplyCollateral(mp, amount, a, "") {
            valueIn[a] += amount * p / SCALE; opsOf[a]++; _count("supplyCollateral", true);
        } catch (bytes memory r) {
            _fail("supplyCollateral", r);
            if (prov != address(0)) {                              // give the tokens back
                vm.prank(prov);
                (bool okB, ) = mp.collateralToken.call(abi.encodeWithSignature("transfer(address,uint256)", a, amount));
                okB;
            }
        }
    }

    function withdrawCollateral(uint256 actorSeed, uint256 mSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        (bool found, ILender.MarketParams memory mp, bytes32 id, uint256 i) = _withPosition(a, mSeed, 2);
        if (!found) return;
        (,, uint128 coll) = T.position(id, a);
        uint256 amount = uint256(coll) * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        address prov = collateralRole[i];
        uint256 p = _price(mp);
        vm.prank(prov != address(0) ? prov : a);
        try T.withdrawCollateral(mp, amount, a, a) {
            valueOut[a] += amount * p / SCALE; opsOf[a]++; _count("withdrawCollateral", true);
        } catch (bytes memory r) { _fail("withdrawCollateral", r); }
    }

    function borrow(uint256 actorSeed, uint256 mSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        (bool found, ILender.MarketParams memory mp, bytes32 id, ) = _withPosition(a, mSeed, 2);
        if (!found) return;
        (,, uint128 coll) = T.position(id, a);
        uint256 cap = uint256(coll) * _price(mp) / SCALE;      // upper bound; the protocol enforces LTV
        if (amount % 2 == 1) cap = cap * 80 / 100;              // half the time stay well inside typical LTVs
        (uint128 sA,, uint128 bA,,,) = T.market(id);
        uint256 liq = sA > bA ? uint256(sA) - uint256(bA) : 0;  // free liquidity in this market
        if (cap > liq) cap = liq;
        uint256 lo = _minLoan(mp);
        if (cap < lo) return;
        amount = bound(amount, lo, cap);
        vm.prank(a);
        try T.borrow(mp, amount, 0, a, a) returns (uint256 assets, uint256) {
            valueOut[a] += assets; opsOf[a]++; _count("borrow", true);
        } catch (bytes memory r) { _fail("borrow", r); }
    }

    function repay(uint256 actorSeed, uint256 mSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        (bool found, ILender.MarketParams memory mp, bytes32 id, ) = _withPosition(a, mSeed, 1);
        if (!found) return;
        (, uint128 bShares,) = T.position(id, a);
        if (bps % 2 == 0) bps = 10_000;                          // half the time: repay fully
        uint256 shares = uint256(bShares) * bound(bps, 1, 10_000) / 10_000;
        if (shares == 0) return;
        vm.prank(a);
        try T.repay(mp, 0, shares, a, "") returns (uint256 assets, uint256) {
            valueIn[a] += assets; opsOf[a]++; _count("repay", true);
        } catch (bytes memory r) { _fail("repay", r); }
    }

    /// Only targeted in --warp mode: lets interest accrue so positions can become unhealthy.
    function warp(uint256 dt) external {
        if (!WARP) return;
        dt = bound(dt, 1 hours, 30 days);
        vm.warp(block.timestamp + dt);
        vm.roll(block.number + dt / 12);
        _count("warp", true);
    }

    /// Only targeted in --warp mode (liquidator profit is intended, so NO-FREE-WITHDRAW is off there).
    function liquidate(uint256 actorSeed, uint256 victimSeed, uint256 mSeed, uint256 bps) external {
        if (!WARP) return;
        (ILender.MarketParams memory mp, bytes32 id) = _m(mSeed);
        address a = _pick(actorSeed);
        address v = actors[victimSeed % actors.length];
        (, uint128 bShares,) = T.position(id, v);
        if (bShares == 0 || v == a) return;
        uint256 shares = uint256(bShares) * bound(bps, 1, 10_000) / 10_000;
        if (shares == 0) return;
        vm.prank(a);
        try T.liquidate(mp, v, 0, shares, "") { _count("liquidate", true); } catch { _count("liquidate", false); }
    }
}
"""


# ATTACKER-PROFIT: a universal invariant for every template. An unprivileged actor, after any sequence of the
# handler's normal actions, must not end up with (a) more token value out than in, (b) an allowance the TARGET
# granted it over the TARGET's own funds, or (c) owner()/DEFAULT_ADMIN_ROLE it did not start with. Uses only
# HandlerBase hooks (TARGET/actors/valueIn/valueOut/opsOf) and the template's tokens(), so it is template-agnostic.
# Detection only: a break is reported as a missing protection + fix, never as an attack sequence.
ATTACKER_PROFIT = r"""
    function _isOwnerOrAdmin(address a) internal view returns (bool) {
        (bool ok, bytes memory d) = h.TARGET().staticcall(abi.encodeWithSignature("owner()"));
        if (ok && d.length == 32 && abi.decode(d, (address)) == a) return true;
        (ok, d) = h.TARGET().staticcall(abi.encodeWithSignature("hasRole(bytes32,address)", bytes32(0), a));
        if (ok && d.length == 32 && abi.decode(d, (bool))) return true;
        return false;
    }

    function invariant_attackerProfit() public view {
        for (uint256 i = 0; i < h.actorCount(); i++) {
            address a = h.actors(i);
            // (a) token value: out never exceeds in (+ rounding). Actors are unprivileged test addresses.
            assertLe(h.valueOut(a), h.valueIn(a) + TOL * (1 + h.opsOf(a)) + h.valueIn(a) / 1e12,
                "ATTACKER-PROFIT: actor took out more token value than it put in");
            // (b) the target must never approve an unprivileged actor to spend the target's own holdings
            for (uint256 c = 0; c < h.tokenCount(); c++) {
                assertEq(IERC20Min(h.tokens(c)).allowance(h.TARGET(), a), 0,
                    "ATTACKER-PROFIT: target granted the actor an allowance over its own funds");
            }
            // (c) an unprivileged actor must never acquire ownership / default-admin
            assertFalse(_isOwnerOrAdmin(a), "ATTACKER-PROFIT: actor acquired owner/admin role");
        }
    }
"""


# Under --warp, yield/interest legitimately makes value-out exceed value-in, so the value check is dropped;
# the allowance and role checks stay valid (time never grants an unprivileged actor an allowance or a role).
ATTACKER_PROFIT_WARP = r"""
    function _isOwnerOrAdminW(address a) internal view returns (bool) {
        (bool ok, bytes memory d) = h.TARGET().staticcall(abi.encodeWithSignature("owner()"));
        if (ok && d.length == 32 && abi.decode(d, (address)) == a) return true;
        (ok, d) = h.TARGET().staticcall(abi.encodeWithSignature("hasRole(bytes32,address)", bytes32(0), a));
        if (ok && d.length == 32 && abi.decode(d, (bool))) return true;
        return false;
    }
    function invariant_attackerProfit() public view {
        for (uint256 i = 0; i < h.actorCount(); i++) {
            address a = h.actors(i);
            for (uint256 c = 0; c < h.tokenCount(); c++) {
                assertEq(IERC20Min(h.tokens(c)).allowance(h.TARGET(), a), 0,
                    "ATTACKER-PROFIT: target granted the actor an allowance over its own funds");
            }
            assertFalse(_isOwnerOrAdminW(a), "ATTACKER-PROFIT: actor acquired owner/admin role");
        }
    }
"""

LENDER_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: per market borrow <= supply; per token the contract holds at least what lenders can
    /// withdraw. Absolute for tokens only used as loan token (covers pre-existing users too), and as a
    /// delta for every token (what the actors added must still be there).
    function invariant_solvency() public view {
        uint256 n = h.marketCount();
        for (uint256 m = 0; m < n; m++) {
            (,, bytes32 id) = h.marketAt(m);
            (uint128 sA,, uint128 bA,,,) = L.market(id);
            assertLe(bA, sA, "SOLVENCY: totalBorrowAssets > totalSupplyAssets");
        }
        uint256 nt = h.tokenCount();
        for (uint256 t = 0; t < nt; t++) {
            address tok = h.tokens(t);
            int256 need;      // change in what the contract owes in `tok` since setUp
            uint256 owedAbs;  // absolute withdrawable liquidity in `tok` (loan side)
            bool alsoCollateral;
            for (uint256 m = 0; m < n; m++) {
                (address loan, address coll, bytes32 id) = h.marketAt(m);
                (uint128 sA,, uint128 bA,,,) = L.market(id);
                if (loan == tok) {
                    owedAbs += uint256(sA) - uint256(bA);
                    need += (int256(uint256(sA)) - int256(uint256(bA))) - liq0[id];
                }
                if (coll == tok) {
                    alsoCollateral = true;
                    for (uint256 a = 0; a < h.actorCount(); a++) {
                        (,, uint128 c) = L.position(id, h.actors(a));
                        need += int256(uint256(c));
                    }
                }
            }
            uint256 bal = IERC20Min(tok).balanceOf(address(L));
            assertGe(int256(bal) - int256(bal0[tok]), need - int256(TOL), "SOLVENCY: token backing shrank below obligations");
            if (!alsoCollateral) assertGe(bal + TOL, owedAbs, "SOLVENCY: balance < totalSupplyAssets - totalBorrowAssets");
        }
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: no actor ever takes out more value than it put in (collateral valued at the
    /// market oracle). Rounding tolerance: 10 wei per successful operation. Disabled with --warp.
    function invariant_noFreeWithdraw() public view {
        if (WARP) return;
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertLe(h.valueOut(who), h.valueIn(who) + 10 * h.opsOf(who) + TOL,
                "NO-FREE-WITHDRAW: actor withdrew more value than deposited");
        }
    }
""",
    "conservation": r"""
    /// CONSERVATION: on the fork only the actors and the target move these tokens, so per token
    /// (sum of actor balances + target balance) must stay exactly constant.
    function invariant_conservation() public view {
        for (uint256 t = 0; t < h.tokenCount(); t++) {
            address tok = h.tokens(t);
            assertEq(_held(tok), held0[tok], "CONSERVATION: tokens created or destroyed");
        }
    }
""",
    "access": r"""
    /// ACCESS: owner/role-gated functions must revert for an unauthorized actor.
    function invariant_access() public view {
        assertFalse(h.accessViolation(), string.concat("ACCESS: gated function succeeded for unauthorized actor: ", h.accessViolationFn()));
    }
""",
}

LENDER_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    ILender internal L;
    bool internal WARP;
    uint256 internal constant TOL = __TOL__;
    mapping(address => uint256) internal bal0;
    mapping(address => uint256) internal held0;
    mapping(bytes32 => int256) internal liq0;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        WARP = vm.envOr("FUZZ_WARP", false);
        L = ILender(__TARGET__);
        h = new Handler(address(L), __ACTORS__, WARP);
        for (uint256 t = 0; t < h.tokenCount(); t++) {
            address tok = h.tokens(t);
            bal0[tok] = IERC20Min(tok).balanceOf(address(L));
            held0[tok] = _held(tok);
        }
        for (uint256 m = 0; m < h.marketCount(); m++) {
            (,, bytes32 id) = h.marketAt(m);
            (uint128 sA,, uint128 bA,,,) = L.market(id);
            liq0[id] = int256(uint256(sA)) - int256(uint256(bA));
        }
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        // The handler impersonates its own actors (vm.prank); pin the fuzz sender so the fuzzer does not
        // invent thousands of random senders that each cost an upstream account lookup on the fork.
        targetSender(address(0xF022));
    }

    function _held(address tok) internal view returns (uint256 s) {
        s = IERC20Min(tok).balanceOf(address(L));
        for (uint256 a = 0; a < h.actorCount(); a++) s += IERC20Min(tok).balanceOf(h.actors(a));
    }

__INVARIANTS__

    /// Runs once after each campaign: prints how often each action actually succeeded (coverage).
    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        // emitted via forge's console in the generated file header
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- vault (ERC-4626)
VAULT_HANDLER = r"""
interface IVault4626 {
    function asset() external view returns (address);
    function totalAssets() external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function convertToAssets(uint256) external view returns (uint256);
    function deposit(uint256, address) external returns (uint256);
    function mint(uint256, address) external returns (uint256);
    function withdraw(uint256, address, address) external returns (uint256);
    function redeem(uint256, address, address) external returns (uint256);
    function transfer(address, uint256) external returns (bool);
    function maxDeposit(address) external view returns (uint256);
    function maxMint(address) external view returns (uint256);
}

contract Handler is HandlerBase {
    IVault4626 internal immutable V;
    address public immutable ASSET;
    bool public immutable WARP;
    uint256 internal constant FUND = __FUND__;

    constructor(address target, uint256 nActors, bool warp_) HandlerBase(target, nActors) {
        V = IVault4626(target);
        ASSET = V.asset();
        WARP = warp_;
        for (uint256 a = 0; a < actors.length; a++) {
            _fund(ASSET, actors[a], FUND);
            vm.prank(actors[a]);
            _approve(ASSET, target);
        }
__PRIV__
    }

    function tokenCount() external pure returns (uint256) { return 1; }
    function tokens(uint256) external view returns (address) { return ASSET; }

    function deposit(uint256 actorSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        uint256 bal = _bal(ASSET, a);
        try V.maxDeposit(a) returns (uint256 m) { if (m < bal) bal = m; } catch {}   // respect caps / shutdown
        if (bal == 0) { _count("deposit(cap=0)", false); return; }
        amount = bound(amount, 1, bal);
        uint256 before = _bal(ASSET, a);
        vm.prank(a);
        try V.deposit(amount, a) { valueIn[a] += before - _bal(ASSET, a); opsOf[a]++; _count("deposit", true); }
        catch (bytes memory r) { _fail("deposit", r); }
    }

    function mint(uint256 actorSeed, uint256 shares) external {
        address a = _pick(actorSeed);
        uint256 maxS = 1e30;
        try V.maxMint(a) returns (uint256 m) { if (m < maxS) maxS = m; } catch {}
        if (maxS == 0) { _count("mint(cap=0)", false); return; }
        shares = bound(shares, 1, maxS);
        uint256 before = _bal(ASSET, a);
        vm.prank(a);
        try V.mint(shares, a) { valueIn[a] += before - _bal(ASSET, a); opsOf[a]++; _count("mint", true); }
        catch (bytes memory r) { _fail("mint", r); }
    }

    function withdraw(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 maxA = V.convertToAssets(V.balanceOf(a));
        if (maxA == 0) return;
        uint256 amount = maxA * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        uint256 before = _bal(ASSET, a);
        vm.roll(block.number + 1);   // users exit in a later block (same-block anti-flash checks, e.g. IdleCDO)
        vm.prank(a);
        try V.withdraw(amount, a, a) { valueOut[a] += _bal(ASSET, a) - before; opsOf[a]++; _count("withdraw", true); }
        catch (bytes memory r) { _fail("withdraw", r); }
    }

    function redeem(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 shares = V.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (shares == 0) return;
        uint256 before = _bal(ASSET, a);
        vm.roll(block.number + 1);   // users exit in a later block (same-block anti-flash checks, e.g. IdleCDO)
        vm.prank(a);
        try V.redeem(shares, a, a) { valueOut[a] += _bal(ASSET, a) - before; opsOf[a]++; _count("redeem", true); }
        catch (bytes memory r) { _fail("redeem", r); }
    }

    /// Share transfer between actors: moves the shares' current value in the ghost books.
    function transferShares(uint256 fromSeed, uint256 toSeed, uint256 bps) external {
        address a = _pick(fromSeed);
        address b = actors[toSeed % actors.length];
        uint256 shares = V.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (shares == 0 || a == b) return;
        uint256 val = V.convertToAssets(shares);
        vm.prank(a);
        try V.transfer(b, shares) {
            valueOut[a] += val; valueIn[b] += val; _count("transferShares", true);
        } catch (bytes memory r) { _fail("transferShares", r); }
    }

    function warp(uint256 dt) external {
        if (!WARP) return;
        dt = bound(dt, 1 hours, 30 days);
        vm.warp(block.timestamp + dt);
        vm.roll(block.number + dt / 12);
        _count("warp", true);
    }
}
"""

VAULT_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: the value of all shares never exceeds what the vault reports to hold.
    function invariant_solvency() public view {
        assertLe(V.convertToAssets(V.totalSupply()), V.totalAssets() + TOL,
            "SOLVENCY: convertToAssets(totalSupply) > totalAssets");
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: no actor withdraws more than it deposited (plus share transfers received).
    function invariant_noFreeWithdraw() public view {
        if (WARP) return;
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertLe(h.valueOut(who), h.valueIn(who) + 10 * h.opsOf(who) + TOL,
                "NO-FREE-WITHDRAW: actor withdrew more value than deposited");
        }
    }
""",
    "conservation": r"""
    /// CONSERVATION: the actors as a group never end up with more value than they started with
    /// (asset balances + value of their shares). Disabled with --warp (yield is intended).
    function invariant_conservation() public view {
        if (WARP) return;
        uint256 v;
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            v += IERC20Min(h.ASSET()).balanceOf(who) + V.convertToAssets(V.balanceOf(who));
        }
        assertLe(v, actorValue0 + TOL * (1 + h.actorCount()), "CONSERVATION: actors gained value out of nothing");
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

VAULT_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IVault4626 internal V;
    bool internal WARP;
    uint256 internal constant TOL = __TOL__;
    uint256 internal actorValue0;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        WARP = vm.envOr("FUZZ_WARP", false);
        V = IVault4626(__TARGET__);
        h = new Handler(address(V), __ACTORS__, WARP);
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            actorValue0 += IERC20Min(h.ASSET()).balanceOf(who) + V.convertToAssets(V.balanceOf(who));
        }
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        // The handler impersonates its own actors (vm.prank); pin the fuzz sender so the fuzzer does not
        // invent thousands of random senders that each cost an upstream account lookup on the fork.
        targetSender(address(0xF022));
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- token (ERC-20)
TOKEN_HANDLER = r"""
interface IToken {
    function transfer(address, uint256) external returns (bool);
    function transferFrom(address, address, uint256) external returns (bool);
    function approve(address, uint256) external returns (bool);
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
}

contract Handler is HandlerBase {
    IToken internal immutable K;
    uint256 internal constant FUND = __FUND__;
    mapping(address => uint256) public expected;   // ghost balance per actor

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        K = IToken(target);
        for (uint256 a = 0; a < actors.length; a++) {
            _fund(target, actors[a], FUND);
            expected[actors[a]] = K.balanceOf(actors[a]);
            valueIn[actors[a]] = expected[actors[a]];
        }
__PRIV__
    }

    function tokenCount() external pure returns (uint256) { return 1; }
    function tokens(uint256) external view returns (address) { return TARGET; }

    function transfer(uint256 fromSeed, uint256 toSeed, uint256 amount) external {
        address a = _pick(fromSeed);
        address b = actors[toSeed % actors.length];
        uint256 bal = K.balanceOf(a);
        if (bal == 0) return;
        amount = bound(amount, 0, bal);
        vm.prank(a);
        (bool ok, ) = TARGET.call(abi.encodeWithSelector(IToken.transfer.selector, b, amount));
        _count("transfer", ok);
        if (ok && a != b) { expected[a] -= amount; expected[b] += amount; valueOut[a] += amount; valueIn[b] += amount; }
    }

    function approveAndTransferFrom(uint256 ownerSeed, uint256 spenderSeed, uint256 toSeed, uint256 amount) external {
        address o = _pick(ownerSeed);
        address s = actors[spenderSeed % actors.length];
        address b = actors[toSeed % actors.length];
        uint256 bal = K.balanceOf(o);
        if (bal == 0) return;
        amount = bound(amount, 0, bal);
        vm.prank(o);
        (bool ok1, ) = TARGET.call(abi.encodeWithSelector(IToken.approve.selector, s, amount));
        if (!ok1) return;
        vm.prank(s);
        (bool ok, ) = TARGET.call(abi.encodeWithSelector(IToken.transferFrom.selector, o, b, amount));
        _count("transferFrom", ok);
        if (ok && o != b) { expected[o] -= amount; expected[b] += amount; valueOut[o] += amount; valueIn[b] += amount; }
    }
}
"""

TOKEN_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "conservation": r"""
    /// CONSERVATION: transfers never change totalSupply nor the actors' combined balance.
    function invariant_conservation() public view {
        assertEq(K.totalSupply(), supply0, "CONSERVATION: totalSupply changed by transfers");
        uint256 s;
        for (uint256 a = 0; a < h.actorCount(); a++) s += K.balanceOf(h.actors(a));
        assertEq(s, actorSum0, "CONSERVATION: actor balances created or destroyed");
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: every actor's balance equals its ghost balance (received - sent).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertEq(K.balanceOf(who), h.expected(who), "NO-FREE-WITHDRAW: balance differs from received - sent");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

TOKEN_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IToken internal K;
    uint256 internal supply0;
    uint256 internal actorSum0;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        K = IToken(__TARGET__);
        h = new Handler(address(K), __ACTORS__, false);
        supply0 = K.totalSupply();
        for (uint256 a = 0; a < h.actorCount(); a++) actorSum0 += K.balanceOf(h.actors(a));
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        // The handler impersonates its own actors (vm.prank); pin the fuzz sender so the fuzzer does not
        // invent thousands of random senders that each cost an upstream account lookup on the fork.
        targetSender(address(0xF022));
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- amm (Uniswap-V2 pair)
AMM_HANDLER = r"""
interface IPair {
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getReserves() external view returns (uint112, uint112, uint32);
    function swap(uint256, uint256, address, bytes calldata) external;
    function sync() external;
    function mint(address) external returns (uint256);
    function burn(address) external returns (uint256, uint256);
    function factory() external view returns (address);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function transfer(address, uint256) external returns (bool);
}

contract Handler is HandlerBase {
    IPair internal immutable P;
    address public immutable T0;
    address public immutable T1;
    uint256 internal constant FUND = __FUND__;
    uint256 internal constant FEE_BPS = __FEE_BPS__;   // assumed swap fee (conservative: >= real fee)
    address public feeTo;   // V2 protocol-fee recipient (gets LP minted in _mintFee); 0 if off/unknown

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        P = IPair(target);
        T0 = P.token0();
        T1 = P.token1();
        try P.factory() returns (address f) {
            (bool ok, bytes memory d) = f.staticcall(abi.encodeWithSignature("feeTo()"));
            if (ok && d.length >= 32) feeTo = abi.decode(d, (address));
        } catch {}
        for (uint256 a = 0; a < actors.length; a++) {
            _fund(T0, actors[a], FUND);
            _fund(T1, actors[a], FUND);
        }
__PRIV__
    }

    function tokenCount() external pure returns (uint256) { return 2; }
    function tokens(uint256 i) external view returns (address) { return i == 0 ? T0 : T1; }

    function _xfer(address token, address from, address to, uint256 amt) internal returns (bool ok) {
        vm.prank(from);
        (ok, ) = token.call(abi.encodeWithSignature("transfer(address,uint256)", to, amt));
    }

    function swap(uint256 actorSeed, bool zeroForOne, uint256 amountIn) external {
        address a = _pick(actorSeed);
        (uint112 r0, uint112 r1, ) = P.getReserves();
        address tin = zeroForOne ? T0 : T1;
        uint256 bal = _bal(tin, a);
        if (bal == 0 || r0 == 0 || r1 == 0) return;
        amountIn = bound(amountIn, 1, bal);
        (uint256 rin, uint256 rout) = zeroForOne ? (uint256(r0), uint256(r1)) : (uint256(r1), uint256(r0));
        uint256 inFee = amountIn * (10_000 - FEE_BPS);
        uint256 out = inFee * rout / (rin * 10_000 + inFee);
        if (out == 0) return;
        if (!_xfer(tin, a, address(P), amountIn)) return;
        vm.prank(a);
        try P.swap(zeroForOne ? 0 : out, zeroForOne ? out : 0, a, "") { _count("swap", true); }
        catch { _count("swap", false); }
    }

    function addLiquidity(uint256 actorSeed, uint256 amount0) external {
        address a = _pick(actorSeed);
        (uint112 r0, uint112 r1, ) = P.getReserves();
        if (r0 == 0 || r1 == 0) return;
        uint256 b0 = _bal(T0, a);
        if (b0 == 0) return;
        amount0 = bound(amount0, 1, b0);
        uint256 amount1 = amount0 * r1 / r0 + 1;
        if (amount1 > _bal(T1, a)) return;
        if (!_xfer(T0, a, address(P), amount0) || !_xfer(T1, a, address(P), amount1)) return;
        vm.prank(a);
        try P.mint(a) { _count("mint", true); } catch { _count("mint", false); }
    }

    function removeLiquidity(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 lp = P.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (lp == 0) return;
        if (!_xfer(address(P), a, address(P), lp)) return;
        vm.prank(a);
        try P.burn(a) { _count("burn", true); } catch { _count("burn", false); }
    }
}
"""

AMM_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: the pair's token balances always cover its recorded reserves.
    function invariant_solvency() public view {
        (uint112 r0, uint112 r1, ) = P.getReserves();
        assertGe(IERC20Min(h.T0()).balanceOf(address(P)), r0, "SOLVENCY: balance0 < reserve0");
        assertGe(IERC20Min(h.T1()).balanceOf(address(P)), r1, "SOLVENCY: balance1 < reserve1");
    }
""",
    "k-monotonic": r"""
    /// K-MONOTONIC: sqrt(k) per LP share (all shares, incl. protocol LP — that is what burn() pays out) never
    /// decreases, except for exactly the dilution from LP minted to the V2 protocol-fee recipient (`_mintFee`,
    /// by design). _mintFee runs first in mint()/burn(), against the supply of the previous check (lastTs):
    /// allowed = lastKps * lastTs / (lastTs + d), d = protocol LP minted since that check.
    function invariant_kPerShare() public {
        (uint112 r0, uint112 r1, ) = P.getReserves();
        uint256 ts = P.totalSupply();
        if (ts == 0) return;
        uint256 proto = _protocolLp();
        uint256 d = proto - lastProto;
        uint256 kps = _sqrt(uint256(r0) * uint256(r1)) * 1e18 / ts;
        uint256 allowed = lastTs == 0 ? lastKps : lastKps * lastTs / (lastTs + d);
        // Tolerance = what one base unit of the smaller reserve is worth in this metric: integer sqrt and
        // share rounding cause drops far below that, and nothing smaller than one token unit can be extracted.
        uint256 minR = r0 < r1 ? uint256(r0) : uint256(r1);
        uint256 tol = minR == 0 ? 1 : lastKps * 2 / minR + 1;
        assertGe(kps + tol, allowed, "K-MONOTONIC: sqrt(k) per LP share decreased");
        lastKps = kps;
        lastProto = proto;
        lastTs = ts;
    }

    function _sqrt(uint256 y) internal pure returns (uint256 z) {
        if (y > 3) { z = y; uint256 x = y / 2 + 1; while (x < z) { z = x; x = (y / x + x) / 2; } }
        else if (y != 0) { z = 1; }
    }
""",
    "conservation": r"""
    /// CONSERVATION: per token, actors + pair together hold exactly what they held at setUp.
    function invariant_conservation() public view {
        for (uint256 t = 0; t < 2; t++) {
            address tok = h.tokens(t);
            uint256 s = IERC20Min(tok).balanceOf(address(P));
            for (uint256 a = 0; a < h.actorCount(); a++) s += IERC20Min(tok).balanceOf(h.actors(a));
            assertEq(s, held0[t], "CONSERVATION: tokens created or destroyed");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

AMM_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IPair internal P;
    uint256 internal lastKps;
    uint256 internal lastProto;
    uint256 internal lastTs;
    uint256 internal feeToLp0;
    uint256[2] internal held0;

    function _protocolLp() internal view returns (uint256) {
        address f = h.feeTo();
        return f == address(0) ? 0 : P.balanceOf(f) - feeToLp0;
    }
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        P = IPair(__TARGET__);
        h = new Handler(address(P), __ACTORS__, false);
        if (h.feeTo() != address(0)) feeToLp0 = P.balanceOf(h.feeTo());
        (uint112 r0, uint112 r1, ) = P.getReserves();
        uint256 ts = P.totalSupply();
        lastTs = ts;
        if (ts > 0) {
            uint256 y = uint256(r0) * uint256(r1);
            uint256 z = y; uint256 x = y / 2 + 1;
            while (x < z) { z = x; x = (y / x + x) / 2; }
            lastKps = z * 1e18 / ts;
        }
        for (uint256 t = 0; t < 2; t++) {
            address tok = h.tokens(t);
            uint256 s = IERC20Min(tok).balanceOf(address(P));
            for (uint256 a = 0; a < h.actorCount(); a++) s += IERC20Min(tok).balanceOf(h.actors(a));
            held0[t] = s;
        }
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        // The handler impersonates its own actors (vm.prank); pin the fuzz sender so the fuzzer does not
        // invent thousands of random senders that each cost an upstream account lookup on the fork.
        targetSender(address(0xF022));
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- wrapper (Convex staking wrapper, 1:1)
WRAPPER_HANDLER = r"""
interface IWrapper {
    function curveToken() external view returns (address);
    function convexToken() external view returns (address);
    function convexPool() external view returns (address);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function deposit(uint256, address) external;
    function stake(uint256, address) external;
    function withdraw(uint256) external;
    function withdrawAndUnwrap(uint256) external;
    function transfer(address, uint256) external returns (bool);
    function getReward(address) external;
}

contract Handler is HandlerBase {
    IWrapper internal immutable W;
    address public immutable LP;      // underlying (Curve LP)
    address public immutable CVXT;    // Convex deposit token
    address public immutable POOL;    // Convex reward pool where the wrapper stakes

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        W = IWrapper(target);
        LP = W.curveToken();
        CVXT = W.convexToken();
        POOL = W.convexPool();
        for (uint256 a = 0; a < actors.length; a++) {
            _fund(LP, actors[a], _fundAmount(LP));
            _fund(CVXT, actors[a], _fundAmount(CVXT));
            vm.startPrank(actors[a]);
            _approve(LP, target);
            _approve(CVXT, target);
            vm.stopPrank();
        }
__PRIV__
    }

    function tokenCount() external pure returns (uint256) { return 2; }
    function tokens(uint256 i) external view returns (address) { return i == 0 ? LP : CVXT; }

    function deposit(uint256 actorSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        uint256 bal = _bal(LP, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(a);
        try W.deposit(amount, a) { valueIn[a] += amount; opsOf[a]++; _count("deposit", true); }
        catch (bytes memory r) { _fail("deposit", r); }
    }

    function stake(uint256 actorSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        uint256 bal = _bal(CVXT, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        vm.prank(a);
        try W.stake(amount, a) { valueIn[a] += amount; opsOf[a]++; _count("stake", true); }
        catch (bytes memory r) { _fail("stake", r); }
    }

    function withdraw(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 amount = W.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        uint256 before = _bal(CVXT, a);
        vm.prank(a);
        try W.withdraw(amount) { valueOut[a] += _bal(CVXT, a) - before; opsOf[a]++; _count("withdraw", true); }
        catch (bytes memory r) { _fail("withdraw", r); }
    }

    function withdrawAndUnwrap(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 amount = W.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        uint256 before = _bal(LP, a);
        vm.prank(a);
        try W.withdrawAndUnwrap(amount) { valueOut[a] += _bal(LP, a) - before; opsOf[a]++; _count("withdrawAndUnwrap", true); }
        catch (bytes memory r) { _fail("withdrawAndUnwrap", r); }
    }

    /// Share transfer between actors moves value 1:1 in the ghost books (the wrapper is 1:1 with the LP).
    function transferShares(uint256 fromSeed, uint256 toSeed, uint256 bps) external {
        address a = _pick(fromSeed);
        address b = actors[toSeed % actors.length];
        uint256 amount = W.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0 || a == b) return;
        vm.prank(a);
        try W.transfer(b, amount) { valueOut[a] += amount; valueIn[b] += amount; _count("transferShares", true); }
        catch (bytes memory r) { _fail("transferShares", r); }
    }

    /// Reward claims go through the checkpoint logic; rewards are separate tokens, not principal.
    function getReward(uint256 actorSeed) external {
        address a = _pick(actorSeed);
        try W.getReward(a) { _count("getReward", true); } catch (bytes memory r) { _fail("getReward", r); }
    }
}
"""

WRAPPER_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: every wrapper share is backed 1:1 by LP staked in the Convex pool (or idle in the wrapper).
    function invariant_solvency() public view {
        uint256 backing = IERC20Min(h.POOL()).balanceOf(address(W)) + IERC20Min(h.LP()).balanceOf(address(W))
            + IERC20Min(h.CVXT()).balanceOf(address(W));
        assertGe(backing + TOL, W.totalSupply(), "SOLVENCY: wrapper shares exceed staked backing");
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: no actor takes out more LP/deposit-token than it put in (1:1, incl. share transfers).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertLe(h.valueOut(who), h.valueIn(who) + TOL, "NO-FREE-WITHDRAW: actor withdrew more than deposited");
        }
    }
""",
    "conservation": r"""
    /// CONSERVATION: per actor set, LP + Convex deposit token + wrapper shares is constant (all 1:1).
    function invariant_conservation() public view {
        assertEq(_actorValue(), value0, "CONSERVATION: actor LP + cvx-token + shares changed");
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

WRAPPER_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IWrapper internal W;
    uint256 internal value0;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        W = IWrapper(__TARGET__);
        h = new Handler(address(W), __ACTORS__, false);
        value0 = _actorValue();
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

    function _actorValue() internal view returns (uint256 v) {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            v += IERC20Min(h.LP()).balanceOf(who) + IERC20Min(h.CVXT()).balanceOf(who) + W.balanceOf(who);
        }
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- mintredeem (collateral-backed stable)
# Shape: mintWithCollateral(asset, amount) / redeem(asset, amount, allowQueue) / cancelRedeem(), collateral held in
# a separate multi-collateral token (mct) with collateralBalance(asset) bookkeeping (NaraUSD). KYC gates
# (Keyring credentials) are satisfied for the test actors with vm.mockCall — a KYC'd user is an ordinary user.
MINTREDEEM_HANDLER = r"""
interface IMintRedeem {
    struct RedemptionRequest { uint152 naraUsdAmount; address collateralAsset; }
    function mct() external view returns (address);
    function feeTreasury() external view returns (address);
    function keyringAddress() external view returns (address);
    function keyringPolicyId() external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function balanceOf(address) external view returns (uint256);
    function mintWithCollateral(address, uint256) external returns (uint256);
    function redeem(address, uint256, bool) external returns (uint256, bool);
    function cancelRedeem() external;
    function redemptionRequests(address) external view returns (RedemptionRequest memory);
}

interface IMct {
    function getSupportedAssets() external view returns (address[] memory);
    function collateralBalance(address) external view returns (uint256);
}

contract Handler is HandlerBase {
    IMintRedeem internal immutable S;
    address public immutable MCT;
    address public immutable TREASURY;
    address[] public assets;
    mapping(address => uint256) public dec;   // collateral decimals

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        S = IMintRedeem(target);
        MCT = S.mct();
        TREASURY = S.feeTreasury();
        assets = IMct(MCT).getSupportedAssets();
        address keyring = S.keyringAddress();
        uint256 policy = S.keyringPolicyId();
        for (uint256 a = 0; a < actors.length; a++) {
            if (keyring != address(0)) {   // simulated KYC credential (ordinary user, not a privileged role)
                vm.mockCall(keyring, abi.encodeWithSignature("checkCredential(uint256,address)", policy, actors[a]),
                            abi.encode(true));
            }
            for (uint256 i = 0; i < assets.length; i++) {
                _fund(assets[i], actors[a], _fundAmount(assets[i]) / 1000);   // 1e6 whole units
                vm.prank(actors[a]);
                _approve(assets[i], target);
            }
        }
        for (uint256 i = 0; i < assets.length; i++) {
            (bool ok, bytes memory d) = assets[i].staticcall(abi.encodeWithSignature("decimals()"));
            dec[assets[i]] = ok && d.length >= 32 ? abi.decode(d, (uint256)) : 18;
        }
__PRIV__
    }

    function tokenCount() external view returns (uint256) { return assets.length; }
    function tokens(uint256 i) external view returns (address) { return assets[i]; }
    function norm(address asset, uint256 amt) public view returns (uint256) {
        uint256 d = dec[asset];
        return d <= 18 ? amt * 10 ** (18 - d) : amt / 10 ** (d - 18);
    }
    function queued(address who) public view returns (uint256) {
        return uint256(S.redemptionRequests(who).naraUsdAmount);
    }

    function mint(uint256 actorSeed, uint256 assetSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        address asset = assets[assetSeed % assets.length];
        uint256 bal = _bal(asset, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try S.mintWithCollateral(asset, amount) {
            valueIn[a] += norm(asset, before - _bal(asset, a)); opsOf[a]++; _count("mint", true);
        } catch (bytes memory r) { _fail("mint", r); }
    }

    function redeemInstant(uint256 actorSeed, uint256 assetSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        address asset = assets[assetSeed % assets.length];
        uint256 amt = S.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amt == 0) return;
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try S.redeem(asset, amt, false) {
            valueOut[a] += norm(asset, _bal(asset, a) - before); opsOf[a]++; _count("redeemInstant", true);
        } catch (bytes memory r) { _fail("redeemInstant", r); }
    }

    /// allowQueue = true: instant if liquidity, else the NaraUSD is escrowed in the redeem silo.
    function redeemOrQueue(uint256 actorSeed, uint256 assetSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        if (queued(a) > 0) return;    // one active request per user
        address asset = assets[assetSeed % assets.length];
        uint256 amt = S.balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amt == 0) return;
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try S.redeem(asset, amt, true) {
            valueOut[a] += norm(asset, _bal(asset, a) - before); opsOf[a]++; _count("redeemOrQueue", true);
        } catch (bytes memory r) { _fail("redeemOrQueue", r); }
    }

    function cancelRedeem(uint256 actorSeed) external {
        address a = _pick(actorSeed);
        if (queued(a) == 0) return;
        vm.prank(a);
        try S.cancelRedeem() { _count("cancelRedeem", true); } catch (bytes memory r) { _fail("cancelRedeem", r); }
    }
}
"""

MINTREDEEM_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: (a) what the actors added to the stable's supply is backed by at least as much new collateral
    /// (normalized to 18 decimals) in the MCT; (b) the MCT's collateralBalance bookkeeping never exceeds the
    /// tokens it really holds.
    function invariant_solvency() public view {
        int256 dSupply = int256(S.totalSupply()) - int256(supply0);
        int256 dBacking;
        for (uint256 i = 0; i < h.tokenCount(); i++) {
            address asset = h.tokens(i);
            uint256 cb = IMct(h.MCT()).collateralBalance(asset);
            dBacking += int256(h.norm(asset, cb)) - int256(h.norm(asset, backing0[asset]));
            assertLe(cb, IERC20Min(asset).balanceOf(h.MCT()), "SOLVENCY: MCT collateralBalance exceeds real balance");
        }
        assertLe(dSupply, dBacking + int256(TOL), "SOLVENCY: new supply not backed by new collateral");
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: collateral taken out + stable still held + stable escrowed in a queued redemption never
    /// exceeds the collateral put in (all normalized to 18 decimals; fees only make the left side smaller).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            uint256 has = h.valueOut(who) + S.balanceOf(who) + h.queued(who);
            assertLe(has, h.valueIn(who) + TOL * (1 + h.opsOf(who)), "NO-FREE-WITHDRAW: actor got more value than deposited");
        }
    }
""",
    "conservation": r"""
    /// CONSERVATION: per collateral token, actors + stable + MCT + fee treasury hold exactly what they held at setUp.
    function invariant_conservation() public view {
        for (uint256 i = 0; i < h.tokenCount(); i++) {
            address asset = h.tokens(i);
            assertEq(_held(asset), held0[asset], "CONSERVATION: collateral created or destroyed");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

MINTREDEEM_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IMintRedeem internal S;
    uint256 internal supply0;
    mapping(address => uint256) internal backing0;
    mapping(address => uint256) internal held0;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        S = IMintRedeem(__TARGET__);
        h = new Handler(address(S), __ACTORS__, false);
        supply0 = S.totalSupply();
        for (uint256 i = 0; i < h.tokenCount(); i++) {
            address asset = h.tokens(i);
            backing0[asset] = IMct(h.MCT()).collateralBalance(asset);
            held0[asset] = _held(asset);
        }
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

    function _held(address asset) internal view returns (uint256 s) {
        s = IERC20Min(asset).balanceOf(address(S)) + IERC20Min(asset).balanceOf(h.MCT())
            + IERC20Min(asset).balanceOf(h.TREASURY());
        for (uint256 a = 0; a < h.actorCount(); a++) s += IERC20Min(asset).balanceOf(h.actors(a));
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- queuevault (mint + async withdrawal queue)
# Shape: mint(amount) of `asset` into a vault that issues a rebasing oToken 1:1, requestWithdrawal(oTokenAmount)
# burns and queues, claimWithdrawal(id) pays out after withdrawalClaimDelay (Origin OUSD/OETH vault). Test actors
# opt out of rebasing so their oToken balances only move through their own actions (exact ghost accounting).
QUEUEVAULT_HANDLER = r"""
interface IQueueVault {
    function asset() external view returns (address);
    function oToken() external view returns (address);
    function totalValue() external view returns (uint256);
    function withdrawalClaimDelay() external view returns (uint256);
    function mint(uint256) external;
    function requestWithdrawal(uint256) external returns (uint256, uint256);
    function claimWithdrawal(uint256) external returns (uint256);
}

interface IRebasingToken {
    function balanceOf(address) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function rebaseOptOut() external;
}

contract Handler is HandlerBase {
    IQueueVault internal immutable Q;
    address public immutable ASSET;
    address public immutable OTOKEN;
    uint256 public immutable ASSET_DEC;
    mapping(address => uint256[]) internal openIds;
    mapping(address => uint256) public pending;         // oToken amount (18 dec) requested, not yet claimed
    mapping(uint256 => uint256) internal reqAmount;
    int256 public netMinted;     // oToken (18 dec) minted to actors minus oToken burned by their requests
    uint256 public opsTotal;

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        Q = IQueueVault(target);
        ASSET = Q.asset();
        OTOKEN = Q.oToken();
        (bool ok, bytes memory d) = ASSET.staticcall(abi.encodeWithSignature("decimals()"));
        ASSET_DEC = ok && d.length >= 32 ? abi.decode(d, (uint256)) : 18;
        for (uint256 a = 0; a < actors.length; a++) {
            _fund(ASSET, actors[a], _fundAmount(ASSET) / 1000);
            vm.startPrank(actors[a]);
            _approve(ASSET, target);
            try IRebasingToken(OTOKEN).rebaseOptOut() {} catch {}
            vm.stopPrank();
        }
__PRIV__
    }

    function tokenCount() external pure returns (uint256) { return 1; }
    function tokens(uint256) external view returns (address) { return ASSET; }
    function norm(uint256 amt) public view returns (uint256) {
        return ASSET_DEC <= 18 ? amt * 10 ** (18 - ASSET_DEC) : amt / 10 ** (ASSET_DEC - 18);
    }

    function mint(uint256 actorSeed, uint256 amount) external {
        address a = _pick(actorSeed);
        uint256 bal = _bal(ASSET, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        uint256 before = _bal(ASSET, a);
        uint256 oBefore = IRebasingToken(OTOKEN).balanceOf(a);
        vm.prank(a);
        try Q.mint(amount) {
            valueIn[a] += norm(before - _bal(ASSET, a)); opsOf[a]++; opsTotal++;
            netMinted += int256(IRebasingToken(OTOKEN).balanceOf(a) - oBefore);
            _count("mint", true);
        } catch (bytes memory r) { _fail("mint", r); }
    }

    function requestWithdrawal(uint256 actorSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256 amt = IRebasingToken(OTOKEN).balanceOf(a) * bound(bps, 1, 10_000) / 10_000;
        if (amt == 0) return;
        vm.prank(a);
        try Q.requestWithdrawal(amt) returns (uint256 id, uint256) {
            openIds[a].push(id); reqAmount[id] = amt; pending[a] += amt; opsOf[a]++; opsTotal++;
            netMinted -= int256(amt);
            _count("requestWithdrawal", true);
        } catch (bytes memory r) { _fail("requestWithdrawal", r); }
    }

    /// Lets the claim delay pass, then claims the actor's oldest open request.
    function claimWithdrawal(uint256 actorSeed) external {
        address a = _pick(actorSeed);
        if (openIds[a].length == 0) return;
        uint256 id = openIds[a][0];
        vm.warp(block.timestamp + Q.withdrawalClaimDelay() + 1);
        uint256 before = _bal(ASSET, a);
        vm.prank(a);
        try Q.claimWithdrawal(id) {
            valueOut[a] += norm(_bal(ASSET, a) - before);
            pending[a] -= reqAmount[id];
            openIds[a][0] = openIds[a][openIds[a].length - 1];
            openIds[a].pop();
            opsOf[a]++;
            _count("claimWithdrawal", true);
        } catch (bytes memory r) { _fail("claimWithdrawal", r); }
    }
}
"""

QUEUEVAULT_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: vault value only leaves through accounted user exits: the change in totalValue is at least the
    /// net oToken the actors minted (mint +, requestWithdrawal -). Rebase/yield only makes this easier.
    /// (A 1:1 mint at a backing ratio > 1 lowers the RATIO by pure arithmetic, so the ratio is not the invariant.)
    function invariant_solvency() public view {
        int256 dValue = int256(Q.totalValue()) - int256(value0);
        assertGe(dValue + int256(TOL * (1 + h.opsTotal())), h.netMinted(),
            "SOLVENCY: vault value fell by more than the actors' net redemptions");
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: asset claimed + oToken held + oToken in open withdrawal requests never exceeds the
    /// asset put in (all normalized to 18 decimals; actors are opted out of rebasing).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            uint256 has = h.valueOut(who) + IRebasingToken(h.OTOKEN()).balanceOf(who) + h.pending(who);
            assertLe(has, h.valueIn(who) + TOL * (1 + h.opsOf(who)), "NO-FREE-WITHDRAW: actor got more value than deposited");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

QUEUEVAULT_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IQueueVault internal Q;
    uint256 internal value0;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        Q = IQueueVault(__TARGET__);
        h = new Handler(address(Q), __ACTORS__, false);
        value0 = Q.totalValue();
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

__INVARIANTS__

    /// Runs after each campaign run: records how often each action actually succeeded (coverage).
    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- sir (SIR leverage vault: APE/TEA)
# Vault.mint(isAPE, vaultParams, collateralAmount, 0, 0) deposits COLLATERAL (collateralToDepositMin=0 path, no swap)
# and credits APE (ERC20 clone per vault) or TEA (ERC1155 id=vaultId on the Vault). burn(...) returns collateral.
# Price is a 30-min Uniswap V3 TWAP (Oracle.TWAP_DURATION); a fuzz sequence on a static fork cannot move it, so the
# handler never swaps. NO-FREE-WITHDRAW over mint+burn round-trips is the value-extraction check.
SIR_HANDLER = r"""
interface ISirVault {
    struct VaultParameters { address debtToken; address collateralToken; int8 leverageTier; }
    function numberOfVaults() external view returns (uint48);
    function paramsById(uint48) external view returns (VaultParameters memory);
    function totalReserves(address) external view returns (uint256);
    function balanceOf(address, uint256) external view returns (uint256);
    function mint(bool, VaultParameters memory, uint256, uint144, uint40) external payable returns (uint256);
    function burn(bool, VaultParameters calldata, uint256, uint40) external returns (uint144);
}

interface IApe { function balanceOf(address) external view returns (uint256); }

contract Handler is HandlerBase {
    ISirVault internal immutable SV;
    bytes32 internal constant PROXY_HASH = 0x21c35dbe1b344a2488cf3321d6ce542f8e9f305544ff09e4993a62319a497c1f;
    ISirVault.VaultParameters[] internal vp;
    uint48[] public ids;
    address[] public apes;
    address[] public collaterals;

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        SV = ISirVault(target);
        uint48 n = SV.numberOfVaults();
        // The system's own receipt tokens (APE clones) can be some vault's collateral. They must NOT be funded with
        // `deal` (that would write unbacked claims into storage and let a burn redeem real reserves): skip those vaults.
        for (uint48 id = 1; id <= n; id++) isReceipt[_apeAddress(id)] = true;
        for (uint48 id = 1; id <= n; id++) {
            ISirVault.VaultParameters memory p = SV.paramsById(id);
            if (p.collateralToken == address(0)) continue;
            if (isReceipt[p.collateralToken] || p.collateralToken == target) continue;
            if (!_fundable(p.collateralToken)) continue;      // skip tokens whose balance slot cannot be set up
            vp.push(p); ids.push(id); apes.push(_apeAddress(id)); _addColl(p.collateralToken);
        }
        for (uint256 a = 0; a < actors.length; a++)
            for (uint256 c = 0; c < collaterals.length; c++) {
                _fund(collaterals[c], actors[a], _fundAmount(collaterals[c]) / 1000);
                vm.prank(actors[a]); _approve(collaterals[c], target);
            }
__PRIV__
    }

    // CREATE3 clone address for a vaultId (deployer = Vault), matching ClonesWithImmutableArgs.addressOfClone3.
    function _apeAddress(uint48 id) internal view returns (address) {
        address proxy = address(uint160(uint256(keccak256(
            abi.encodePacked(bytes1(0xff), TARGET, bytes32(uint256(id)), PROXY_HASH)))));
        return address(uint160(uint256(keccak256(
            abi.encodePacked(bytes1(0xd6), bytes1(0x94), proxy, bytes1(0x01))))));
    }
    mapping(address => bool) internal isReceipt;    // APE clones of this very system
    mapping(address => uint8) internal fundState;   // 0 unknown, 1 fundable, 2 not fundable
    function _fundable(address tok) internal returns (bool) {
        if (fundState[tok] == 0) {
            _fund(tok, actors[0], _fundAmount(tok) / 1000);
            fundState[tok] = _bal(tok, actors[0]) > 0 ? 1 : 2;
        }
        return fundState[tok] == 1;
    }
    function skippedCollaterals() external view returns (uint256 n) { n = 0; }
    function _addColl(address c) internal { for (uint256 i=0;i<collaterals.length;i++) if (collaterals[i]==c) return; collaterals.push(c); }
    function vaultCount() external view returns (uint256) { return vp.length; }
    function collateralCount() external view returns (uint256) { return collaterals.length; }
    function tokenCount() external view returns (uint256) { return collaterals.length; }
    function tokens(uint256 i) external view returns (address) { return collaterals[i]; }
    function _balToken(uint256 vi, address a, bool isAPE) internal view returns (uint256) {
        return isAPE ? IApe(apes[vi]).balanceOf(a) : SV.balanceOf(a, ids[vi]);
    }

    function _mint(uint256 actorSeed, uint256 vSeed, uint256 amount, bool isAPE) internal {
        uint256 vi = vSeed % vp.length; address a = _pick(actorSeed);
        address coll = vp[vi].collateralToken;
        uint256 bal = _bal(coll, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        uint256 before = _bal(coll, a);
        vm.prank(a);
        try SV.mint(isAPE, vp[vi], amount, 0, 0) { valueIn[a] += before - _bal(coll, a); opsOf[a]++; _count(isAPE?"mintAPE":"mintTEA", true); }
        catch (bytes memory r) { _fail(isAPE?"mintAPE":"mintTEA", r); }
    }
    function mintAPE(uint256 s, uint256 v, uint256 amt) external { _mint(s, v, amt, true); }
    function mintTEA(uint256 s, uint256 v, uint256 amt) external { _mint(s, v, amt, false); }

    function _burn(uint256 actorSeed, uint256 vSeed, uint256 bps, bool isAPE) internal {
        uint256 vi = vSeed % vp.length; address a = _pick(actorSeed);
        uint256 tok = _balToken(vi, a, isAPE);
        tok = tok * bound(bps, 1, 10_000) / 10_000;
        if (tok == 0) return;
        address coll = vp[vi].collateralToken;
        uint256 before = _bal(coll, a);
        vm.prank(a);
        try SV.burn(isAPE, vp[vi], tok, 0) { valueOut[a] += _bal(coll, a) - before; opsOf[a]++; _count(isAPE?"burnAPE":"burnTEA", true); }
        catch (bytes memory r) { _fail(isAPE?"burnAPE":"burnTEA", r); }
    }
    function burnAPE(uint256 s, uint256 v, uint256 bps) external { _burn(s, v, bps, true); }
    function burnTEA(uint256 s, uint256 v, uint256 bps) external { _burn(s, v, bps, false); }

    // Mint then immediately burn the whole freshly minted position in the same call: a cheap round-trip must not
    // return more collateral than it cost (otherwise value is created out of the price/accounting).
    function roundTripAPE(uint256 s, uint256 v, uint256 amt) external { _roundTrip(s, v, amt, true); }
    function roundTripTEA(uint256 s, uint256 v, uint256 amt) external { _roundTrip(s, v, amt, false); }
    function _roundTrip(uint256 actorSeed, uint256 vSeed, uint256 amount, bool isAPE) internal {
        uint256 vi = vSeed % vp.length; address a = _pick(actorSeed);
        address coll = vp[vi].collateralToken;
        uint256 bal = _bal(coll, a);
        if (bal == 0) return;
        amount = bound(amount, 1, bal);
        uint256 tBefore = _balToken(vi, a, isAPE);
        uint256 cBefore = _bal(coll, a);
        vm.prank(a);
        try SV.mint(isAPE, vp[vi], amount, 0, 0) {} catch { return; }
        uint256 minted = _balToken(vi, a, isAPE) - tBefore;
        if (minted == 0) return;
        vm.prank(a);
        try SV.burn(isAPE, vp[vi], minted, 0) {} catch {}
        uint256 cAfter = _bal(coll, a);
        // record net: spent (cBefore - cAfter) as valueIn if positive, returned surplus as valueOut
        if (cAfter > cBefore) { valueOut[a] += cAfter - cBefore; } else { valueIn[a] += cBefore - cAfter; }
        opsOf[a]++; _count(isAPE?"roundTripAPE":"roundTripTEA", true);
    }
}
"""

SIR_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: the vault's recorded totalReserves[collateral] is always backed by at least that much real
    /// collateral held by the vault (surplus above it is only fees owed to stakers).
    function invariant_solvency() public view {
        for (uint256 c = 0; c < h.collateralCount(); c++) {
            address coll = h.tokens(c);
            assertGe(IERC20Min(coll).balanceOf(address(SV)), SV.totalReserves(coll),
                "SOLVENCY: collateral balance below recorded totalReserves");
        }
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: collateral an actor got back (burns + round-trip surplus) never exceeds collateral it put
    /// in, up to rounding. A cheaply manipulable price would show up here as a profitable round-trip.
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertLe(h.valueOut(who), h.valueIn(who) + TOL * (1 + h.opsOf(who)),
                "NO-FREE-WITHDRAW: actor withdrew more collateral than deposited");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

SIR_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    ISirVault internal SV;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        SV = ISirVault(__TARGET__);
        h = new Handler(address(SV), __ACTORS__, false);
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

__INVARIANTS__

    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }

    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure {
        __CONSOLE__
    }
}
"""

# --------------------------------------------------------------------------- locktoken (deposit + unlock-withdraw + claim)
# Cytonic BridgeDepositor: deposit credits usersBalances; withdraw debits and queues a ClaimData unlockable after
# unlockPeriod; claim pays out; cancelWithdraw re-credits. owner-only migrate is out of scope. ERC20 assets only
# (ETH/0x0 path skipped for clean accounting). Assets are discovered in the constructor from a candidate list.
LOCK_HANDLER = r"""
interface ILockDepositor {
    function usersBalances(address, address) external view returns (uint256);
    function allowedAssets(address) external view returns (bool);
    function unlockPeriod() external view returns (uint256);
    function deposit(address, uint256, bytes calldata) external;
    function withdraw(address, uint128, uint256) external;
    function claim(uint128, address) external;
    function cancelWithdraw(uint128) external;
}

contract Handler is HandlerBase {
    ILockDepositor internal immutable D;
    address[] public assets;
    uint128 internal nextId = 1;
    mapping(uint128 => address) internal claimOwner;
    mapping(uint128 => uint256) internal claimAmt;
    mapping(uint128 => address) internal claimAsset;
    uint128[] internal openClaims;
    mapping(address => uint256) public pending;
    mapping(address => uint256) public pendingAsset;

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        D = ILockDepositor(target);
        address[7] memory cand = [
            0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599, 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2,
            0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0, 0xdAC17F958D2ee523a2206206994597C13D831ec7,
            0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0x6B175474E89094C44Da98b954EedeAC495271d0F,
            0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84];
        for (uint256 i = 0; i < cand.length; i++) {
            try D.allowedAssets(cand[i]) returns (bool ok) { if (ok) assets.push(cand[i]); } catch {}
        }
        for (uint256 a = 0; a < actors.length; a++)
            for (uint256 c = 0; c < assets.length; c++) {
                _fund(assets[c], actors[a], _fundAmount(assets[c]) / 1000);
                vm.prank(actors[a]); _approve(assets[c], target);
            }
__PRIV__
    }

    function tokenCount() external view returns (uint256) { return assets.length; }
    function tokens(uint256 i) external view returns (address) { return assets[i]; }
    function credited(address asset) public view returns (uint256 s) {
        for (uint256 a = 0; a < actors.length; a++) s += D.usersBalances(asset, actors[a]);
    }

    function deposit(uint256 actorSeed, uint256 aSeed, uint256 amount) external {
        if (assets.length == 0) return;
        address a = _pick(actorSeed); address asset = assets[aSeed % assets.length];
        uint256 bal = _bal(asset, a); if (bal == 0) return;
        amount = bound(amount, 1, bal);
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try D.deposit(asset, amount, "") { valueIn[a] += before - _bal(asset, a); opsOf[a]++; _count("deposit", true); }
        catch (bytes memory r) { _fail("deposit", r); }
    }

    function withdraw(uint256 actorSeed, uint256 aSeed, uint256 bps) external {
        if (assets.length == 0) return;
        address a = _pick(actorSeed); address asset = assets[aSeed % assets.length];
        uint256 amount = D.usersBalances(asset, a) * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        uint128 id = nextId++;
        vm.prank(a);
        try D.withdraw(asset, id, amount) {
            claimOwner[id] = a; claimAmt[id] = amount; claimAsset[id] = asset; openClaims.push(id);
            pending[a] += amount; pendingAsset[asset] += amount; _count("withdraw", true);
        } catch (bytes memory r) { _fail("withdraw", r); }
    }

    function claim(uint256 seed) external {
        if (openClaims.length == 0) return;
        uint256 k = seed % openClaims.length; uint128 id = openClaims[k];
        address a = claimOwner[id]; address asset = claimAsset[id];
        vm.warp(block.timestamp + D.unlockPeriod() + 1);
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try D.claim(id, a) {
            valueOut[a] += _bal(asset, a) - before; pending[a] -= claimAmt[id]; pendingAsset[asset] -= claimAmt[id];
            openClaims[k] = openClaims[openClaims.length-1]; openClaims.pop(); _count("claim", true);
        } catch (bytes memory r) { _fail("claim", r); }
    }

    function cancelWithdraw(uint256 seed) external {
        if (openClaims.length == 0) return;
        uint256 k = seed % openClaims.length; uint128 id = openClaims[k];
        address a = claimOwner[id];
        vm.prank(a);
        try D.cancelWithdraw(id) {
            pending[a] -= claimAmt[id]; pendingAsset[claimAsset[id]] -= claimAmt[id];
            openClaims[k] = openClaims[openClaims.length-1]; openClaims.pop(); _count("cancelWithdraw", true);
        } catch (bytes memory r) { _fail("cancelWithdraw", r); }
    }
}
"""

LOCK_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: per asset, the contract's balance change since setUp covers the change in what it owes the actors
    /// (still-credited balances + queued pending withdrawals).
    function invariant_solvency() public view {
        for (uint256 c = 0; c < h.tokenCount(); c++) {
            address asset = h.tokens(c);
            int256 dBal = int256(IERC20Min(asset).balanceOf(address(D))) - int256(bal0[asset]);
            int256 dOwed = int256(h.credited(asset) + _pendingOf(asset)) - int256(owed0[asset]);
            assertGe(dBal + int256(TOL), dOwed, "SOLVENCY: contract balance below credited+pending obligations");
        }
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: claimed out + still credited + queued pending never exceeds deposited in (per actor).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            uint256 cred; for (uint256 c = 0; c < h.tokenCount(); c++) cred += D.usersBalances(h.tokens(c), who);
            assertLe(h.valueOut(who) + cred + h.pending(who), h.valueIn(who) + TOL * (1 + h.opsOf(who)),
                "NO-FREE-WITHDRAW: actor got more than deposited");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

LOCK_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    ILockDepositor internal D;
    uint256 internal constant TOL = __TOL__;
    mapping(address => uint256) internal bal0;
    mapping(address => uint256) internal owed0;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        D = ILockDepositor(__TARGET__);
        h = new Handler(__TARGET__, __ACTORS__, false);
        for (uint256 c = 0; c < h.tokenCount(); c++) {
            address asset = h.tokens(c);
            bal0[asset] = IERC20Min(asset).balanceOf(__TARGET__);
            owed0[asset] = h.credited(asset);
        }
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

    function _pendingOf(address asset) internal view returns (uint256) {
        return h.pendingAsset(asset);
    }

__INVARIANTS__

    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }
    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure { __CONSOLE__ }
}
"""

# --------------------------------------------------------------------------- aavebook (deposit-to-Aave book with NGO split)
# SFI AaveImpact: deposit(token, amount, ngoPercent) supplies `token` to Aave and books a per-(user,id) share;
# withdraw(amount, id, token) pulls from Aave back to the user. ngoPercent (1%..100%) is split off to an NGO, so a
# round-trip returns less than deposited. KYC/ban are per-user; NGO distribution and oracle are gated (out of scope).
AAVEBOOK_HANDLER = r"""
interface IAaveBook {
    function factory() external view returns (address);
    function getUserBalance(address, uint256, address) external view returns (uint256);
    function getUserDepositInfo(uint256) external view returns (uint256, uint256, address, uint16);
    function deposit(address, uint256, uint16) external;
    function withdraw(uint256, uint256, address) external;
}
interface ISfiFactory { function validDepositTokenAddresses(address) external view returns (address); }

contract Handler is HandlerBase {
    IAaveBook internal immutable S;
    ISfiFactory internal factory;
    address[] public assets;          // underlying deposit tokens
    mapping(address => address) public aToken;   // underlying -> wrapped aToken (backing)
    bytes32 internal constant DEPOSIT_SIG =
        keccak256("Deposit(uint256,address,uint256,uint16,address,uint256,uint256,address)");
    mapping(address => uint256[]) internal actorIds;

    constructor(address target, uint256 nActors, bool) HandlerBase(target, nActors) {
        S = IAaveBook(target);
        factory = ISfiFactory(S.factory());
        address[3] memory cand = [
            0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48, 0xdAC17F958D2ee523a2206206994597C13D831ec7,
            0x6B175474E89094C44Da98b954EedeAC495271d0F];
        for (uint256 i = 0; i < cand.length; i++) {
            try factory.validDepositTokenAddresses(cand[i]) returns (address w) {
                if (w != address(0)) { assets.push(cand[i]); aToken[cand[i]] = w; }
            } catch {}
        }
        for (uint256 a = 0; a < actors.length; a++)
            for (uint256 c = 0; c < assets.length; c++) {
                _fund(assets[c], actors[a], _fundAmount(assets[c]) / 1000);
                vm.prank(actors[a]); _approve(assets[c], target);
            }
__PRIV__
    }

    function tokenCount() external view returns (uint256) { return assets.length; }
    function tokens(uint256 i) external view returns (address) { return assets[i]; }
    function aTokenOf(uint256 i) external view returns (address) { return aToken[assets[i]]; }
    function idCount(address a) external view returns (uint256) { return actorIds[a].length; }
    function idAt(address a, uint256 k) external view returns (uint256) { return actorIds[a][k]; }
    function userClaimable(address asset) public view returns (uint256 s) {
        for (uint256 a = 0; a < actors.length; a++) {
            uint256[] storage ids = actorIds[actors[a]];
            for (uint256 k = 0; k < ids.length; k++) {
                try S.getUserBalance(actors[a], ids[k], asset) returns (uint256 v) { s += v; } catch {}
            }
        }
    }
    /// true if the contract's own getUserBalance view reverts for any tracked position of this asset
    /// (observed: a one-unit Aave rounding makes `balance - _lastNGOBalance` underflow until the next accrual).
    function viewReverts(address asset) public view returns (bool r) {
        for (uint256 a = 0; a < actors.length; a++) {
            uint256[] storage ids = actorIds[actors[a]];
            for (uint256 k = 0; k < ids.length; k++) {
                try S.getUserBalance(actors[a], ids[k], asset) returns (uint256) {} catch { return true; }
            }
        }
    }

    function deposit(uint256 actorSeed, uint256 aSeed, uint256 amount, uint16 ngo) external {
        if (assets.length == 0) return;
        address a = _pick(actorSeed); address asset = assets[aSeed % assets.length];
        uint256 bal = _bal(asset, a); if (bal == 0) return;
        (bool okd, bytes memory d) = asset.staticcall(abi.encodeWithSignature("decimals()"));
        uint256 dec = okd && d.length >= 32 ? abi.decode(d,(uint256)) : 18;
        uint256 minDep = 10 ** dec;                 // contract requires >= 1 whole token
        if (bal < minDep) return;
        amount = bound(amount, minDep, bal);
        ngo = uint16(bound(ngo, 100, 10_000));      // MIN_SHARE_PERCENT .. MAX_SHARE_PERCENT
        uint256 before = _bal(asset, a);
        vm.recordLogs();
        vm.prank(a);
        try S.deposit(asset, amount, ngo) {
            valueIn[a] += before - _bal(asset, a); opsOf[a]++;
            // the deposit id is the first (non-indexed) word of the Deposit event: read it from the logs
            Vm.Log[] memory logs = vm.getRecordedLogs();
            for (uint256 i = 0; i < logs.length; i++) {
                if (logs[i].emitter == address(S) && logs[i].topics.length > 0 && logs[i].topics[0] == DEPOSIT_SIG) {
                    actorIds[a].push(abi.decode(logs[i].data, (uint256)));
                    break;
                }
            }
            _count("deposit", true);
        } catch (bytes memory r) { _fail("deposit", r); }
    }

    function withdraw(uint256 actorSeed, uint256 idSeed, uint256 bps) external {
        address a = _pick(actorSeed);
        uint256[] storage ids = actorIds[a];
        if (ids.length == 0) return;
        uint256 id = ids[idSeed % ids.length];
        (,, address asset,) = S.getUserDepositInfo(id);
        if (asset == address(0)) return;
        uint256 claimable;
        try S.getUserBalance(a, id, asset) returns (uint256 v) { claimable = v; }
        catch { _count("getUserBalance(reverts)", false); return; }
        uint256 amount = claimable * bound(bps, 1, 10_000) / 10_000;
        if (amount == 0) return;
        uint256 before = _bal(asset, a);
        vm.prank(a);
        try S.withdraw(amount, id, asset) { valueOut[a] += _bal(asset, a) - before; opsOf[a]++; _count("withdraw", true); }
        catch (bytes memory r) { _fail("withdraw", r); }
    }
}
"""

AAVEBOOK_INVARIANTS = {
    "attacker-profit-warp": ATTACKER_PROFIT_WARP,
    "attacker-profit": ATTACKER_PROFIT,
    "solvency": r"""
    /// SOLVENCY: per deposit token, the Aave wrapped-token (aToken) balance held by the contract covers the sum of
    /// all actors' claimable balances across their deposit ids. NGO shares only add to the backing.
    function invariant_solvency() public view {
        for (uint256 c = 0; c < h.tokenCount(); c++) {
            address asset = h.tokens(c);
            if (h.viewReverts(asset)) continue;            // contract's own view underflows this block: not measurable
            uint256 backing = IERC20Min(h.aTokenOf(c)).balanceOf(address(S));
            assertGe(backing + TOL + backing / 1e12, h.userClaimable(asset), "SOLVENCY: aToken backing below users' claimable");
        }
    }
""",
    "no-free-withdraw": r"""
    /// NO-FREE-WITHDRAW: no actor withdraws more underlying than it deposited (the NGO split makes the gap strict).
    function invariant_noFreeWithdraw() public view {
        for (uint256 a = 0; a < h.actorCount(); a++) {
            address who = h.actors(a);
            assertLe(h.valueOut(who), h.valueIn(who) + TOL * (1 + h.opsOf(who)) + h.valueIn(who) / 1e12,
                "NO-FREE-WITHDRAW: actor withdrew more than deposited");
        }
    }
""",
    "access": LENDER_INVARIANTS["access"],
}

AAVEBOOK_TEST = r"""
contract FuzzInvariants is Test {
    Handler internal h;
    IAaveBook internal S;
    uint256 internal constant TOL = __TOL__;

    function setUp() public {
        vm.createSelectFork(vm.envString("FUZZ_RPC_URL"), __BLOCK__);
        S = IAaveBook(__TARGET__);
        h = new Handler(__TARGET__, __ACTORS__, false);
        bytes4[] memory sel = new bytes4[](__NSEL__);
__SELECTORS__
        targetSelector(FuzzSelector({addr: address(h), selectors: sel}));
        targetContract(address(h));
        targetSender(address(0xF022));
    }

__INVARIANTS__

    function afterInvariant() public {
        string memory s = "";
        for (uint256 i = 0; i < h.actionCount(); i++) {
            string memory n = h.actionNames(i);
            console2_log(n, h.okCalls(n), h.tryCalls(n));
            s = string.concat(s, n, ",", vm.toString(h.okCalls(n)), ",", vm.toString(h.tryCalls(n)), ",", h.lastRevert(n), "\n");
        }
        vm.writeLine("coverage.csv", s);
    }
    function console2_log(string memory n, uint256 ok, uint256 tried) internal pure { __CONSOLE__ }
}
"""

TEMPLATES = {
    "lender": (LENDER_HANDLER, LENDER_INVARIANTS, LENDER_TEST,
               ["supply", "withdraw", "supplyCollateral", "withdrawCollateral", "borrow", "repay"],
               ["warpTime", "liquidate"]),
    "vault": (VAULT_HANDLER, VAULT_INVARIANTS, VAULT_TEST,
              ["deposit", "mint", "withdraw", "redeem", "transferShares"], ["warpTime"]),
    "token": (TOKEN_HANDLER, TOKEN_INVARIANTS, TOKEN_TEST, ["transfer", "approveAndTransferFrom"], ["warpTime"]),
    "amm": (AMM_HANDLER, AMM_INVARIANTS, AMM_TEST, ["swap", "addLiquidity", "removeLiquidity"], ["warpTime"]),
    "sir": (SIR_HANDLER, SIR_INVARIANTS, SIR_TEST,
            ["mintAPE", "mintTEA", "burnAPE", "burnTEA", "roundTripAPE", "roundTripTEA"], ["warpTime"]),
    "locktoken": (LOCK_HANDLER, LOCK_INVARIANTS, LOCK_TEST,
                  ["deposit", "withdraw", "claim", "cancelWithdraw"], ["warpTime"]),
    "aavebook": (AAVEBOOK_HANDLER, AAVEBOOK_INVARIANTS, AAVEBOOK_TEST,
                 ["deposit", "withdraw"], ["warpTime"]),
    "queuevault": (QUEUEVAULT_HANDLER, QUEUEVAULT_INVARIANTS, QUEUEVAULT_TEST,
                   ["mint", "requestWithdrawal", "claimWithdrawal"], ["warpTime"]),
    "mintredeem": (MINTREDEEM_HANDLER, MINTREDEEM_INVARIANTS, MINTREDEEM_TEST,
                   ["mint", "redeemInstant", "redeemOrQueue", "cancelRedeem"], ["warpTime"]),
    "wrapper": (WRAPPER_HANDLER, WRAPPER_INVARIANTS, WRAPPER_TEST,
                ["deposit", "stake", "withdraw", "withdrawAndUnwrap", "transferShares", "getReward"], ["warpTime"]),
}

CUSTOM_STUB = r"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

// Contract-specific invariants. This file is never overwritten by the generator.
// Add functions named invariant_<name>() that read the target / handler state and assert.
// They are picked up automatically because FuzzCustom extends the generated FuzzInvariants.
import "./Invariants.t.sol";

contract FuzzCustom is FuzzInvariants {
    // Example:
    // function invariant_myRule() public view {
    //     assertLe(someValue, someBound, "MY-RULE: explanation");
    // }
}
"""


# Positive controls: prove the invariants fire on deliberately corrupted fork state.
# Plain unit tests (no fuzzing); a passing control means "the check can detect this kind of break".
CONTROL = r"""// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.20;

import "./Invariants.t.sol";

contract FuzzControl is FuzzInvariants {
    function _expectBroken(bytes memory call, string memory what) internal {
        (bool ok, ) = address(this).call(call);
        assertFalse(ok, string.concat("CONTROL: invariant did not fire on corrupted state: ", what));
    }
__CONTROLS__
}
"""

CONTROLS = {
    "no-free-withdraw": {
        "sir": """
    function test_control_noFreeWithdraw() public {
        h.ctlBumpOut(h.actors(0), 10 ** 30);                 // the ledger claims actor0 withdrew a huge amount for free
        _expectBroken(abi.encodeCall(this.invariant_noFreeWithdraw, ()), "no-free-withdraw");
    }
""",
        "queuevault": """
    function test_control_noFreeWithdraw() public {
        address a = h.actors(0);
        uint256 b = IRebasingToken(h.OTOKEN()).balanceOf(a);
        vm.mockCall(h.OTOKEN(), abi.encodeWithSignature("balanceOf(address)", a), abi.encode(b + 1e18)); // 1 oToken for free
        _expectBroken(abi.encodeCall(this.invariant_noFreeWithdraw, ()), "no-free-withdraw");
    }
""",
    },
    "solvency": {
        "aavebook": """
    function test_control_solvency() public {
        assertGt(h.tokenCount(), 0, "CONTROL SETUP: no deposit token");
        h.deposit(0, 0, type(uint256).max, 100);              // actor0 deposits asset0 (1% to NGO) -> a real position
        address a0 = h.actors(0);
        assertGt(h.idCount(a0), 0, "CONTROL SETUP: deposit did not create a position");
        uint256 id = h.idAt(a0, 0);
        // corrupt the obligations side: the contract now claims the position is worth far more than it backs
        vm.mockCall(address(S), abi.encodeWithSignature("getUserBalance(address,uint256,address)", a0, id, h.tokens(0)),
                    abi.encode(uint256(type(uint128).max)));
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "locktoken": """
    function test_control_solvency() public {
        if (h.tokenCount() == 0) return;
        address asset = h.tokens(0);
        uint256 b = IERC20Min(asset).balanceOf(address(D));
        if (b == 0) return;
        vm.mockCall(asset, abi.encodeWithSignature("balanceOf(address)", address(D)), abi.encode(uint256(0)));
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "sir": """
    function test_control_solvency() public {
        address coll = h.tokens(0);
        uint256 r = SV.totalReserves(coll);
        if (r == 0) return;
        deal(coll, address(SV), r == 0 ? 0 : r - 1);    // vault holds one unit less than it records
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "queuevault": """
    function test_control_solvency() public {
        vm.mockCall(address(Q), abi.encodeWithSignature("totalValue()"), abi.encode(Q.totalValue() / 2));
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "mintredeem": """
    function test_control_solvency() public {
        address asset = h.tokens(0);
        uint256 real = IERC20Min(asset).balanceOf(h.MCT());
        // the MCT books one unit more than it really holds (works even if collateralBalance is 0 at this block)
        vm.mockCall(h.MCT(), abi.encodeWithSignature("collateralBalance(address)", asset), abi.encode(real + 1));
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "wrapper": """
    function test_control_solvency() public {
        if (W.totalSupply() == 0) return;
        vm.mockCall(h.POOL(), abi.encodeWithSignature("balanceOf(address)", address(W)), abi.encode(uint256(0)));
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "lender": """
    function test_control_solvency() public {
        (address loan,,) = h.marketAt(0);
        deal(loan, address(L), 0);                       // the contract loses its loan-token backing
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "vault": """
    function test_control_solvency() public {
        vm.mockCall(address(V), abi.encodeWithSignature("totalAssets()"), abi.encode(uint256(0)));
        if (V.totalSupply() == 0) return;
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
        "amm": """
    function test_control_solvency() public {
        deal(h.T0(), address(P), 0);
        _expectBroken(abi.encodeCall(this.invariant_solvency, ()), "solvency");
    }
""",
    },
    "k-monotonic": {
        "amm": """
    function test_control_kmonotonic() public {
        uint256 b = IERC20Min(h.T0()).balanceOf(address(P));
        deal(h.T0(), address(P), b / 2);                 // half of token0 disappears from the pair
        P.sync();
        _expectBroken(abi.encodeCall(this.invariant_kPerShare, ()), "k-monotonic");
    }
""",
    },
    "conservation": {
        "mintredeem": """
    function test_control_conservation() public {
        address asset = h.tokens(0);
        address a = h.actors(0);
        deal(asset, a, IERC20Min(asset).balanceOf(a) + 1);
        _expectBroken(abi.encodeCall(this.invariant_conservation, ()), "conservation");
    }
""",
        "wrapper": """
    function test_control_conservation() public {
        address a = h.actors(0);
        deal(h.LP(), a, IERC20Min(h.LP()).balanceOf(a) + 1);
        _expectBroken(abi.encodeCall(this.invariant_conservation, ()), "conservation");
    }
""",
        "lender": """
    function test_control_conservation() public {
        address tok = h.tokens(0);
        address a = h.actors(0);
        deal(tok, a, IERC20Min(tok).balanceOf(a) + 1);  // one token unit appears out of nothing
        _expectBroken(abi.encodeCall(this.invariant_conservation, ()), "conservation");
    }
""",
        "amm": """
    function test_control_conservation() public {
        address a = h.actors(0);
        deal(h.T0(), a, IERC20Min(h.T0()).balanceOf(a) + 1);
        _expectBroken(abi.encodeCall(this.invariant_conservation, ()), "conservation");
    }
""",
        "token": """
    function test_control_conservation() public {
        address a = h.actors(0);
        deal(address(K), a, K.balanceOf(a) + 1);
        _expectBroken(abi.encodeCall(this.invariant_conservation, ()), "conservation");
    }
""",
    },
}
