"""Invariant fuzzing for EVM contracts: generates a Foundry invariant suite that forks mainnet
at a live contract, drives it with a handler of fuzzed actor calls, and checks safety rules.

Everything runs locally against a forked state (anvil/forge fork). Nothing is ever broadcast.
"""
