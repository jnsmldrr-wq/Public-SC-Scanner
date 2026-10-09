# Triage: Byreal CLMM

- Repo: https://github.com/byreal-git/byreal-clmm.
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC (`getAccountInfo`, `getProgramAccounts`, `getTokenAccountBalance`). Geen exploit, geen transactie.
- **Privilege-filter (CLAUDE.md) toegepast:** alleen bevindingen die een externe aanvaller of gewone gebruiker kan benutten, zijn uitgewerkt.

## Uitkomst

**Eén GOUD-kandidaat met beperkt geldrisico (B-1).** Verder niks GOUD.

- Een tweede, ernstiger kandidaat (een router-bypass van de dynamische fee) bleek **niet bereikbaar**: die instructie is uitgeschakeld en staat niet in de live bytecode.
- De kern-wiskunde is identiek aan Raydium.

## 1. Livecheck, sourcecheck en versie

| ID | Mainnet | Bron |
|---|---|---|
| `REALQqNEomY6cQGZJUGwywTBD2UmDT32rZcNnfxQ5N2` (mainnet-build, zonder features) | **LIVE**, upgrade authority `EmEa9b4yGffixdeFQ9zoyB3V5D9PZAbcE79mfwXb3bhs`, deploy-slot 438767271 (**2026-08-12 07:16 UTC**) | **VOLLEDIGE BRON**: 68 bronpaden in de bytecode, 53 in de repo, 0 eigen ontbrekend |
| `45iBNkaENereLKMjLm2LHkF3hpDapf6mnvrM5HWFg9cY` (localnet/devnet-build) | ook live, upgrade authority `9ZG4mY…` (volgens de code-commentaar de devnet-multisig), deploy 2026-08-11 | niet gescand |

Verified build (OtterSec): nee.

**Gescande versie: `6863b33`** ("feat: support swap dynamic fee", 2026-04-29). Dat is HEAD en de laatste commit vóór de deploy van 2026-08-12. In de repo staat geen nieuwere code; de bytecode-paden komen volledig overeen.

## 2. Fork-analyse: Byreal tegenover Raydium CLMM

**Basis:** Raydium CLMM **`eb7c392`** (2025-05-14, "Upgrade anchor to version 0.31"). Ik heb alle Raydium-commits van jun 2024 – jun 2025 vergeleken met Byreals eerste commit `cf1f0fd`; deze had de kleinste diff (360 regels).

**Afwijking deploy ↔ basis:** +7.901 / −2.919 regels in 67 bestanden. De volledige diff staat in `shortlist/s500/byreal_vs_raydium_eb7c392.diff`.

| Gebied | Bestanden (belangrijkste) | Wie kan het aanroepen |
|---|---|---|
| **Kern-wiskunde** | `swap_math`, `liquidity_math`, `sqrt_price_math`, `tick_math`, `full_math`, `big_num`, `fixed_point_64`, `unsafe_math` | **IDENTIEK aan Raydium** (witruimte-ongevoelig vergeleken); alleen rustfmt |
| **Dynamische fee + Pyth-oracle** | `libraries/dynamic_fee_math.rs` (+497), `util/pyth.rs` (+206), `instructions/swap_v3_dyn.rs` (+68), `states/pool.rs` (+815/−308) | **gewone swapper** → B-1 |
| **Dynamische tick-arrays** | `states/dyn_tick_array.rs` (+1.480), `states/tick_array_container.rs` (+744), `states/tick_state_utils.rs` (+282), wijzigingen in `swap.rs`, `open_position.rs`, `increase/decrease_liquidity*.rs` | gewone LP/swapper → structureel nagelopen, zie §4 |
| **Decay-fee-pools** | `instructions/create_pool_decay_fee.rs` (+291) | pool-maker (permissionless) |
| **Admin-group, off-chain rewards, fee-instellingen** | `admin/*` (init/update_amm_admin_group, deposit/claim/withdraw_offchain_reward, set_pool_trade_fee_rate, set_swap_dynamic_fee_params, set_pool_quote_flag) | **admin / pool_manager** → LAAG, niet uitgewerkt |
| Verwijderd t.o.v. Raydium | limit orders, permissioned/customizable pools, permission-PDA | n.v.t. |

## 3. Scan

`scan.py programs/amm` gaf 52 High, 102 Medium, 538 Low (`byreal-report.md`).

**Fout-positieven:**
- **SOL-CFG-201:** de workspace-`Cargo.toml:11` zet `overflow-checks = true`.
- **SOL-ORACLE-301 in `swap.rs` (regels 1.237–3.088):** dat is testcode (`#[cfg(test)]`), geen oracle.
- **Casts en arithmetic in tests en padding-initialisatie:** geen productiecode.
- **SOL-TYPE-003 (`bytemuck::from_bytes`):** het zijn Raydium-patronen, voorafgegaan door eigenaar- en discriminatorchecks.
- **SOL-OWNER-002 op tick-arrays en `protocol_position`:** die worden in de handler via `TickArrayContainer::try_from` (eigenaar + discriminator) en `get_pool_id() == pool` gecontroleerd, zie §4.

Wat overblijft is hieronder met de hand beoordeeld.

## 4. De punten waar je specifiek naar vroeg (alleen wat een gewone gebruiker kan raken)

- **Swap-rekenwerk, afronding en precisie:** de kern-wiskunde is identiek aan Raydium, dus geen nieuwe afrondingsbugs. Dynamische fees worden als `total_fee_rate` aan de ongewijzigde swap-wiskunde gegeven.
- **Tick- en liquidity-boekhouding (dynamische tick-arrays):**
  - Laden gebeurt altijd via eigenaar (`crate::id()`) plus discriminator (`TickArrayState` of `DynTickArrayState`).
  - Bij aanmaak wordt de PDA `[TICK_ARRAY_SEED, pool, start_index]` afgedwongen (`tick_array_container.rs:350-359`).
  - Bij gebruik wordt `get_pool_id() == pool_state` gecontroleerd in swap (`swap.rs:192`, `:256`, `:744`), increase (`:151-152`), decrease (`:159-160`, `:390-391`) en open_position (`:470-471`).
  - `try_from_without_check` wordt alleen in `swap.rs:743` gebruikt, direct gevolgd door de `pool_id`-check.
  - **Geen vervalsing of hergebruik over pools gevonden.** De interne tickboekhouding van `dyn_tick_array.rs` (1.480 regels) heb ik structureel, niet regel voor regel, nagelopen.
- **Fee-berekening:**
  - De arbitrage-, trade-slippage- en imbalance-fee gebruiken checked math en `mul_div_ceil` (afronding in het voordeel van de LP).
  - Alle publieke swap-instructies dwingen de dynamische fee af: `swap` (`:737`) en `swap_v2` (`:379`) weigeren dynamische pools, en `swap_v3_dyn` rekent hem.
- **SOL-ORACLE-301:** zie **B-1**.
- **SOL-CPI-302:** de reads van `vault.amount` vóór de transfer (`swap.rs:669`, `swap_v2.rs:263`) zijn ongewijzigde Raydium-logica en lezen vóór de CPI. In orde.
- **Pool- of positie-accounts vervalsen:**
  - Een positie is gekoppeld aan het NFT-account (`mint == personal_position.nft_mint`, `amount == 1`), plus `personal_position.pool_id == pool_state`.
  - Vaults moeten gelijk zijn aan `pool_state.token_vault_0/1`.
  - Geen probleem gevonden.

## 5. Kandidaten

### B-1 — GOUD (elke swapper), MEDIUM/LAAG geldrisico: de swapper kiest de oracle-prijs uit een venster van 1 uur, zonder verificatie- of confidence-check. **AFWIJKING van Raydium**

Plaats:

- `programs/amm/src/util/pyth.rs:9-43` (`load_pyth_price`);
- `programs/amm/src/states/pool.rs:436` (`MAX_PYTH_AGE_SECONDS: u64 = 3600`) en `:452-461`;
- `programs/amm/src/instructions/swap_v3_dyn.rs:20-24`.

**Wat er misgaat:**

- `swap_v3_dyn` neemt de twee Pyth-`PriceUpdateV2`-accounts uit de **door de swapper aangeleverde** `remaining_accounts`.
- `load_pyth_price` controleert:
  - de eigenaar (Pyth-receiver);
  - de feed-ID (vastgelegd in de pool door de `pool_manager`);
  - prijs > 0;
  - `publish_time ≥ nu − 3600 s`.
- De controle op **verificatieniveau is bewust uitgecommentarieerd** (`pyth.rs:22-27`).
- Er is **geen confidence-check**, en een maximale leeftijd van **een uur**.

**Waarom dat ertoe doet:**

- De belangrijkste component van de dynamische fee is de **arbitrage-fee**: `max(0, |p_pool − p_oracle|/p_oracle − buffer − base)` (`dynamic_fee_math.rs:14-32`). Die bestaat om LP's te beschermen tegen arbitrage (LVR).
- Een arbitrageur kan elke echte, door Pyth getekende prijs uit het afgelopen uur aanleveren; prijs-updates kun je zelf naar een eigen account posten. Hij kiest dan de prijs die het dichtst bij de huidige poolprijs ligt.
- Daardoor wordt de arbitrage-fee ~0 en betaalt hij alleen de basis-fee, juist op de momenten waarop de pool het verst van de markt ligt.
- **Vervalsen** van een prijs kan níet: dat vereist handtekeningen van Wormhole-guardians. Het probleem is **kiezen** uit echte, maar tot een uur oude prijzen.
- **Niet geverifieerd:** dat een recente Pyth-receiver posten van historische updates toestaat. Dat is gebaseerd op het bekende Pyth-ontwerp; ik heb geen update gepost en geen transactie gesimuleerd.

**Wie:** elke gebruiker die swapt. Er zijn geen rechten nodig.

**Geldrisico:** LP's lopen de arbitrage-fee mis die de dynamische fee had moeten innen. Dit is waardelekkage naar arbitrageurs, geen diefstal van hoofdsom.

**Blootstelling (read-only gemeten):** van de 133 live pools hebben er **5** `swap_dynamic_fee` aan (`decay_fee_flag & 0b10000`):

| Pool | Paar | Saldo (ruw) |
|---|---|---|
| `23XoPQqG…` | USDC/USDT | 375k / 706k |
| `HrWp3QR3…` | USD1/USDC | 97k / 112k |
| `9GTj99g9…` | SOL/USDC | 203 SOL / 43,5k USDC |
| `DyzGYEhd…` | SOL/USD1 | 34 SOL / 27,9k |
| `34oUrDd3…` | USDC/USDT | klein |

Samen ~$1,4M.

- In de stablecoin-pools beweegt de prijs in een uur nauwelijks, dus de winst is verwaarloosbaar.
- Relevant is dit vooral voor de **SOL-pools (~$100–150k)** bij volatiele uren.

**Oplossingsrichting (voor een eventuele melding):**

- een korte maximale leeftijd (bijv. ≤ 30–60 s);
- `get_price_no_older_than`;
- de verificatieniveau-check terugzetten;
- een confidence-check.

### Geschrapt na verificatie: router-bypass van de dynamische fee (zou GOUD zijn geweest)

- `instructions/swap_router_base_in.rs:44-64` roept `exact_internal_v2` (alleen basis-fee) aan, **zonder** de check `is_swap_dynamic_fee_enabled()`.
- **Maar:** de router-instructie is in `lib.rs:584-589` uitgecommentarieerd en `Instruction: SwapRouterBaseIn` staat **niet** in de live bytecode.
- **Niet bereikbaar.** Het is wel een valkuil als de router ooit weer aangezet wordt: zonder die check zou elke gebruiker de dynamische fee kunnen omzeilen.

### LAAG (geprivilegieerd, niet uitgewerkt)

| Wat | Wie |
|---|---|
| Admin-group, `set_pool_trade_fee_rate`, `set_swap_dynamic_fee_params` (inclusief keuze van feed-ID's), off-chain-reward deposit/withdraw | admin / `pool_manager` |
| `create_pool_decay_fee` | pool-maker. Een hoge, aflopende start-fee raakt alleen traders die die pool zelf kiezen; zij hebben slippage-limieten |

## Conclusie

- De kern van Byreal is Raydium, en die is ongewijzigd. Alle afwijkingen die een gebruiker kan raken zijn nagelopen.
- **B-1** is de enige GOUD-bevinding. Hij is echt en zit in eigen Byreal-code, maar de geldwaarde is beperkt: alleen een gemiste dynamische fee, op ~$1,4M TVL, merkbaar vooral in de SOL-pools.
- **Melden?** Ja, als vrijblijvende, kosteloze melding met een concreet advies (maximale leeftijd, verificatieniveau, confidence).
  - Byreals `security_txt` noemt geen contact (`policy: ""`, `auditors: "byreal"`), dus het contact moet via hun site of Discord.
  - Vermeld ook de uitgeschakelde router als aandachtspunt voor de toekomst.
