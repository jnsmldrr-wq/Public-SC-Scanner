# Shortlist-500k: Solana-protocollen $500K–$20M (nieuwe stukken van de range)

Datum: 2026-10-04.

Pijplijn: DeFiLlama → repo → eigen programma (`declare_id!` + config/README/build.rs) → `livecheck.py` → `sourcecheck.py` → audit-diepte. Alleen lezen en read-only RPC; er zijn geen scans of triage gedaan.

**Bron:**
- DeFiLlama `api.llama.fi/protocols`, Solana-TVL $500K–$20M.
- De 72 protocollen uit de eerdere range $1M–$10M zijn overgeslagen.
- Over: **49 nieuwe listings**, 21 in $10M–$20M en 28 in $500K–$1M.
- Loyal Earn is op verzoek overgeslagen.

Ruwe data: `shortlist/s500/` (`todo.json`, `livecheck.txt`, `audits.json`, `repos/`).

## ✅ SCANBAAR (VOLLEDIGE BRON + live), gesorteerd op prioriteit

| # | Protocol | Status | Repo | Program ID | Solana-TVL | Audits | Verified | Code ná laatste audit? | Prioriteit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Byreal** (CLMM) | ✅ SCANBAAR | github.com/byreal-git/byreal-clmm | `REALQqNEomY6cQGZJUGwywTBD2UmDT32rZcNnfxQ5N2` (mainnet-build; ook `45iBNk…` live) | **$13,3M** | **GEEN gevonden** (geen PDF, branches of audit-commits; README zegt alleen "the implement of CLMM"). Gebruikt Raydium-crates, vermoedelijk een Raydium-CLMM-afgeleide; de Raydium-audits dekken deze code niet aantoonbaar | nee | n.v.t. (geen audit). Deploy 2026-08-12 = HEAD | **HOOG** |
| 2 | **Manifest Trade** | ✅ SCANBAAR | github.com/Bonasa-Tech/manifest | `MNFSTqtC93rEfYHB6hF82sKdZpUDFWkViLByLd1k1Ms` (+ `wMNFST…` wrapper, `UMnFSt…` ui-wrapper, alle live) | **$19,6M** | **LICHT**: Certora (audit + formal verification, 2024-11, branch `certora-audit`). Latere "audits" zijn AI-reviews (`codex-security-*.md`, 2026-07/08) en tellen niet als audit | **ja** (`f6eb1305`) | **JA, fors.** ~10.900/2.150 regels in `programs/manifest/src` tussen Certora (`e6d46bf1`, 2024-11-26) en de deploy (`a879785e`, 2026-09-16). HEAD heeft 6 commits die niet gedeployd zijn | **HOOG** |
| 3 | **Serum** (v3 DEX) | ✅ SCANBAAR (native; ID uit README) | github.com/project-serum/serum-dex | `9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin` | **$17,2M** | **GEEN gevonden in de repo**; de README zegt letterlijk "The code is unaudited" | nee | n.v.t. Deploy 2022-08-19 | **HOOG volgens de regel, maar zie de noot**: legacy-code die sinds 2021 intensief bekeken is (OpenBook is een fork). De upgrade authority `6XvcBm…` is de sleutel die sinds de FTX-hack (nov 2022) als gecompromitteerd geldt |
| 4 | **Omnipair** | ✅ SCANBAAR | github.com/omnipair/omnipair-rs | `omnixgS8fnqHfCcTGKWj6JtKjzpJZ1Y5y9pyFkQDkYE` | $0,68M | **LICHT**: Ackee (rapport + Trident-fuzzing) en Offside, plus audit-fix-branches (`audit-critical-01`, `audit-high-01/02`, …) | **ja** (`32a6d169`) | **JA.** ~3.300/650 regels in `programs/omnipair` tussen de audit-docs (`f83fccd`, 2026-01-28) en de deploy (2026-08-16) | **HOOG** (lage TVL) |
| 5 | **PsyOptions** (psy_american) | ✅ SCANBAAR | github.com/mithraiclabs/psyoptions | `R2y9ip6mxmWUj4pt54jP2hz2dgvMozy9VTSwMWE7evs` | $0,63M | **GEEN gevonden** in de repo | nee | n.v.t. Deploy 2025-02-26 = HEAD | **MIDDEL** (geen audit, maar lage TVL en oude, rustige code) |
| 6 | **Futarchy AMM** (MetaDAO) | ✅ SCANBAAR | github.com/metaDAOproject/programs | `FUTARELBfJfQ8RDGhg1wdhddq1odMAJUePHFuBYfUxKq` (+ `VLTX1ish…` conditional_vault, launchpads `moon…`/`Moo…`, `LiQnow…`, `WALL8…`, `pPV2…`, `pbPP…`, `gvnr…`, `GaTEj…`: allemaal live en VOLLEDIGE BRON) | $14,4M | **ZWAAR**: OffsideLabs ×3, Accretion ×3, Ackee, OtterSec (2025–2026) | **ja** (`e263bbf8`) | Nee. De deploy is de verified commit | **LAAG** |
| 7 | **Exponent** (core) | ✅ SCANBAAR | github.com/exponent-finance/exponent-core | `ExponentnaRg3CQbW6dqQNZKXp7gtZ9DGMp1cwC4HAS7` (+ `3D6ojc…` admin) | $14,2M + $12,1M (twee listings) | **ZWAAR**: 24 rapporten in `exponent-audits` (OffsideLabs, OtterSec, Sec3, Certora, Accretion, Adevar) | nee | Onbekend. De repo is een gepubliceerde momentopname (2 commits, 2026-08-18), dus er is geen historie | **LAAG** |

**Noten bij de ✅-lijst:**

- **Exponent:** de listings "Risk Tranching" en "Strategy Vaults" draaien op programma's (tranching, vaults) die **niet** in de publieke `exponent-core` staan; die bevat alleen core en admin. Het is onzeker of hun TVL door het scanbare core-programma loopt. Ik tel dit als één protocol.
- **Byreal:** in `lib.rs` kiezen `cfg`-features het ID. `REALQq…` (mainnet-build) en `45iBNk…` zijn allebei live; sourcecheck op `REALQq…` geeft VOLLEDIGE BRON (68 paden, 0 eigen ontbrekend).
- **Serum:** de prioriteit volgt de regel (geen audit, echt geld), maar de kans op een vondst is laag gezien de leeftijd en het aantal mensen dat de code al heeft bekeken. Let op: de upgrade-key `6XvcBm…` geldt als gecompromitteerd.

## Pijplijnverbeteringen tijdens deze ronde (`sourcecheck.py`)

1. **String-bewust commentaar strippen.** Een `//` of `/*` binnen een string-literal (URL, glob) wiste eerder stukken code, waardoor handlers verdwenen. Nu is er een kleine Rust-lexer (strings, raw strings, char-literals, geneste blokken), met unit-tests.
2. **Native handlers in de hele crate.** Serum heeft zijn logica in `state.rs` (`State::process`) en werd daardoor ten onrechte SHELL. Nu tellen niet-triviale `process*`/`handle*`-functies overal in de crate mee.
3. **Regressietest:** Larix blijft SHELL/PRIVAAT; Quarry, Saber, Solido en Serum geven VOLLEDIGE BRON.

## Afvallers (één regel per listing)

**CEX, geen on-chain programma (7):**
- Phemex, OSL Exchange, HTX, VALR, BitKan, HashKey Global, Webot.

**SHELL / LIVE = PRIVAAT (2):**
- **Drift Trade:** in de publieke `drift-labs/protocol-v2` (HEAD) is de **hele `#[program]`-module uitgecommentarieerd**, en de org toont nog maar 2 repo's. `dRiftyHA…` is live, maar de publieke bron is een schil.
- **Streamflow:** de publieke `streamflow-program` is het oude v1-programma (`2DvvSE…`, bestaat niet op mainnet). Het live programma `strmRqUC…` staat niet publiek; slechts 1 van 26 bronpaden komt overeen.

**Geen eigen Solana-programma (6):**
- **YO Protocol:** alleen Solidity.
- **KAIO:** alleen Solidity.
- **Ribbon:** alleen EVM/Aevo.
- **Kyros:** alleen SDK.
- **DefiTuna** (Lending/Liquidity/AMM, 3 listings → 1): alleen SDK's en CPI-interface (`fusionamm-cpi`); het programma zelf is niet publiek.

**Closed source (geen publieke programma-repo; 27 listings):**
- **$10M–$20M:**
  - Hubra Staked SOL: org `block-sync-one` bestaat niet.
  - Aster Bridge.
  - Bitwise USCC (Superstate).
  - Perena Vaults.
  - Solayer Restaking: `solayer-labs` heeft alleen docs, RPC, agave-fork, CLI en Jupiter-integratie.
  - Unitas USDu: `Unipayfi` heeft alleen Go-CEX-tools, POR en een audit-repo.
  - Exponent Strategy Vaults en Risk Tranching: hun eigen programma's staan niet publiek (zie de noot bij Exponent).
  - Tessera V.
  - Bonk Staked SOL: LST, vermoedelijk een SPL stake pool.
  - marginfi LST: LST, vermoedelijk een SPL single-pool.
- **$500K–$1M:**
  - Archer Exchange: `SquareRoot-Labs` is leeg.
  - Byzanlink RWA Markets.
  - Parcl V3: alleen Python-SDK en docs.
  - Sat Rush.
  - Lavarage: org leeg.
  - TurboFlow Perps.
  - Adrastea LRT.
  - Solayer USD (zelfde org als Solayer).
  - Zeus btcSOL: org `ZeusNetworkHQ` bestaat niet.
  - Bonkswap.
  - Perena Dex (zelfde als Perena).
  - The Vault Unstake Pool: de gelinkte org `fuma-nama` is niet gerelateerd.
  - Armada: `mithraiclabs` heeft alleen de site en helpers.
  - UNCX Network Solana: `chainsulting` is hun auditor, geen eigen repo.
  - Overpass.

**Overgeslagen op verzoek (1):** Loyal Earn.

## Telling

| | Aantal |
|---|---|
| Nieuwe listings in $500K–$20M (DeFiLlama, excl. de al beoordeelde 72) | **49** |
| — overgeslagen op verzoek | 1 (Loyal Earn) |
| — ontdubbeld | DefiTuna 3→1; Exponent 2 listings → 1 scanbaar protocol; Solayer 2 en Perena 2 (beide closed) |
| ✅ **Scanbaar** (VOLLEDIGE BRON + live) | **7 protocollen** (Byreal, Manifest, Serum, Omnipair, PsyOptions, Futarchy/MetaDAO, Exponent), samen 8 listings |
| — waarvan **HOOG** | **4**: Byreal, Manifest, Serum (met noot), Omnipair |
| — MIDDEL / LAAG | 1 / 2 |
| Afgevallen (listings) | **40** |
| — CEX | 7 |
| — closed source | 25, plus de 2 Exponent-sublistings (tranching/vaults-programma niet publiek) = 27 |
| — geen eigen Solana-programma | 6 listings (YO, KAIO, Ribbon, Kyros, DefiTuna ×3 → 1 protocol) |
| — SHELL / LIVE = PRIVAAT | 2 (Drift, Streamflow) |

De aantallen tellen op tot 49 inclusief Loyal. De Exponent-sublistings staan bij "closed" voor hun eigen programma, maar hun org is wel als scanbaar meegeteld; dat is ±1 qua boekhouding.

## Advies voor de volgende triage

Volgorde op basis van geld × onbekendheid:

1. **Byreal** ($13,3M, geen audit gevonden). Wel eerst nagaan of het een (vrijwel) ongewijzigde Raydium-CLMM-fork is. Zo ja, dan zitten de verschillen met Raydium in de echte nieuwe code.
2. **Manifest** ($19,6M, ~11k regels na de enige menselijke audit, verified build).
3. **Omnipair** (klein, maar ~3.300 regels na de audit).

Pas het privilege-filter uit CLAUDE.md toe: alleen bevindingen die een gebruiker of aanvaller zonder rechten kan benutten, krijgen diepe triage.
