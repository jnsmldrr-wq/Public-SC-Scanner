# Triage — Opyn Gamma (Ethereum)

Analyse: alleen lezen (geverifieerde source + read-only `eth_call`), peildatum 2026-10-05.
Uitkomst: **geen GOUD**. Wel **één oracle-observatie op een actief pad**, met impact **laag**
(alleen relevant bij een storing van de Chainlink-feed).

## Geanalyseerde (live) contracten

| Rol | Adres | Code |
|---|---|---|
| AddressBook | `0x1e31f2dcbad4dc572004eae6355fb18f9615cbe4` | via `MarginPool.addressBook()` |
| Controller (proxy) | `0x4ccc2339f87f6c59c6893e1a678c2266ca58dc72` | → impl `0xcc2fd280a669a4453b30b5e72871ad3e2a2663d0`, bevestigd via ZeppelinOS-slot |
| Oracle | `0x789cd7ab3742e23ce0952f6bc3eb3a73a0e08833` | `Oracle` (0.6.10) |
| MarginCalculator | `0xfaa67e3736572645b38af7410b3e1006708e13f4` | `MarginCalculator` (0.6.10) |
| WETH-pricer | `0x908fa5e6f8e997c32a15ebdbe7377a5a4321918c` | `ChainLinkPricer` → Chainlink ETH/USD `0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419` |
| MarginPool | `0x5934807cc0654d46755ebd2848840b616256c6ef` | alleen `onlyController`-transfers |

## Oracle-observatie: live prijs zonder versheidscontrole in de naked-margin-berekening

**Waar**

| Stap | Plek |
|---|---|
| `ChainLinkPricer.getPrice()` leest `latestRoundData()`, controleert alleen `answer > 0`; `updatedAt` wordt niet tegen `block.timestamp` gelegd | `ChainlinkPricer.sol:94-95` |
| `Oracle.getPrice(asset)` geeft die waarde door | `Oracle.sol:474-480` |
| `MarginCalculator._getMarginRequired` gebruikt `oracle.getPrice(shortUnderlyingAsset)` voor **naked-margin-vaults** (`vaultType == 1`) | `MarginCalculator.sol:1558`, `:1605` |
| Ook in `_convertAmountOnLivePrice` | `MarginCalculator.sol:1860-1861` |
| Controller toetst elke vault-actie via `getExcessCollateral` → `_verifyFinalState` | `Controller.sol:1894-1896` |

**Leeft het pad?** Ja, read-only bevestigd:

- `getNakedCap(WETH)` = 5.000 WETH, `getNakedPoolBalance(WETH)` ≈ **188,9 WETH**.
- `getNakedCap(USDC)` = 10.000.000 USDC, `getNakedPoolBalance(USDC)` ≈ 3.100 USDC.
- Het systeem is niet gepauzeerd.
- Een naked-vault openen is permissionless: `_openVault` vereist alleen de eigenaar of een operator van het account. Het volume wordt begrensd door de cap.
- De ETH/USD-feed is actief: bij de peildatum was de laatste update ongeveer 0,7 uur oud.

**Wat kan misgaan.** Stel dat de Chainlink-feed bevriest of wordt uitgefaseerd terwijl de markt beweegt. Dan rekent de margin-check voor het openen, minten en opnemen van collateral in naked vaults met een verouderde onderliggende prijs. In één richting staat het systeem dan te weinig collateral toe; in de andere richting worden gebruikers ten onrechte geblokkeerd.

Liquidaties gebruiken een ander mechanisme en lopen dit risico niet:
- De liquidator kiest een `roundId`.
- `isLiquidatable` eist dat de timestamp van die round na de laatste vault-update ligt.

Settlement bij expiry loopt ook via een ander pad, met locking- en disputeperiode.

**Impact: laag.** Het pad is actief, maar gaat alleen mis bij een storing van een hoofd-feed (ETH/USD). Een gewone gebruiker kan het niet zelf veroorzaken, en het volume is begrensd door de naked cap. Dit is een hardening-punt, geen exploiteerbare bug.

**Fix.** Voeg in `ChainLinkPricer.getPrice()` een leeftijdscontrole toe:

```solidity
(, int256 answer, , uint256 updatedAt, ) = aggregator.latestRoundData();
require(answer > 0, "ChainLinkPricer: price is lower than 0");
require(block.timestamp - updatedAt <= maxDelay, "ChainLinkPricer: stale price");
```

Gebruik voor `maxDelay` de heartbeat van de feed plus een marge. Alternatief: doe de controle centraal in `Oracle.getPrice`.

## Overige meldingen (afgedaan)

| Melding | Oordeel |
|---|---|
| `Oracle.setExpiryPrice` "zonder gate" | onjuist: `require(msg.sender == assetPricer[_asset])` + locking-periode |
| Controller reentrancy / uninitialized-local | `operate` met acties op eigen vaults; geen extern misbruik gevonden |
| `MarginPool.transferToPool` "arbitrary from" | `onlyController` → LAAG |
