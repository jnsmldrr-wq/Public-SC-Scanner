# Nieuwe fuzz-kandidaten (DefiLlama, Ethereum, $20–50k TVL)

Peildatum: 2026-10-08. Alles is read-only bepaald.

**Waar de adressen vandaan komen:**
- de DefiLlama-adapter (`api.llama.fi/protocols` → module → DefiLlama-Adapters op GitHub);
- voor Ebisu, YLD en SFI, die niet meer in `main` staan: de adapter-PR's #15470, #18430 en #18473;
- de API's en subgraphs van de projecten zelf (YLD, UFarm, TermFinance);
- voor Bitbond: de officiële Token-Tool-documentatie.

**Hoe de bron is gecontroleerd:**
- Etherscan v2, met Sourcify als tweede bron;
- proxy's gevolgd via de EIP-1967-slot, de beacon-slot of de EIP-1167-bytecode;
- template-check via `detect.classify` op de geverifieerde ABI;
- gates via de ACCESS-heuristiek, en voor de kernfuncties met de hand nagelopen.

| # | protocol | ETH-TVL | geldcontract (Ethereum) | bron / proxy | template | kernflow door gewone gebruikers? | oordeel |
|---|---|---|---|---|---|---|---|
| 1 | **TermFinance Vaults** | $26,6k | grootste vault `0xe852db931ac6f02490a32695f09ee79a31f53821` (28 vaults via subgraph) | ✓ `Strategy`-proxy → `TokenizedStrategy` `0xbb51273d…` (EIP-1967) | **✓ `vault`** (ERC-4626) | **Ja**: `deposit/mint/withdraw/redeem` open; `report/tend/shutdown/setKeeper…` gated (keeper/management) | **Direct fuzzbaar.** Yearn-V3-TokenizedStrategy-fork met Term's eigen strategie (repo-tokens/veilingen) |
| 2 | **YLD** | $22,7k | strategy-vault `0xCa960E6DF1150100586c51382f619efCCcF72706` (yscvxcrv); wrapper-vault `0x95f19B19…` | ✓ `CvxCrvCompounder` → `TokenizedStrategy` `0xd377919f…` (standaard Yearn); wrapper = standaard Yearn V3 Vault (Vyper) | **✓ `vault`** (op de strategy) | **Ja**: deposit/redeem open; `report/tend` keeper-gated | **Direct fuzzbaar** op de strategy (eigen compounder). De wrapper is standaard Yearn en valt buiten scope |
| 3 | **SIR** | $43,2k | `Vault` `0x7Dad75dD36dE234C937C105e652B6E50d68b0309` | ✓ geverifieerd, geen proxy, eigen code (audit Egis) | ✗ eigen leverage-model (APE/TEA, `mint/burn` per `vaultParams`) | **Ja**: `mint`/`burn` open; `claimSIR/withdrawFees/updateSystemState` gated | **Sterke kandidaat**, maar vraagt een nieuw `sir`-template (reserves-boekhouding APE/TEA). Redelijk te bouwen |
| 4 | **Cytonic Airdrop** | $29,9k | `BridgeDepositor` `0xaEA5Bf79F1E3F2069a99A99928927988EC642e0B` | ✓ proxy → `BridgeDepositor` `0xce84c402…` (EIP-1967; ook Sourcify) | ✗ (deposit + withdraw met unlock-periode + claim) | **Ja**: `deposit/depositETH/withdraw/claim/cancelWithdraw/purchase` open; `pause/migrate/toggleAsset/updateUnlockPeriod…` owner-gated | **Kandidaat.** Klein template nodig, verwant aan `queuevault`. Let op: `migrate` (owner) kan fondsen verplaatsen (LAAG, privileged) |
| 5 | **Stablecoin for Impact** | $20,2k | `AaveImpact` `0xd8831608954c7C4044938aC76E32dA81d692f0a6` | ✓ proxy → `AaveImpact` `0x14173250…` (EIP-1967; Sourcify exact match) | ✗ (eigen deposit-boek naar Aave, yield-split naar NGO) | **Ja**: `deposit(token, amount, ngoPercent)` en `withdraw(amount, id, token)` hebben alleen per-user-modifiers (`notBanned`, `onlyExistingToken`, `validDeposit`); NGO-afhandeling en oracle zijn gated | **Kandidaat.** Klein template nodig (deposit-boek + Aave-backing) |
| 6 | **JUSD Finance** | $23,9k | `AccountableAsyncRedeemVault` `0x2B5895b716311A1eaC8f93fB88C56aF9eC8C1A69` | ✓ geverifieerd, geen proxy | ~ `vault` herkend, maar redeem is async (ERC-7540) | **Alleen geverifieerde gebruikers**: `deposit`/`requestRedeem` met `onlyAuth` (handtekening van een signer, whitelist); `fulfillRedeemRequest/process*/lockAssets…` zijn alleen voor de strategy | Pas na een async-template plus KYC-simulatie. Het geld gaat naar off-chain kredietstrategieën, dus on-chain is weinig te toetsen |
| 7 | **UFarm Digital V2** | $23,3k | pools `0x406A69A4…a924`, `0xd1c832c2…9335` (beacon-proxies) | ✓ beacon `0xd1159972…` → `UFarmVault` `0x537d75f9…` (ook Sourcify) | ✗ ERC-7540 async plus modules | **Deels**: `requestDeposit` met `ClientVerification` (credential); settlement via oracle-NAV (Chainlink/CCIP); admin-functies via aparte modules | Niet nu. Async plus oracle-settlement plus modulaire gates: veel werk, en de kernflow hangt van off-chain NAV af |
| 8 | **Seer** | $30,5k | `MarketFactory` `0x1F728c2fD6a3008935c1446a965a313E657b7904`; geld zit in Gnosis **ConditionalTokens** `0xC59b0e4D…` + Wrapped1155Factory (sDAI) | ✓ factory geverifieerd | ✗ (CTF split/merge) | **Ja** (markten aanmaken, split/merge), maar de bewaring is Gnosis-code | Laag. De custody is externe Gnosis-CTF-code (al gescand in batch 4); Seer zelf doet marktbeheer en resolutie |
| 9 | **Ebisu V2** | $25,2k | `BorrowerOperations` (weETH) `0x97CA1883908b45A002D25845F5Ba486Fb8F5CD2c`; `StabilityPool` (weETH) `0x4f14903b…5cf4` | ✗ **BorrowerOperations-impl `0x28fb5fd2…` niet geverifieerd** (Etherscan én Sourcify 404); StabilityPool ✓ (Liquity-V2-code, "Bold") | ✗ (CDP/troves) | StabilityPool: ja (`provideToSP/withdrawFromSP`). Troves: onbekend, want de bron ontbreekt | **Niet fuzzen.** De trove-kern is niet geverifieerd, vergelijkbaar met het LIVE=PRIVAAT-geval op Solana. Alleen de StabilityPool zou kunnen |
| 10 | **Bitbond Lockers** | $34,4k | Token-Tool-factory `0x4904Ba3148147D2f78b05a8446C01c48a7ABa4bd`; lockers zijn losse contracten per maker | ✗ **factory niet geverifieerd** (Etherscan én Sourcify) | ✗ | **Nee**: een locker wordt alleen door de eigen eigenaar of begunstigde vrijgegeven | **Niet geschikt**: geen bron, en de kernflow hoort bij de eigenaar |

## Rangschikking voor fuzzen

1. **TermFinance Vaults**: het `vault`-template werkt direct, en de eigen strategie houdt echt geld.
2. **YLD** (strategy-vault): `vault`-template, eigen compounder.
3. **SIR**: volledig eigen code en de kernflow is open, maar er is een nieuw `sir`-template nodig.
4. **Cytonic**: klein template nodig (deposit + unlock-withdraw).
5. **Stablecoin for Impact**: klein template nodig (deposit-boek + Aave).
6. JUSD / UFarm: alleen na een async-7540-template met credential-simulatie.
7. Seer: custody is Gnosis-code. Ebisu V2 en Bitbond: geen (volledige) geverifieerde bron.

## Bijvangst: drie zwakke plekken in de ACCESS-heuristiek, waarvan twee gerepareerd

- **Opgelost:** een `only*`-modifier die de caller niet controleert (`onlyExistingToken`,
  `notBanned`-achtig) telde als gate. Nu telt een modifier alleen als gate als hij een
  bekende auth-modifier is, of als zijn body de caller tegen een autoriteit toetst. Dit
  speelde bij SFI's `deposit`/`withdraw`. Regressietest toegevoegd: 15/15.
- **Opgelost:** een gated override achter een ongegate virtuele basis werd gemist. Nu
  geldt: gated als alle definities gated zijn, óf als de override gated is. Dit speelde
  bij JUSD's `setAllowed` (`onlyStrategy` op de override). Die valt overigens buiten
  ACCESS-fuzzing, omdat de functie arrays als parameter heeft.
- **Bekende beperking:** bij modulaire contracten (UFarm's
  `_delegateToVaultModule`) zitten de checks in aparte module-contracten. De heuristiek
  ziet ze niet. Zo'n contract moet je per module beoordelen.
