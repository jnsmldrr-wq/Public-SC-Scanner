// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
// TEST FIXTURE for Module 4 (time). Local only. A time-dependent bug is only reachable once time advances:
// BuggyVesting lets claimable exceed the allocation after enough time (no cap); SafeVesting caps at allocation.
contract BuggyVesting {
    uint256 public start; uint256 public rate; uint256 public allocation;
    constructor(uint256 _rate, uint256 _alloc) { start = block.timestamp; rate = _rate; allocation = _alloc; }
    function claimable() public view returns (uint256) { return (block.timestamp - start) * rate; } // BUG: no cap
}
contract SafeVesting {
    uint256 public start; uint256 public rate; uint256 public allocation;
    constructor(uint256 _rate, uint256 _alloc) { start = block.timestamp; rate = _rate; allocation = _alloc; }
    function claimable() public view returns (uint256) {
        uint256 v = (block.timestamp - start) * rate;
        return v > allocation ? allocation : v;
    }
}
