# Triage: Brickken (EVM, batch 3)

- Adres: `0x91af681c85ca98efc5d69c1b62e6f435030969db` = `ERC1967Proxy` → **STOFactoryManagedUpgradeable** (RWA/security-token-offerings).
  - Het oracle-gebruik zit in het helper-contract **`PriceAndSwapManager`** (`contracts/sto/helpers/PriceAndSwapManager.sol`), dat in dezelfde verified source zit.
- Fork? Nee, eigen code. `UniswapLibraries.sol` is een kopie van Uniswap's `FullMath`.
- Datum: 2026-10-05. Read-only. Slither + SolScan-triage + oracle-check.

**Scan:** High 1 · Medium 7 · Low 6. Oracle-dekking: ja (Chainlink). Ruwe output: `evm-reports/batch3/brickken.*`.

## Oracle-gat (defensief: ontbrekende bescherming + fix)

**EVM-ORACLE-FRESH**: `PriceAndSwapManager.getUSDPriceOfPaymentToken(...)` (`PriceAndSwapManager.sol:167`) en `_getChainlinkTWAP(...)` (`:299`).

**Wat ontbreekt:**
1. **Leeftijdscontrole.** `latestRoundData()` levert `updatedAt`, maar die wordt nergens met `block.timestamp` vergeleken.
   - `_getChainlinkTWAP` middelt over rondes binnen `[updatedAt − twapInterval, updatedAt]`, dus relatief aan de **laatste update**.
   - Als de feed niet meer wordt bijgewerkt, wordt een oude prijs gewoon gebruikt.
2. **Positiviteitscontrole die 0 uitsluit.** De check is `if (finalPrice < 0) revert`, en een prijs van **0** komt daardoor door.

**Fix-advies:**
- `require(block.timestamp - updatedAt <= MAX_AGE)`, met `MAX_AGE` passend bij de heartbeat van de feed;
- `require(price > 0)` (of `finalPrice > 0`) vóór gebruik;
- optioneel: dezelfde leeftijdscheck in de middelings-loop.

## Overige findings: niks echts

| Melding | Oordeel |
|---|---|
| `incorrect-exp` in `FullMath.mulDiv` (`UniswapLibraries.sol:249`) | **Fout-positief.** Uniswap's `FullMath` gebruikt `(3 * denominator) ^ 2` bewust als startwaarde voor de Newton-iteratie. |
| Overige Medium/Low | Geen pad gevonden waarlangs een gebruiker zonder rechten geld van een ander raakt. Beheerfuncties zijn LAAG. |
