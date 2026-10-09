# Brickken — onderbouwing oracle-observatie (PriceAndSwapManager)

Status: read-only analyse van publiek geverifieerde broncode en publieke on-chain state
(alleen `eth_call` / `eth_getCode`, geen transacties). Peildatum: 2026-10-05.
Security-contact volgens de broncode (`@custom:security-contact`): tech@brickken.com

## Samenvatting

`PriceAndSwapManager.getUSDPriceOfPaymentToken` leest een Chainlink-feed zonder
versheidscontrole (`updatedAt` wordt niet tegen `block.timestamp` gelegd) en laat een
prijs van **0** door (alleen `< 0` wordt geweigerd). Die prijs bepaalt in `buyToken`
hoeveel STO-tokens een investeerder krijgt.

**Belangrijk voor de impact:** op Ethereum gebruikt op de peildatum **geen enkele van
de 52 escrows** een Chainlink-oracle. Bij allemaal staat `paymentTokenOracle` op
`address(0)`, en dan geeft de functie een vaste eenheidsprijs (1e18) terug zonder de
feed te lezen. Het Chainlink-pad staat live dus niet aan. Wij noemen dit daarom een
**defensieve hardening-aanbeveling (laag / informational)**, geen actief
exploiteerbaar probleem.

## 1. Locatie

Contract `PriceAndSwapManager`, Ethereum `0x36fb65754b70982d1aa0d5cedefd8bc614af8fd6`.
Het contract is geen proxy, is geverifieerd en gecompileerd met Solidity 0.8.19. De
regelnummers hieronder gelden voor de geverifieerde bron
(`contracts/sto/helpers/PriceAndSwapManager.sol`).

| Regel | Code | Observatie |
|---|---|---|
| 154 | `function getUSDPriceOfPaymentToken(IChainlinkPriceFeed paymentTokenOracle, uint256 twapInterval) public view` | Prijsfunctie die de escrows aanroepen. |
| 163–165 | `if (address(paymentTokenOracle) == address(0)) return 1e18;` | Zonder oracle: vaste eenheidsprijs; de feed wordt niet gelezen. |
| 167 | `(uint80 roundId, int256 price, , uint256 updatedAt, ) = paymentTokenOracle.latestRoundData();` | `updatedAt` wordt alleen als ankerpunt voor de TWAP gebruikt, niet als leeftijdscontrole. |
| 169 | `if (finalPrice < 0) revert Errors.NotNegativeValue(finalPrice);` | Een prijs van precies 0 komt erdoor. |
| 299–330 | `_getChainlinkTWAP(...)` | Middelt eerdere rondes binnen `twapInterval`, gerekend vanaf de *laatste update* (r. 309/319) en niet vanaf "nu". Een bevroren feed levert daardoor gewoon een gemiddelde van oude rondes op. Rondes met `answer <= 0` tellen ook mee in het gemiddelde. |

In het hele bestand komt `block.timestamp` niet voor.

Het oracle-adres staat per escrow in `STOEscrowUpgradeable.paymentTokenOracle` (r. 135).
Het wordt gezet bij initialisatie (r. 763) en kan daarna alleen via
`setPaymentToken(...)` worden aangepast. Die functie vereist `DEFAULT_ADMIN_ROLE`
(`STOEscrowManagedUpgradeable.sol` r. 107–118 → `_setPaymentToken` r. 1196–1226). Ze kan
alleen worden aangeroepen als er geen lopende uitgifte is, en een nul-oracle is
uitdrukkelijk toegestaan (r. 1209).

## 2. Gebruikte feeds (on-chain gelezen)

Fabriek `STOFactoryManagedUpgradeable` (proxy `0x91af681c85ca98efc5d69c1b62e6f435030969db`):
`idSTOs() = 52`, escrows via `stoEscrows(i)`. Per escrow is
`paymentTokenOracle()`, `paymentToken()`, `twapInterval()`, `issuanceIndex()`,
`isStarted()` en `isEnded()` gelezen.

| | Aantal escrows |
|---|---|
| `paymentTokenOracle == address(0)` | **52 van 52** |
| `paymentTokenOracle != address(0)` | 0 |
| Payment token USDT | 24 |
| Payment token USDC | 16 |
| Payment token EURC | 11 |
| Payment token HAI (`0x05fb…9a63`) | 1 |
| Uitgifte op peildatum lopend (gestart, niet beëindigd) | 4 (`0x7497…5057`, `0x6d45…ed3d`, `0xf4bf…d461`, `0xee28…b11a`) |

Er is dus **geen Chainlink-feed in gebruik**. Paar, heartbeat, deviation-drempel en
onderhoudsstatus van een feed zijn daardoor niet van toepassing. Ze worden pas
relevant als een admin via `setPaymentToken` een oracle instelt.

Dezelfde contractadressen zijn ook gecontroleerd op Polygon, BNB Chain, Base, Optimism,
Arbitrum en Avalanche. Daar staat geen code (`eth_getCode` = `0x`). Brickken-deployments
op andere adressen zijn niet onderzocht.

## 3. Wat hangt eraan (geldstroom)

`STOEscrowUpgradeable.buyToken(tokenUsed, amountOfTokens, minAmountExpected, onBehalfOf)`
(r. 315, `external`, `nonReentrant`) loopt zo:

1. `_checkValidStatus` (r. 944): de aanroeper moet gewhitelist zijn
   (`TOKEN_WHITELIST_ROLE` op het STO-token), en de uitgifte moet lopen en niet vol zijn.
2. Het payment token wordt overgemaakt, of een ander token wordt via de manager geswapt.
3. r. 379–380: `usdPriceOfPaymentToken = priceAndSwapManager.getUSDPriceOfPaymentToken(paymentTokenOracle, twapInterval)`.
4. r. 382 → `_validateInputs` (r. 990–1065): de USD-waarde wordt getoetst aan `minTicket`,
   `maxTicket` en `hardCap`. Bij overschrijding van de hardCap wordt het verschil
   teruggestort (r. 389–398).
5. r. 405–415: `newAmountInSTO = actualAmount × usdPrice / 10^dec × 10^stoDec / priceInUSD`.
6. r. 420: `investor.amountInSTO += newAmountInSTO`. Dit bepaalt hoeveel STO-tokens de
   investeerder later kan claimen.

De prijs wordt ook gebruikt in:
- `_offchainReporting` (r. 1251), alleen voor `ESCROW_OFFCHAIN_REPORTER_ROLE`;
- de berekening van de opnamefee voor de uitgever (r. 1319–1325), waar gedeeld wordt
  door de prijs.

## 4. Wie kan het raken

- **Prijsafhankelijke functie:** `buyToken` kan worden aangeroepen door elke
  **gewhitelist investeerder** (een gewone gebruiker, geen admin).
- **Voorwaarde voor het hele risico:** het Chainlink-pad staat alleen aan als een
  **admin** (`DEFAULT_ADMIN_ROLE`) een oracle instelt. Op de peildatum heeft geen enkele
  escrow dat gedaan.

## 5. Wat kan misgaan *als* er een oracle is ingesteld

Dit zijn alleen gevolgen. Er is niets uitgevoerd of getest.

- **Bevroren of uitgefaseerde feed** (de feed stopt met updaten of wordt door Chainlink
  uitgefaseerd):
  - De laatste, verouderde prijs wordt zonder foutmelding gebruikt, en de TWAP verandert
    dat niet (zie r. 309/319).
  - Investeerders krijgen STO-tokens tegen een verkeerde koers: te veel als de echte
    koers inmiddels lager ligt (verwatering van andere investeerders en de uitgever), te
    weinig als hij hoger ligt.
  - De opnamefee (r. 1323) wordt ook op een verkeerde koers berekend.
- **Prijs = 0** (storing of onjuiste feed):
  - In de meeste gevallen reverteert `buyToken`: de USD-waarde wordt 0, wat kleiner is
    dan `minTicket` (r. 1010–1011). Voor bestaande investeerders volgt een deling door
    nul (r. 1031).
  - De fee-berekening voor de uitgever (r. 1323) reverteert ook. Dat is tijdelijke
    onbeschikbaarheid, geen verlies.
  - Randgeval: als het resterende plafond kleiner is dan `minTicket`, kan een *nieuwe*
    investeerder betalen en `newAmountInSTO = 0` toegekend krijgen. Er wordt dan betaald
    zonder STO-toekenning.

## 6. Impactclassificatie

**Laag / informational (theoretisch) voor de huidige deployment.**

- Op Ethereum staat het kwetsbare codepad in geen van de 52 escrows aan.
- Het kan alleen aangaan via een admin-handeling (`setPaymentToken` met een
  oracle-adres).
- Als het aangaat, is het een correctheidsrisico afhankelijk van feedstoringen: een
  verkeerde toekenning bij een bevroren feed, of onbeschikbaarheid of een
  nul-toekenning bij prijs 0. Het is geen manier om zonder rechten geld van anderen weg
  te halen.
- Met een ingesteld oracle zouden wij het medium noemen. Daarom raden we de fix aan
  vóórdat er ooit een oracle wordt geconfigureerd.

## 7. Voorgestelde fix

In `getUSDPriceOfPaymentToken`, direct na `latestRoundData()`:

```solidity
(uint80 roundId, int256 price, , uint256 updatedAt, ) = paymentTokenOracle.latestRoundData();
if (price <= 0) revert Errors.NotNegativeValue(price);                 // 0 ook weigeren
if (updatedAt == 0 || block.timestamp - updatedAt > maxOracleAge)       // versheid
    revert Errors.StalePrice(updatedAt);                                 // (nieuwe error)
```

Aanvullend:
- In `_getChainlinkTWAP`: sla rondes met `answer <= 0` over in plaats van ze mee te
  middelen.
- Controleer na het middelen opnieuw `finalPrice > 0` (r. 169: `<= 0` in plaats van
  `< 0`).
- Maak `maxOracleAge` per oracle configureerbaar, gelijk aan de heartbeat van die feed
  plus een marge (bijvoorbeeld heartbeat + 10%). De heartbeat verschilt per feed.

## Werkwijze en beperkingen

- De bron is de geverifieerde source op Etherscan. Er is geen code uitgevoerd tegen
  mainnet behalve read-only `eth_call` / `eth_getCode`.
- Escrow-implementatie: beacon `0xe2f8f2910d923e660a4a526f7c08ef3ddd7a713d` →
  `0x4459432f1626cc4de0e0a004e74ff282ae9c4a6f` (`STOEscrowManagedUpgradeable`, 0.8.26).
- Alleen de genoemde adressen en ketens zijn onderzocht. Eventuele andere
  Brickken-deployments vallen erbuiten.
