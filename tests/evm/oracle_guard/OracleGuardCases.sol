// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

// TEST FIXTURE for Module 3 (ORACLE-GUARD). Local test-suite only; never deployed.
// A Chainlink-shaped feed is forced to anomalous readings (stale / zero / deviated). A protocol with proper
// input validation must REVERT on those; one without validation acts on the bad price. No attack primitive:
// the "skew" is a test-only forced value (what a misbehaving/compromised feed would return), not a swap/trade.

interface IAggregatorV3 {
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80);
    function decimals() external view returns (uint8);
}

/// Minimal settable Chainlink-shaped feed (stands in for a real aggregator in the positive control).
contract ToyFeed is IAggregatorV3 {
    int256 public answer;
    uint256 public updatedAt;
    uint80 public roundId;
    function decimals() external pure returns (uint8) { return 8; }
    function set(int256 a, uint256 u, uint80 r) external { answer = a; updatedAt = u; roundId = r; }
    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80) {
        return (roundId, answer, updatedAt, updatedAt, roundId);
    }
}

/// BUG: reads latestRoundData and uses the answer with no staleness / positivity check.
contract UnguardedConsumer {
    IAggregatorV3 public feed;
    constructor(IAggregatorV3 f) { feed = f; }
    function price() external view returns (uint256) {
        (, int256 a, , , ) = feed.latestRoundData();
        return uint256(a);               // no answer>0, no updatedAt freshness check
    }
}

/// Safe: rejects non-positive and stale answers, mirroring the FIX the report would recommend.
contract GuardedConsumer {
    IAggregatorV3 public feed;
    uint256 public constant MAX_AGE = 1 hours;
    constructor(IAggregatorV3 f) { feed = f; }
    function price() external view returns (uint256) {
        (uint80 rid, int256 a, , uint256 upd, uint80 air) = feed.latestRoundData();
        require(a > 0, "bad price");
        require(upd != 0 && block.timestamp - upd <= MAX_AGE, "stale price");
        require(air >= rid, "stale round");
        return uint256(a);
    }
}
