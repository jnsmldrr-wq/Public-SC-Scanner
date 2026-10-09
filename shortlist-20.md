# Shortlist-20: echt scanbare Solana-protocollen ($1M–$10M TVL)

Datum: 2026-10-04.

Pijplijn: DeFiLlama → repo → eigen programma → `livecheck.py` → `sourcecheck.py` (VOLLEDIGE BRON / SHELL / LIVE=PRIVAAT) → audit-diepte. Alleen lezen en read-only RPC; er zijn geen scans of triage gedaan.

## Uitkomst in één alinea

**Het doel van 20 is niet gehaald: de lijst binnen de filters is op.**

- De DeFiLlama-API geeft voor Solana **72 protocollen** met TVL tussen $1M en $10M. Dat is de hele lijst, niet alleen de top.
- **50** daarvan zijn in eerdere rondes al echt beoordeeld (`shortlist.md`, `shortlist-2.md`, `shortlist-bulk.md`).
- De overige **22** waren in de bulk-ronde alleen op categorie weggefilterd (CEX, LST, bridge, curator) en zijn nu alsnog per stuk beoordeeld.
- Nieuw scanbaar: **3 protocollen** (Lido/Solido, NEAR Omni Bridge, Starke).
- Totaal binnen het filter: **10 scanbaar** (VOLLEDIGE BRON).

## ✅ Nieuw scanbaar deze ronde (gesorteerd op prioriteit)

| Protocol | Status | Repo | Program ID | Solana-TVL | Audits | Verified | Code ná audit? | Prioriteit |
|---|---|---|---|---|---|---|---|---|
| **Starke Staked SOL** (Starke vaults) | ✅ SCANBAAR (VOLLEDIGE BRON; 45 bronpaden, 0 eigen ontbrekend) | github.com/starke-labs/vaults | `56gFPCzaTGNJQcZrpfewDDgGYD8SR7G2RCrxy5z26jch` (vaults). Ook live: `Gk7syLzEbk46Ez6Fr9pApPPhTJMDavKxiN9JHAtfhZCz` (transfer_hook, immutable) | $1,3M | **LICHT**: 1× Kudelski Security (PDF in `audits/`, 2025-04/05) | nee | **JA, fors.** 54 commits, ~5.100/440 regels in `programs/vaults` tussen de audit (`af93838`, 2025-05-02) en de deploy (2026-06-24). O.a. **Pyth-Pro-oracle** (`withdraw_in_deposit_token_pyth_pro.rs`, `token_oracle_config.rs`), `withdraw_in_deposit_token.rs`, fund-update/pause, `vault.rs` +516 regels | **HOOG** (oracle- en withdraw-logica na de audit, echt geld; wel lage TVL) |
| **NEAR Bridge** (Omni Bridge, Solana-deel) | ✅ SCANBAAR (VOLLEDIGE BRON; 30 paden, 0 eigen ontbrekend) | github.com/Near-One/omni-bridge (`solana/programs/bridge_token_factory`) | `dahPEoZGXfyV58JqqH85okdHmpN8U2q8owgPUXSCPxe` | $6,8M | **LICHT**: audit-branches `audit-22-11-24`, `minor-audit-improvments`; commits "Audit fixes (#167)", "#2 (#171)", "fast transfers audit fixes (#309)" (dec 2024 – mei 2025). Auditor niet genoemd; "Claude audit fixes" (2026-02) telt niet als audit | nee | **JA.** 7 programma-commits na de laatste audit-fix (mei 2025) t/m de deploy (2026-06-25): o.a. Fogo/omni-address-ondersteuning (#620), admin-setter `derived_near_bridge_address` (#623), `finalizeTransferSol` voor program-owned recipients (#630). Exacte omvang niet te meten: de Solana-map is na de audit verplaatst (diff toont +6.177 als volledig nieuw) | **HOOG** (bridge met echt geld en relevante post-audit wijzigingen) |
| **Lido** (Lido for Solana / Solido) | ✅ SCANBAAR (VOLLEDIGE BRON; native entrypoint met 12 handlers; bytecode bevat geen bronpaden, dus niet te vergelijken) | github.com/lidofinance/solido (`program/`) | `CrX7kMhLC3cSsXJdT7JDgqrRVWGnUpX3gfEfxxU2NVLi` | $6,3M | **ZWAAR**: Bramah Systems (2021-07), Neodyme (2021-08, 2022-04, 2022-10); 4 PDF's in `audit/` | nee | **Nee.** De deploy (2022-12-07) heeft 0 programma-commits na de Neodyme-v2-audit (2022-10-13). Let op: HEAD heeft 79 latere commits die **niet** gedeployd zijn; scan dus deploy-commit `72dc28a` | **LAAG** (zwaar geaudit, gedeployde code = geaudite code; Lido for Solana is uitgefaseerd) |

**Wat ID-detectie in deze ronde misliep:** Solido en Omni Bridge zetten hun program-ID níet met `declare_id!` in `lib.rs`. Solido krijgt het bij de deploy mee, Omni Bridge genereert het in `build.rs` uit `PROGRAM_ID`. De automatische detectie miste ze dus. Ik heb de mainnet-ID's met de hand uit de repo-configuratie gehaald (`solido_config.json`, `solana/.env.example`) en daarna met `livecheck` en `sourcecheck` bevestigd.

- Voor Omni Bridge stonden er 3 kandidaat-ID's in de repo. Alleen `dahPEo…` bestaat op mainnet; `Gy1XPw…` (de default in `build.rs`) en `3ZtEZ8…` (Anchor.toml) bestaan niet.

## ✅ Scanbaar uit eerdere rondes (nu ook door sourcecheck bevestigd)

| Protocol | Program ID | TVL | Audits | Verified | Code ná audit? | Prioriteit | Bron |
|---|---|---|---|---|---|---|---|
| Quarry | `QMNeHCGY…` (+5) | $6,9M | LICHT | nee | ja (~2.000 regels) | HOOG → **getrieerd: niks** | `triage-quarry.md` |
| Saber | `SSwpkEEc…` | $5,8M | LICHT | nee | nee | HOOG | `shortlist-bulk.md` |
| SolvBTC | `soLv1S6G…` | $2,7M | GEEN publiek Solana-audit | ja | onbekend | **HOOG** | `shortlist-2.md` (sourcecheck nu: VOLLEDIGE BRON) |
| OpenBook | `opnb2LAf…` | $1,2M | LICHT | nee | ja (~370 regels) | MIDDEL | `shortlist-bulk.md` |
| Phoenix Spot | `PhoeNiXZ…` | $1,1M | LICHT (2 firma's) | ja | minimaal | LAAG | `shortlist-bulk.md` |
| Solomon (Chancery) | `ChnryP5R…` | $7,4M | ZWAAR | ja | nee | LAAG | `shortlist-bulk.md` |
| Privacy Cash | `9fhQBbum…` | $1,8M | ZWAAR | ja | nee | LAAG → **getrieerd: niks** | `triage-privacycash.md` |

**Door sourcecheck afgewaardeerd:**

- **Larix:** LIVE = PRIVAAT, de repo is een schil (`triage-larix.md`).
- **Orderly:** LIVE = PRIVAAT (gedeeltelijk). De live bytecode bevat 3 nonce-bestanden die niet publiek zijn (`triage-orderly.md`).

## Afvallers deze ronde (één regel per protocol)

**Geen eigen programma**

- **13 CEX'en:** Bitvavo, BloFin, Coinstore, Bitunix, Poloniex, WEEX, Deribit, Zoomex, Bitrue, Gate US, LeveX, Pionex, BitMart. Dit zijn custodial beurzen; de "TVL" zijn walletsaldi, er is geen on-chain programma.
- **Loopscale Curation:** een risk curator op Loopscale-vaults. Geen eigen programma; de GitHub-org `loopscale` hoort bij een niet-gerelateerd persoon.
- **Japan Staked SOL:** `DawnLabsTech` heeft alleen docs, een TS-`vault` (zonder `declare_id!`/programma) en een CLI.

**Closed source** (geen publieke programma-repo via API, site/docs of org-naam):

- **StandX Bridge:** geen repo gevonden.
- **N1 Exchange Bridge:** geen repo gevonden.
- **Phase Stake:** geen URL en geen repo.
- **Lantern Staked SOL:** org `LanternStake` heeft geen publieke repos.

## Telling

| | Aantal |
|---|---|
| Solana-protocollen met $1M–$10M TVL (DeFiLlama, volledige lijst) | **72** |
| ✅ Scanbaar (VOLLEDIGE BRON, eigen live programma) | **10** (Starke, NEAR Omni Bridge, Lido/Solido, Quarry, Saber, SolvBTC, OpenBook, Phoenix Spot, Solomon/Chancery, Privacy Cash) |
| — waarvan HOOG en nog niet getrieerd | **4**: Starke, NEAR Omni Bridge, SolvBTC, Saber |
| Afgevallen | **62** |
| — CEX (geen programma) | 13 |
| — closed source | ~32 (o.a. alle LST's zonder repo, DEX'en als FluxBeam/GoonFi/DOOAR, RWA's) |
| — geen eigen programma (SDK/EVM/curator/wrapper) | ~13 |
| — live = privaat of schil | 2 (Larix, Orderly) |
| — niet live / dubbel | rest (o.a. Reflect-fork-ID's; Sunny leunt op Quarry) |

De tellingen per afvalreden zijn bij benadering (±2): een paar protocollen vallen onder meer dan één reden, bijvoorbeeld "GEEN EIGEN" én "closed".

## Om 20 te halen

Daarvoor moet het filter ruimer. Opties, read-only en in dezelfde pijplijn:

- **TVL $10M–$50M:** meer protocollen met een eigen programma; die zijn wel vaker zwaar geaudit.
- **TVL $0,3M–$1M:** veel kleine, vaak licht of niet geaudite programma's.
- **Andere bron:** bijvoorbeeld de OtterSec verified-programs-lijst of de Solana security.txt-registry. Daar heeft elk programma per definitie publieke broncode.

## Voortgang / hervatten

- De ruwe data staat in `shortlist/s20/` (`all.json`, `todo.json`, repos in `shortlist/s20/repos/`).
- Alle 72 protocollen binnen het filter zijn verwerkt; er staat niets open.
- Gerepareerd in `sourcecheck.py` tijdens deze ronde: `#[program]` gevolgd door andere attributen (bijv. `#[allow(...)]`) werd niet herkend. Omni Bridge gaf daardoor eerst ten onrechte SHELL.
