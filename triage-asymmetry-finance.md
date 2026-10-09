# Triage: Asymmetry Finance (EVM, batch 2)

- Adres: `0xe95a203b1a91a908f9b9ce46459d101078c2c3cb` = `AdminUpgradeabilityProxy` (0.6.8).
- Implementation: `0xe672e0e0101a7f58d728751e2a5e6da5ff1fda64` = **AETH_R21** (0.6.11), bevestigd via de EIP-1967-slot.
  - Het gaat om de **Ankr aETH**-token. De DeFiLlama-adapter van Asymmetry wijst naar dit contract als gehouden asset; het is dus niet per se eigen Asymmetry-logica.
- Datum: 2026-10-05. Read-only.

**Scan:** High 11 · Low 3. Ruwe output: `evm-reports/batch2/asymmetry-finance.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| 6× `incorrect-return` (`AdminUpgradeabilityProxy.ifAdmin/admin/upgradeTo…`) | GOUD-label | **Fout-positief.** Bekend Slither-patroon bij een OZ-transparent proxy (assembly-return in `ifAdmin`). |
| 5× `shadowing-state` (`AETH_R21._totalSupply/_name/_symbol/_decimals/__gap`) | n.v.t. | De eigen kopieën worden alleen in de initializer op 0 gezet en verder **nooit gebruikt**. De geërfde `ERC20UpgradeSafe` gebruikt consistent zijn eigen (private) variabelen. Het zijn dode slots, geen boekhoudfout. |

**Aandachtspunt voor de inventaris:** dit adres is waarschijnlijk een gehouden token (Ankr aETH) en niet Asymmetry's eigen kerncontract. Het "hoofdcontract" voor dit protocol is dus mogelijk verkeerd gekozen.
