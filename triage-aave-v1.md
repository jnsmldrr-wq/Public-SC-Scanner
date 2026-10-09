# Triage: Aave V1 (EVM, batch 1)

- Adres (gescand): `0x3dfd23a6c5e8bbcfc9581d2e864a68feb6a076d3`. Dat is `InitializableAdminUpgradeabilityProxy`, Solidity 0.5.14.
- Implementation: `0x0e26e0bf83b4ec2cb0dcbc037bb01da5bb352eae` = **LendingPoolCore** (0.5.17), bevestigd via de EIP-1967-slot.
- Fork? Nee. Aave V1 is de oorspronkelijke Aave-code. De inventaris-notitie "integreert Aave" verviel na de aanscherping.
- Datum: 2026-10-05. Methode: Slither + SolScan-triage, read-only.

**Scan:** High 3 · Medium 31 · Low 29 (na triage). Ruwe output: `evm-reports/batch1/aave-v1.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `controlled-delegatecall` in `InitializableUpgradeabilityProxy.initialize(address,bytes)` | LAAG (eenmalig) | Standaard OZ-proxy-initializer met de guard `require(_implementation() == address(0))`. De proxy is al geïnitialiseerd, want de implementation-slot is gevuld. Deze guard is na deze batch aan de privilege-detectie toegevoegd. |
| 3× `uninitialized-state` (`LendingPoolLiquidationManager.addressesProvider/core/dataProvider`) | GOUD-label | **Fout-positief.** In Aave V1 wordt de LiquidationManager via `delegatecall` vanuit de LendingPool uitgevoerd, dus die variabelen zijn de storage-slots van de LendingPool zelf. Slither ziet dat ontwerp niet. |
| Medium (unused-return, uninitialized-local, divide-before-multiply, incorrect-equality) | GOUD-label | Bekende ruis van Slither op oude 0.5-code. Geen pad gevonden waarlangs een gebruiker geld van een ander raakt. |
| `arbitrary-send-*`, `unprotected-upgrade`, `controlled-array-length` | LAAG | Alleen via LendingPool/configurator/admin bereikbaar. |

Aave V1 is uitgefaseerd en uitgebreid geaudit.
