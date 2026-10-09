# Fuzz-harnas uitbreidingsmodules — status

Scope-afspraak voor deze uitbreiding (binnen CLAUDE.md hard rules):
- alles draait op een **lokale fork**; nooit transacties op mainnet;
- elke module is **detect-only**: een gebroken invariant → melding "ontbrekende bescherming + fix",
  nooit een kant-en-klaar aanvalsscript;
- elke module heeft een **verplichte positive control** (bewijs dat de invariant/afgaat bij kapotte staat);
- historische-hack-validatie = **fork op het blok vóór het incident en aantonen dat de invariant/detector
  afgaat op de pre-patch code**. Dat is een regressietest die bewijst dat de scanner de klasse vindt — het is
  geen replay van de drain.

## Modules

| # | module | type | gebouwd | positive control | historische-hack-validatie |
|---|---|---|---|---|---|
| 1 | **ATTACKER-PROFIT** | invariant (alle templates) | ✅ | ✅ `tests/evm/test_attacker_profit.py` (4/4) | ✅ **echte fork** Meta Pool mpETH (blok 22722910, DeFiHackLabs) — invariant gaat af op pre-patch state; + reconstructie-benchmark (TSURU-free-mint) |
| 2 | Flash-loan-weerbaarheid | handler-actie (lenen→acties→terugbetalen, voedt invarianten; géén prijsmanipulatie-stap) | — | — | — |
| 3 | **Oracle-guard (forced value)** | mock een Chainlink-antwoord (stale/0/afwijkend) → check dat de consumer het weigert | ✅ | ✅ `tests/evm/test_oracle_guard.py` (3/3) | ✅ **live** Opyn ChainLinkPricer op fork: accepteert stale feed (mist updatedAt-check), weigert 0 — bevestigt de statische `EVM-ORACLE-FRESH` |
| 4 | **Tijd** | handler-actie `warpTime` (`vm.warp`/`vm.roll`), gefuzzd onder `--warp`; waarde-conservatie-invarianten uit, SOLVENCY/ACCESS/rol aan | ✅ | ✅ `tests/evm/test_time.py` (2/2) | ✅ bereikbaarheid op echte code (Lista, `--warp`): `warpTime` gefuzzd, SOLVENCY houdt onder opgebouwde rente |
| — | Prijsmanipulatie-drain (flash-loan + live-pool-swap + cross-protocol, getuned op historische drains) | **NIET gebouwd** | n.v.t. | n.v.t. | gedekt aan de detectiekant door `EVM-ORACLE-SPOT` + module 3 |

## Module 1 — ATTACKER-PROFIT (af)

Eén gedeelde invariant (`ATTACKER_PROFIT` in `templates.py`), in elke template opgenomen en in
`DEFAULT_INVARIANTS`. Voor elke onbevoegde test-actor, na elke call:
- **(a) waarde**: `valueOut ≤ valueIn` (+ afrondingstolerantie). De actoren zijn roldloze `makeAddr`-adressen.
- **(b) allowance**: de target heeft de actor nooit een allowance over de **eigen** fondsen van de target gegeven.
- **(c) rol**: de actor is nooit `owner()` of `DEFAULT_ADMIN_ROLE` geworden.

Template-agnostisch: gebruikt alleen `h.TARGET()`, `h.actors()`, `h.valueIn/valueOut/opsOf` en de
template-eigen `tokens()`. Detect-only: een break wordt een "ontbrekende access/accounting-bescherming + fix".

Positive control (`tests/evm/attacker/AttackerProfitCases.sol`, zelf-nagebouwd minimaal voorbeeld):
- `VulnApprove.pullPermission()` → onbevoegde actor krijgt allowance over de vault-fondsen → check (b) gaat af;
- `VulnRole.claimAdmin()` → onbevoegde actor krijgt DEFAULT_ADMIN_ROLE → check (c) gaat af;
- `VulnFreeValue.freebie()` → onbevoegde actor krijgt gratis tokens → check (a) gaat af;
- `SafeVault` (owner-gated) → geen enkele check gaat af.
Resultaat: 4/4. Sanity op een echt, schoon target (Lista Moolah) met de invariant meegedraaid: zie
`fuzz-work/_batch/lista-ap.log`.

### Welke hack valideert welke module (mapping)

| hack-klasse | voorbeeldincidenten | module die hem terugvindt |
|---|---|---|
| Ontbrekende access control / rol-escalatie / gratis mint door onbevoegde call | unprotected `initialize`/mint, publieke privilege-functie | **1 ATTACKER-PROFIT** + statische `unprotected-sibling` / `missing-access-control` |
| Flash-loan die interne boekhouding breekt (zonder prijsmanipulatie) | pool-accounting die niet tegen tijdelijk groot kapitaal kan | **2** (feeding SOLVENCY/ATTACKER-PROFIT) |
| Onbeschermde/stale oracle die een consumer accepteert | een lener/CDP die `latestAnswer` zonder versheids-/bound-check gebruikt | **3** (forced value) + statische `EVM-ORACLE-FRESH`/`-SPOT` |
| Rente/liquidatie/bad-debt/vesting over tijd | posities die pas na tijdsverloop ongezond worden | **4** (tijd) |

(Module 1 benchmark: zie onder — gedaan als reconstructie.)


## Module 3 — ORACLE-GUARD (af)

Detect-only. Een misdragende/gecompromitteerde Chainlink-feed wordt met `vm.mockCall` geforceerd op
stale / 0 / afwijkend (géén swap, géén trade — een geforceerde waarde, wat een kapotte feed zou teruggeven).
Een consumer mét bescherming moet daarop reverten; één zonder bescherming rekent door met de slechte prijs.

- **Positive control** (`tests/evm/oracle_guard/OracleGuardCases.sol`, zelf nagebouwd): `GuardedConsumer`
  revert op stale én 0; `UnguardedConsumer` consumeert beide → 3/3.
- **Benchmark (live, op fork):** Opyn `ChainLinkPricer` `0x908Fa5…918C`, aggregator ETH/USD `0x5f4eC3…8419`.
  Op een fork geforceerd:
  - vers → `getPrice()` = 249.231.315.371 (±$2492) ✓
  - **stale** (updatedAt ver in het verleden) → `getPrice()` **accepteert** en geeft de stale waarde terug
    (geen `updatedAt`-controle) → **bevinding**
  - 0 → `getPrice()` revert (de pricer checkt wél `answer > 0`)

  Dit bevestigt dynamisch de eerdere statische `EVM-ORACLE-FRESH`-melding op dit contract: `answer>0` wel,
  versheid niet. Harnas: `fuzz-work/oracle-guard-bench/`. Rapport zou luiden: "voeg een
  `block.timestamp - updatedAt <= maxAge`-controle toe", geen aanvalsscript.

## Module 1 — benchmark (af: echte fork + reconstructie)

### Echte-fork detectie-benchmark (Meta Pool mpETH)

`fuzz-work/attacker-profit-bench/test/Bench.t.sol`. Fork op **blok 22722910** (= het blok vóór het
Meta-Pool-incident, 2025-06-17, ~$27M; incident/adres/blok uit SunWeb3Sec/DeFiHackLabs
`src/test/2025-06/MetaPool_exp.sol`). Target mpETH `0x48AFbBd342F64EF8a9Ab1C143719b63C2AD81710`.

Een **onbevoegde** actor doet een gewone `depositETH{value:107 ether}` → `got` shares, en roept daarna
`mint(got, actor)` aan **zonder extra asset te sturen of een approval te geven**. Een correcte ERC4626-`mint`
moet `convertToAssets(got)` aan assets van de caller pullen; hier gebeurt dat niet → de actor krijgt ~2× de
shares voor dezelfde inleg. De ATTACKER-PROFIT-waarde-eigenschap (shares-winst zonder bijbehorende
asset-uitstroom) **gaat af op de echte pre-patch bytecode**. Detectie-only: géén exploit-tx, alleen de
constatering "deze call vergroot het aandeel van een onbevoegde actor zonder waarde-in".

### Reconstructie-benchmark (free-mint-klasse)

Daarnaast op een **getrouwe reconstructie** van de free-mint-klasse (TSURU-stijl, 2024):
`tests/evm/attacker/FreeMintIncident.sol` + `fuzz-work/_m1bench/test/Bench.t.sol` — onbevoegde actor roept
de ongegate `onDepositReceived(self, 1e24)` aan, houdt 1.000.000 tokens tegen 0 inleg → waarde-check gaat af.

### Statische free-mint-detector: gebouwd, getest op de 62-set, en **weer verwijderd**

Een smalle statische detector (ongegate, niet-payable externe functie die supply/saldo crediteert zonder
`transferFrom`/`burn`/`msg.value` aan een caller-bepaalde ontvanger) is gebouwd en op de bestaande
62-protocollen-set gedraaid. Uitkomst: **15/61 protocollen vuurden** (meerdere findings elk) — vrijwel
allemaal **vals-positief**. Hij markeerde o.a. de standaard `AToken.transfer(address,uint256)` van Aave als
"mogelijk free-mint", omdat hij de **debet aan de caller-kant** bij interne-boekhouding-transfers niet ziet
(alleen `transferFrom`/`burn`-achtige namen tellen als waarde-in, niet een `balances[msg.sender] -= amount`).
Bij ~25% vals-positief op betrouwbare, gedeployde protocollen is de detector **verwijderd**
(`slither_worker.py`/`slither_runner.py`/`triage.py` teruggedraaid; `unprotected-sibling` blijft intact).
De free-mint-klasse blijft gedekt door de **dynamische** ATTACKER-PROFIT-invariant, die per-actor
`valueIn`/`valueOut` volgt en daarom níét misvuurt op een gewone transfer (de debet van de actor valt weg
tegen zijn credit).

- De "drain-andermans-approvals"-klasse (Seneca/Socket, 2024) past wél bij de statische
  `unprotected-sibling`-detector (ongegate call naar caller-adres), niet bij ATTACKER-PROFIT.

## Module 4 — TIJD (af)

Detect-only. Nieuwe handler-actie `warpTime(seed)` in `HandlerBase` (`vm.warp` + `vm.roll`, tot 90 dagen per
stap), toegevoegd aan de warp-actielijst van elke template en als gefuzzde selector opgenomen wanneer
`--warp` aanstaat (`sel[6] = HandlerBase.warpTime.selector`). Zo worden rente, liquidaties, bad debt,
vesting en claim-delays bereikbaar.

Onder `--warp` laat yield/rente `valueOut` legitiem boven `valueIn` uitkomen, dus de generator **laat de
waarde-conservatie-invarianten vallen** (`no-free-withdraw`, `conservation`, `k-monotonic`) en gebruikt een
**warp-variant van ATTACKER-PROFIT** die alleen de allowance- en rol-checks houdt (tijd kent een onbevoegde
actor nooit een allowance of rol toe). SOLVENCY en ACCESS blijven volledig aan.

- **Positive control** (`tests/evm/time/TimeCases.sol`, `tests/evm/test_time.py`, 2/2): `BuggyVesting` met
  ongecapte `claimable() = (block.timestamp - start) * rate` laat ná een warp van 365 dagen méér vrij dan er
  gestort is → breekt; `SafeVesting` (gecapt op het depot) blijft heel. De bug is **alleen na tijdsverloop**
  bereikbaar — dat is precies wat de warp-actie toevoegt.
- **Bereikbaarheids-benchmark op echte code** (Lista Moolah, blok 26154714, `fuzz-work/lista-warp-m4/`,
  `--warp`, 48 runs × 40 depth): de `--warp`-harnas compileert met de `HandlerBase.warpTime`-selector;
  invarianten = `solvency, access, attacker-profit-warp` (de waarde-conservatie-invarianten zijn er onder
  `--warp` correct uit). `warpTime` is **203/203 keer geslaagd** als gefuzzde actie, en alle drie de
  invarianten hielden over **1920 calls** (positive control `test_control_solvency` vuurde). Dit toont dat de
  tijd-actie op echte lender-code draait zonder de solvency-eigenschap vals te breken. (`supply` revert op dit
  blok vaak met "invalid resilient oracle price" — forkverschijnsel, geen bug; correct geteld, niet gemeld.)
