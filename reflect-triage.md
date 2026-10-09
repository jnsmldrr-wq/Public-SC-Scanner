# Reflect program library: triage

Source: https://github.com/donjne/reflect-program-library (commit e0ac961, 2025-01-04)
Raw scanner output: `reflect-report.md` / `reflect-report.json` (47 High, 9 Medium).
After triage: **3 real candidates**. Everything else is off-chain, a false positive, or not exploitable.

## Real candidates

### 1. Insurance fund: inverted receipt-mint ratio (value theft between depositors)
`insurance-fund/programs/insurance-fund/src/helpers/calculate_receipts_on_mint.rs:22-26`

- Deposit mints `deposit * total_deposits / receipt_supply` receipts.
- Withdraw (`instructions/user/withdraw.rs:50-60`) pays out `receipts * total_deposits / receipt_supply`.
- The deposit side is inverted. The correct formula is `deposit * supply / total_deposits`.
- Whenever `total_deposits != supply`, deposits are mispriced:
  - **`total_deposits > supply`:** anyone can cause this by transferring tokens straight into the hot or cold vault, because `total_deposits` is read from the vault balances. New deposits are then over-minted.
    - Example: pool 1000/1000. Donate 1000, then deposit 9000: 18000 receipts.
    - Those receipts redeem for ~10421 on a 10000 cost.
    - The existing depositors drop from 1000 to ~578.
    - The bigger the deposit, the closer the attacker gets to all of the other depositors' funds. The only limit is `deposit_cap`.
  - **`total_deposits < supply` (after any slash):** with no attacker at all, each new depositor is under-minted.
    - After a 20% slash, depositing 1000 is worth 800 the moment it lands.
- Money attached: yes, the user collateral in the vaults.

### 2. Tokenised bonds: `total_receipt_supply` never decremented (later withdrawers underpaid, funds stuck)
`reflect-tokenised-bonds/programs/reflect-tokenised-bonds/src/instructions/withdraw.rs:36-38`

- `deposit.rs:43` adds to `vault.total_receipt_supply`.
- `withdraw` burns receipts but never subtracts them from `total_receipt_supply`.
- Every withdrawal after the first divides by an inflated supply:
  - The withdrawer receives less than their share.
  - The difference stays locked in the pools for good.
- Example: two users with 100 receipts each, pool 200.
  - User A withdraws 100.
  - User B gets `100 * 100 / 200 = 50` instead of 100.
- Related: `deposit.rs:38` prices new receipts as `amount * deposit_pool / (deposit_pool + reward_pool)`. It should use `total_receipt_supply`. Once the deposit pool and the supply diverge, the mint and redeem sides disagree.

### 3. Tokenised bonds: lockup PDA collides globally (anyone can block all lockups)
`reflect-tokenised-bonds/programs/reflect-tokenised-bonds/src/instructions/lockup.rs:70-73`

- The lockup PDA seed is `[LOCKUP_SEED, user_account.lockups]`, but `lockups` is never incremented. It is always 0.
- The seed also does not include the user, so every user maps to the same PDA, `[LOCKUP_SEED, 0]`.
- One open lockup makes `init` fail for everyone else until its owner withdraws.
- Bad input: any user calls `lockup` once. Every later `lockup` call by anyone fails with "account already in use".
- Impact: denial of service, no theft.

## Discounted (and why)

- **SOL-CFG-201 (×4).** False positive for 3 programs: the workspace `Cargo.toml` sets `overflow-checks = true`. `reflect-single-pool` is a fork of the SPL single-pool. Plain `+`/`-` therefore panics instead of wrapping, so the ARITH-101/102 hits become reverts at worst.
- **CLI paths (`reflect-single-pool/cli/...`).** Off-chain.
- **`reflect-single-pool/program/src/processor.rs:1441-1520`.** Inside `#[cfg(test)]` proptests.
- **`processor.rs:278`, `error.rs`.** Not value arithmetic.
- **SOL-CPI-004 in single-pool.** Program ids are checked by `check_stake_program`, `check_token_program` and `check_system_program`.
- **SOL-CPI-004 in `ssm/.../sell_stake.rs:208/235/247`.** `stake_program` is pinned with an `address =` constraint.
- **SOL-TYPE-003 in `sell_stake.rs:63`.** `try_deserialize` doesn't check the owner. But a fake Bid's vault PDA is empty, so the transfer fails. Writing back to a foreign account is also rejected by the runtime.
- **SOL-TYPE-003 in the Pyth/Switchboard helpers.** The oracle address is pinned to `asset.oracle` (`restake.rs` accounts).
- **SOL-ARITH-101/103 in SSM `place_bid`/`sell_stake` (f64 math).** The rate maths uses floating point, which is sloppy but rounds down in the vault's favour. At worst the last fill of a bid could fail by about 1 lamport (DoS on one bid).
- **`restake.rs:65/92`, casts at 87/109.** Covered by overflow-checks. They involve timestamps or decimals, not amounts an attacker controls.
- **`lockup.rs:112` (`amount - hot_wallet_deposit`).** The hot share is a fraction of the amount.
- **SOL-INIT-006 (`add_admin.rs:69`, bonds `lockup.rs:52`).** Admin-only, or a per-user counter PDA with nothing to reset.

## Before contacting anyone (step 5)

Check on solscan.io that these program ids are live, executable programs on mainnet:

| Program | Program id |
|---|---|
| insurance-fund | `2MN1Dbnu7zM9Yj4ougn6ZCNNKevrSvi9AR56iawzkye8` |
| reflect-tokenised-bonds | `6ZZ1sxKGuXUBL8HSsHqHaYCg92G9VhMNTcJv1gFURCop` |
| solana-stake-market | `sSmYaKe6tj5VKjPzHhpakpamw1PYoJFLQNyMJD3PU37` |
| reflect-single-pool | `rFLUicC93hnZMVZc2hhd4oetXEDG4ja6TaFVSAftsVe` |

This repo is a personal fork (`donjne/...`), not Reflect's official org. Also check:

- Does the official Reflect repo contain the same code?
- Has the bug already been fixed there?
