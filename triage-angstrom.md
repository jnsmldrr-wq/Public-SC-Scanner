# Triage: Angstrom (EVM, batch 2)

- Adres: `0x0000000aa232009084bd71a5797d089aa4edfad4` = **Angstrom** (0.8.26, optimizer 21.000 runs, evm cancun). Geen proxy.
- Fork? Nee. Eigen code: een hook/settlement-laag **op Uniswap V4** (`unlockCallback`, `IPoolManager`). De Uniswap-V4-kern zelf is extern.
- Datum: 2026-10-05. Read-only.

**Scan:** High 1 · Medium 14 · Low 6 (281 dependency-findings weggefilterd). Ruwe output: `evm-reports/batch2/angstrom.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `incorrect-shift` in `OrderInvalidation._invalidateNonce` (`src/modules/OrderInvalidation.sol:21`) | GOUD-label (via `unlockCallback`) | **Fout-positief.** `shl(and(nonce, 0xff), 1)` is in Yul de juiste volgorde (`shl(shift, value)`): 1 wordt verschoven met de laagste 8 bits van de nonce (Permit2-achtige bitmap). Slither leest het verkeerd. |
| Medium: `unused-return` (8), `uninitialized-local`, `incorrect-equality`, `write-after-write`, `divide-before-multiply` | GOUD-label | Typische ruis in sterk geoptimaliseerde assembly- en V4-integratiecode. Geen pad gevonden waarlangs een gebruiker geld van een ander raakt. |
