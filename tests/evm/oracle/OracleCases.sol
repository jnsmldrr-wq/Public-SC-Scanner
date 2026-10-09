// SPDX-License-Identifier: MIT
// Oracle-safety regression cases for SolScan-EVM (unprotected vs protected). NOT for deployment.
pragma solidity ^0.8.24;

interface IUniswapV2Pair { function getReserves() external view returns (uint112, uint112, uint32); }
interface IUniswapV2Router {
    function getAmountsOut(uint256 amountIn, address[] calldata path) external view returns (uint256[] memory);
    function swapExactTokensForTokens(uint256, uint256, address[] calldata, address, uint256) external returns (uint256[] memory);
}
interface IUniswapV3Pool {
    function slot0() external view returns (uint160, int24, uint16, uint16, uint16, uint8, bool);
    function observe(uint32[] calldata secondsAgos) external view returns (int56[] memory, uint160[] memory);
}
interface AggregatorV3Interface {
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
    function latestAnswer() external view returns (int256);
}

// ---------- SPOT ----------
contract UnprotectedSpotV2 {                       // expect: SPOT + SINGLE
    IUniswapV2Pair public pair;
    function collateralValue(uint256 amount) external view returns (uint256) {
        (uint112 r0, uint112 r1, ) = pair.getReserves();
        return amount * r1 / r0;
    }
}

contract ProtectedTwapV3 {                         // expect: nothing (time-averaged)
    IUniswapV3Pool public pool;
    function averageTick(uint32 period) external view returns (int56) {
        uint32[] memory ago = new uint32[](2);
        ago[0] = period; ago[1] = 0;
        (int56[] memory tickCumulatives, ) = pool.observe(ago);
        return (tickCumulatives[1] - tickCumulatives[0]) / int56(uint56(period));
    }
}

contract SwapOnlyRouterUse {                       // expect: nothing (pool numbers used for a swap)
    IUniswapV2Router public router;
    function swapWithSlippage(uint256 amountIn, address[] calldata path, uint256 bps) external {
        uint256[] memory out = router.getAmountsOut(amountIn, path);
        uint256 minOut = out[out.length - 1] * (10000 - bps) / 10000;
        router.swapExactTokensForTokens(amountIn, minOut, path, msg.sender, block.timestamp);
    }
}

// ---------- FRESH ----------
contract UnprotectedLatestAnswer {                 // expect: FRESH (Medium) + SINGLE
    AggregatorV3Interface public feed;
    function price() external view returns (int256) { return feed.latestAnswer(); }
}

contract UnprotectedRoundData {                    // expect: FRESH (High: both checks missing) + SINGLE
    AggregatorV3Interface public feed;
    function price() external view returns (uint256) {
        (, int256 answer, , , ) = feed.latestRoundData();
        return uint256(answer);
    }
}

contract ProtectedChainlink {                      // expect: nothing (fresh + positive + sanity bound)
    AggregatorV3Interface public feed;
    uint256 public constant MAX_AGE = 1 hours;
    uint256 public constant MIN_PRICE = 1e6;
    uint256 public constant MAX_PRICE = 1e12;
    function price() external view returns (uint256) {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        require(answer > 0, "bad price");
        require(block.timestamp - updatedAt <= MAX_AGE, "stale");
        uint256 p = uint256(answer);
        require(p >= MIN_PRICE && p <= MAX_PRICE, "out of bounds");
        return p;
    }
}

contract ProtectedChainlinkViaHelper {             // expect: nothing (checks live in an internal helper)
    AggregatorV3Interface public feed;
    uint256 public maxPrice = 1e12;
    function price() external view returns (uint256) {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        _validate(answer, updatedAt);
        return uint256(answer);
    }
    function _validate(int256 answer, uint256 updatedAt) internal view {
        if (answer <= 0) revert("bad price");
        if (updatedAt < block.timestamp - 3600) revert("stale");
        if (uint256(answer) > maxPrice) revert("bound");
    }
}

// ---------- SINGLE ----------
contract ProtectedTwoSources {                     // expect: nothing (Chainlink checked + TWAP second source)
    AggregatorV3Interface public feed;
    IUniswapV3Pool public pool;
    uint256 public maxDeviationBps = 200;
    function price() external view returns (uint256 p) {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        require(answer > 0 && block.timestamp - updatedAt <= 3600, "chainlink");
        uint32[] memory ago = new uint32[](2);
        ago[0] = 1800; ago[1] = 0;
        pool.observe(ago);
        p = uint256(answer);
    }
}

contract IntervalOnlyChainlink {                   // expect: FRESH only (no age check vs block.timestamp; zero price allowed)
    AggregatorV3Interface public feed;
    uint256 public twapInterval = 1800;
    function price() external view returns (uint256) {
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        uint256 startTime = updatedAt - twapInterval;   // window relative to the last update only
        if (updatedAt < startTime) revert("window");
        if (answer < 0) revert("negative");             // zero still passes
        return uint256(answer);                          // TWAP-like averaging elided
    }
}
