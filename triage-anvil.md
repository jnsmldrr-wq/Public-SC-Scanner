# Triage: Anvil (EVM, batch 2)

- Adres: `0x5d2725fde4d7aa3388da4519ac0449cc031d675f` = **CollateralVault** (0.8.25, optimizer 999.999 runs). Geen proxy.
- Fork? Nee, eigen code.
- Datum: 2026-10-05. Read-only.

**Scan:** High 0 · Medium 3 · Low 5 (6 verlaagd: governance). Ruwe output: `evm-reports/batch2/anvil.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `upgradeAccount(address,address[],uint256[])` "beheerdersnaam zonder gate" (eigen detector, lage confidence) | GOUD-label | **Fout-positief.** Hij werkt alleen op het **eigen** saldo (`accountBalances[msg.sender]`), met een check `available < amount`. Het doelcontract moet door governance zijn goedgekeurd (`permittedCollateralUpgradeContracts`). Gewone gebruikersmigratie. |
| `reentrancy-no-eth` | GOUD-label | De saldo-mutatie gebeurt vóór de externe call (checks-effects-interactions in `upgradeAccount`/`withdraw`). Geen misbruikpad gevonden. |
| `reentrancy-balance` | LAAG | Governance-pad. |

**Detector-notitie:** schrijven via een storage-pointer (`accountBalances[msg.sender][t].available = …`) wordt nog niet als per-gebruiker-write herkend. Dat is een verbeterpunt voor de eigen heuristiek.
