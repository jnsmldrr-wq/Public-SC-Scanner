# Triage: Arrakis V1 (EVM, batch 2)

- Adres: `0xea1aff9dbffd1580f6b81a3ad3589e66652db7d9` = `EIP173ProxyWithReceive` (0.8.4).
- Implementation: `0xb9bb2856e0af9d3e855b0173a40059fc29b632da` = **ArrakisFactoryV1**, bevestigd via de EIP-1967-slot.
- Fork? Nee. Eigen code: een factory voor Uniswap-V3-LP-vaults (G-UNI/Arrakis). De vault-pools zelf zijn aparte contracten.
- Datum: 2026-10-05. Read-only.

**Scan:** High 1 · Medium 5 · Low 5 (7 verlaagd). Ruwe output: `evm-reports/batch2/arrakis-v1.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `uninitialized-state` `ArrakisFactoryV1Storage.gelatoDeployer` | GOUD-label | Alleen gebruikt in de view-functie `getGelatoPools()`. Geen geld of state-wijziging. |
| `controlled-delegatecall` (2×) | LAAG | Proxy-initializer en upgrade: admin/eenmalig. |
| `reentrancy-no-eth`, `unused-return`, `divide-before-multiply` | GOUD-label | In het deploy- en factory-pad; geen geld van derden betrokken. |

**Beperking:** het DeFiLlama-adres is de factory. De afzonderlijke Arrakis-vaults (waar het LP-geld zit) zijn niet apart gescand.
