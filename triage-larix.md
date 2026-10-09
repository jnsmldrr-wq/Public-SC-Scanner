# Triage: Larix (lending)

- Repo: https://github.com/ProjectLarix/larix-lending (HEAD `229c423`, 2022-06-23).
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC. Geen exploit, geen transactie.

## Kernconclusie

**De publieke repo is níet de broncode van het live programma.** Een scan of triage van het lending-gedrag is daarom niet mogelijk. Status: **CLOSED SOURCE (alleen een publieke SDK/interface)**.

## 1. Repo en livecheck

| | |
|---|---|
| Officiële org | `ProjectLarix` (via de DeFiLlama-listing en website). `declare_id!("7Zb1bGi32pfsrBkzWdqd4dFhUXwp5Nybr1zuaEwN34hy")` in `src/lib.rs` |
| Mainnet | **LIVE**, BPFLoaderUpgradeable, upgrade authority `GwqwyQqJ5kr3X7iUDQKgJ1FJYjxmCieiY5PikmMbsL1Q`, deploy-slot 127725622 (**2022-04-01**) |
| Verified build | nee |
| Commit bij de deploydatum | `9114bf0` (2022-03-05). Verschil met HEAD: alleen een stub-`entrypoint.rs` verwijderd (24 regels) |

## 2. Waarom de repo niet het programma is

1. **Geen processor:** `src/processor.rs` en `src/processors/` hebben nooit in de repo gestaan (hele git-geschiedenis doorzocht).
2. **Leeg entrypoint:** het verwijderde `src/entrypoint.rs` had de aanroep naar de processor uitgecommentarieerd en gaf alleen `Ok(())` terug. Deze repo bouwt dus een programma dat niets doet.
3. **Wat de publieke code wel bevat:**
   - datalayouts (pack/unpack van `Reserve`, `Obligation`, `LendingMarket`);
   - instructie-builders (`instruction.rs`);
   - `Decimal`/`Rate`-rekenhulpen;
   - een Pyth-struct-loader;
   - foutcodes.

   Er staat geen enkele functie in voor lenen, aflossen, liquideren, rente-opbouw of health-factor.
4. **Bewijs uit de bytecode** (on-chain ELF, 652.529 bytes, sha256 `5dc1c1dd…`):
   - **Bronpaden die niet in de repo staan:** `src/processor.rs`, `src/processors/deposit_reserve_liquidity.rs`, `refresh_obligation.rs`, `redeem_reserve_collateral.rs`, `refresh_mining.rs`, `src/config/config_process.rs`, `src/util/check_util.rs`, `src/state/mining.rs` en `src/state/larix_oracle.rs`.
   - **Een lokaal pad:** `/Users/shane2shen/Documents/larix-lending-deploy-20211229/larix-lock-pool/…`.
   - **Gedeelde laag:** alle 71 foutteksten uit de publieke `error.rs` staan in de bytecode. De publieke repo is dus een deel van de echte code (de error/state/math-laag), maar zonder de logica.
   - **Prijzen:** de bytecode laat zien dat Larix een **eigen "larix oracle"-programma** en "bridge pools" gebruikt ("Larix oracle program does not match…", "Bridge is stale", "Lp price account is stale and must be refreshed in the current slot"). Prijzen komen dus niet rechtstreeks uit Pyth, maar via een eigen, niet-publiek oracle-programma.

## 3. Scan (alleen de publieke subset)

`scan.py` op de repo (`9114bf0` ≡ HEAD, op de verwijderde stub na) gaf 5 meldingen (`larix-report.md`):

| Melding | Oordeel |
|---|---|
| SOL-CFG-201 `Cargo.toml` | Er staat geen `overflow-checks` in de publieke `Cargo.toml`. Of de echte build dat ook mist, is onbekend, want die build komt uit een privé-workspace. **Niet vast te stellen.** |
| SOL-TYPE-003 `util/pyth.rs:125` | Een generieke `bytemuck`-loader voor Pyth-structs. Of de aanroeper `magic`/`ver`/`atype` controleert, zit in de privé-processor. De bytecode bevat wel "Pyth product account provided is not a valid Pyth account" en "…different version than expected", wat erop wijst dat die checks bestaan. **Niet vast te stellen.** |

De nieuwe semantische detectors gaven geen meldingen. Dat komt doordat de code waar ze naar zoeken (prijs-lezingen in handlers, CPI's, fee-berekeningen) niet publiek is, niet doordat de code veilig is.

## 4. De punten waar je specifiek naar vroeg

| Punt | Te beoordelen? | Waarom niet |
|---|---|---|
| SOL-ORACLE-301 (staleness en confidence) | **Nee** | De prijs komt uit het privé-programma `larix_oracle` en de handlers zijn privé. De bytecode bevat wel slot-staleness-teksten ("…stale and must be refreshed in the current slot"). Of er ook een confidence-check is, valt niet te zien. |
| Rente, schuld en collateral | **Nee** | `accrue_interest`, borrow/repay/liquidate-berekeningen en health-factor staan niet in de repo. Wel publiek: `math/decimal.rs` en `rate.rs` (checked `try_add`/`try_mul`/`try_div`, `try_floor_u64`/`try_ceil_u64`), maar niet waar en hoe die gebruikt worden. |
| Wie mag liquideren, tegen welke prijs | **Nee** | Alleen de constanten zijn zichtbaar (`LIQUIDATION_CLOSE_FACTOR = 50`, `LIQUIDATION_CLOSE_AMOUNT = 2`) en de teksten "Obligation is healthy and cannot be liquidated" en "Liquidation is now paused". De logica zelf is privé. |
| SOL-CPI-302 (reload na transfer) | **Nee** | Er is geen publieke code die CPI's doet. |
| SOL-ROUND-303 (afrondingsrichting) | **Nee** | `calculate_borrow`, fees en liquidatie-bedragen zijn privé. |

## 5. "~3.400 regels post-audit": correctie

In `shortlist-bulk.md` noemde ik ~3.400 regels die ná de audit gewijzigd zouden zijn. **Dat was een verkeerde lezing.**

- Die regels zijn het later toegevoegen van de SDK-bestanden (`state/`, `math/`, `util/`) aan de **publieke** repo (jan–feb 2022, "Add some code for lending-client").
- De enige audit-verwijzing is commit `019f0f6` "The instruction affter round 1 audit" (2021-08). Auditor en rapport worden niet genoemd.
- Over wijzigingen in het échte programma na een audit is niets te zeggen, want die code is niet publiek.

## 6. Echte kandidaten

**Niks gevonden, en niks te vinden met publieke code.** De lending-logica, het afhandelen van prijzen en de liquidaties staan niet in een publieke repo.

Advies:

- **Larix afvoeren** als scankandidaat. Status: CLOSED SOURCE (publieke SDK). Dit is aangepast in `shortlist-bulk.md`.
- **Geen contact opnemen.** Er is geen bevinding, en volgens CLAUDE.md analyseren we alleen publiek beschikbare broncode.
- **Les voor de pijplijn:** een `declare_id!` in `src/lib.rs` bewijst niet dat de repo het programma ís. Een extra snelle check is: bevat de repo een entrypoint met een processor, en staan de bronpaden uit de bytecode (`src/…rs`-strings) in de repo? Dat had Larix in stap 2 al tegengehouden.
