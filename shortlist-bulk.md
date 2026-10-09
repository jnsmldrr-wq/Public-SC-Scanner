# Shortlist bulk: Solana-protocollen met $1M–$10M TVL

Datum: 2026-10-04.

Methode: alleen lezen en read-only RPC. Er zijn geen scans of triage gedaan.

1. **Ophalen.** `api.llama.fi/protocols`, gefilterd op Solana-`chainTvls` tussen $1M en $10M. Dat gaf **72** protocollen.
   - **31** vielen af op categorie (CEX, Liquid Staking, Bridge, Risk Curators, Onchain Capital Allocator).
   - Er bleven **41** over, niet de gevraagde 50. Ik heb ze allemaal meegenomen.
2. **Repo zoeken.** Eerst het github-veld van de API, daarna gescrapete GitHub-links van website en docs, daarna logische org-namen.
   - Bij elke gevonden repo een `declare_id!` gezocht in de `src/lib.rs` van een eigen crate. Voorbeelden en vendored code tellen niet mee.
3. **Livecheck.** `livecheck.py` op elk eigen ID. Ruwe uitvoer in `shortlist/bulk/livecheck.txt`.
4. **Audit-diepte.** Per programma bekeken:
   - branchnamen;
   - commitberichten (audit, otter, sherlock, Fix-T…, enzovoort);
   - audit-bestanden in de repo;
   - de OtterSec verified-build-API;
   - de deploydatum (`getBlockTime` van het ProgramData-slot), vergeleken met de laatste audit-commit;
   - een `git diff` van de programmacode tussen de laatste audit en de gedeployde commit.

   Ruwe data in `shortlist/bulk/audits.json`.

## Resultaat: ✅ SCANBAAR (gesorteerd op prioriteit)

| # | Protocol | Status | Repo | Program ID | Solana-TVL | Audits | Verified build? | Code gewijzigd ná laatste audit? | Prioriteit |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Quarry** | ✅ SCANBAAR | github.com/QuarryProtocol/quarry | `QMNeHCGYnLVDn1icRAfQZpjPLBNkfGbSKRB83G5d8KB` (mine) + 5 andere `Q…`-programma's, allemaal live | $6,9M | LICHT (Quantstamp 2021-12, Soteria 2022-03) | nee | **JA, substantieel.** 16 commits, 46 bestanden, ~2.000 regels in `programs/` tussen Soteria (2022-03-29) en de deploy (v5.2.0, 2022-07/08). O.a. herschreven `quarry-operator`, `Fix set_rewards_share` | **HOOG** |
| 2 | **Saber** | ✅ SCANBAAR | github.com/saber-hq/stable-swap | `SSwpkEEcbUqx4vtoEByFjSkhKdCT862DNVb52nZg1UZ` | $5,8M | LICHT (Bramah Systems, 2022-01) | nee | Nee: na de audit alleen dependency-bumps (Cargo/yarn). Let op: de repo-HEAD heeft 19 commits die **niet** gedeployd zijn (deploy 2022-02-07) | **HOOG** (licht geaudit, echt geld; wel oude, veel geforkte code) |
| 3 | ~~Larix~~ | ❌ **CLOSED SOURCE (alleen publieke SDK)**, gecorrigeerd 2026-10-04 | github.com/ProjectLarix/larix-lending | `7Zb1bGi32pfsrBkzWdqd4dFhUXwp5Nybr1zuaEwN34hy` (live) | $1,4M | – | nee | n.v.t. De repo heeft geen processor/handlers (entrypoint was een stub). De bytecode verwijst naar privé-bronbestanden. De eerder genoemde "~3.400 regels" waren SDK-bestanden, geen programmawijzigingen. Zie `triage-larix.md` | **AFGEVOERD** |
| 4 | **OpenBook** | ✅ SCANBAAR | github.com/openbook-dex/openbook-v2 | `opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb` | $1,2M | LICHT (1 audit-PDF, geüpload 2023-10-25; auditor niet genoemd in de README) | nee | **JA.** 74 commits, ~240/130 regels in `src/` (o.a. `place_take_order`, `open_orders_account`, `book.rs`) tussen de audit-upload en de deploy (2024-02-27). 13 latere commits niet gedeployd | **MIDDEL** (lage TVL, veel bekeken) |
| 5 | **Phoenix Spot** | ✅ SCANBAAR | github.com/Ellipsis-Labs/phoenix-v1 | `PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY` | $1,1M | LICHT (2 firma's: OtterSec in 2023-02 en update 2023-08; MadShield 2023-11. Branches `eugene/audit2`, `update-osec-audit`) | **ja** | Minimaal: 1 commit, 4 regels (#39) tussen MadShield en de deploy (2023-11-21) | **LAAG** (formeel HOOG volgens de regel "licht", maar verified, bijna niets na de audit, lage TVL) |
| 6 | **Solomon USDv** (Chancery) | ✅ SCANBAAR | github.com/SolomonLabs/chancery | `ChnryP5RcZtMvP8vvVyPGUhwCg6uDJc53vCe3sxr11Sz` | $7,4M | ZWAAR (Accretion A26SOL1 en A26SOL2, Zenith 2026-09; plus remediation-ledgers in `audits/`) | **ja** (commit `0dafa95`) | Nee: de deploy (2026-09-03) is precies de verified commit v1.0.1 | **LAAG** (let op: de USDv-stake/vault-programma's staan niet publiek) |
| 7 | **Privacy Cash** | ✅ SCANBAAR | github.com/Privacy-Cash/privacy-cash | `9fhQBbumKEFuXtMBDw8AaQyAjCorLGJQiS3skWZdQyQD` | $1,8M | ZWAAR (6 firma's: Accretion, HashCloak, Kriko, Sherlock, Veridise, Zigtur) | **ja** (commit `06ce337`) | Nee: de deploy (2026-06-18) is de verified commit; stORE-audit 2026-06-19 | **LAAG** (al getrieerd: niks gevonden) |

**Hoe ik de prioriteitsregel heb toegepast.** Letterlijk volgens jouw definitie (eigen live programma + geld + GEEN/LICHT of substantiële code na de audit) zouden Quarry, Saber, Larix, OpenBook en Phoenix allemaal HOOG zijn. Ik heb die groep daarom verder gerangschikt:

- **Phoenix** is verlaagd naar LAAG: de build is verified en er is bijna niets na de audit veranderd.
- **OpenBook** is verlaagd naar MIDDEL: lage TVL en veel bekeken.
- **Quarry** staat bovenaan: de meeste niet-geaudite code en het meeste geld.

### Niet in de bulk-lijst door het categoriefilter, maar wel eerder als ✅ gevonden

| Protocol | Program ID | TVL | Audits | Verified | Na de audit gewijzigd? | Bron |
|---|---|---|---|---|---|---|
| SolvBTC ("Bridge") | `soLv1S6GsAEVEnXmVY3oz6GtrNJteQ28iTyRQrHXvkz` | $2,7M | GEEN publieke Solana-audit gevonden (wel HackenProof-bounty) | ja | onbekend | `shortlist-2.md` |
| Orderly Bridge ("Bridge") | `ErBmAD61mGFKvrFNaTJuxoPwqrS8GgtwtqJTJVjFWx9Q` | $7,4M | ZWAAR (Sherlock, OtterSec, Guardian) | nee | ±40 regels na sep 2025 | `triage-orderly.md` (al getrieerd: niks) |

**Les:** het filter op "Bridge" gooit ook protocollen met een eigen Solana-vaultprogramma weg. **SolvBTC** is daardoor de interessantste kandidaat die buiten deze lijst valt.

### Ontdubbeling en relaties

- **Quarry en Saber:** zelfde team (Saber Labs), maar aparte programma's en repos. Ik tel ze apart.
- **Sunny:** bouwt op Quarry (merge-mine) en heeft geen eigen publiek programma. Het valt hieronder af, en zijn TVL hangt deels aan Quarry.
- **Phoenix Spot:** `Ellipsis-Labs/rise-public` bevat twee helper-programma's voor Phoenix **perps**. `close-position-and-withdraw` (`6oy4nTsJWjAyMX86fxbWVK7UfpWPzzG6AdLouhLNkoen`) is live, `trader-onboarder` niet. Dit hoort niet bij de Spot-listing; ik noteer het alleen.
- **Rise.rich** (launchpad, org `riserich`) is iets anders dan Ellipsis' "Rise" (Phoenix-SDK). Ik heb ze niet samengevoegd.

## Afvallers (één regel per protocol)

**Geen eigen programma (publiek):**
- **Renzo:** `Renzo-Protocol` bevat alleen Solidity.
- **SoSoValue Indexes:** alleen EVM (`SoSoValueLabs/ssi-protocol`).
- **International Stable Currency:** `TheISCTeam` heeft alleen een JS-bridge.
- **Reflect Tranches:** `palindrome-eng` heeft alleen een Jupiter-routing-client (`reflect-routing`). Het oude `srl-program` (`6CiDLj…`) bestaat niet op mainnet.
- **PiggyBank:** `zsociety-io` bevat alleen Aleo-programma's, niets voor Solana.
- **tramplin.io:** alleen een PRNG-library (`ssrand`).
- **Rise.rich:** alleen docs en een TS-SDK.
- **Sunny:** geen programma-repo; leunt op Quarry.

**Closed source** (geen publieke programma-repo gevonden via API, site/docs of org-namen):
- **BULK:** alleen client, keychain en audits-repo, geen programma.
- **PancakeSwap AMM V3:** `pancakeswap` bevat alleen EVM.
- **Francium:** `Francium-DeFi` bevat alleen "materials".
- **GoonFi:** geen repo gevonden.
- **DOOAR V2:** geen repo gevonden.
- **Bumpin Trade:** alleen assets.
- **StakePoint:** de site linkt naar een persoonlijk account zonder publieke repos.
- **Vectis Finance:** org zonder repos.
- **Scorch:** geen repo gevonden.
- **Invesco USTB (Superstate):** geen Solana-repo.
- **Fragmetric:** alleen docs en forks.
- **RateX DEX:** alleen de repos `Audit-Report` en `Mediakit`; het programma is niet publiek.
- **Mansory:** geen repo gevonden.
- **FluxBeam:** geen repo gevonden.
- **Nirvana V2:** geen repo gevonden.
- **Adrastea Restaking Operator:** geen repo gevonden.
- **Oro Finance:** geen repo gevonden.
- **NX Finance:** alleen docs.
- **Katana:** geen repo gevonden.
- **Synatra:** geen repo gevonden.
- **Pascal:** alleen een Python-quickstart.
- **Hubble:** alleen libraries en templates, plus een audits-repo; het CDP-programma is niet publiek.
- **Jupiter Offerbook:** `jup-ag` bevat alleen interfaces en clients voor dit product.
- **Atrix:** geen repo gevonden.
- **AlphaQ:** geen repo gevonden.
- **HawkFi:** geen repo gevonden.

**Weggefilterd op categorie in stap 1 (31):**
- **CEX:** Bitvavo, BloFin, Coinstore, Bitunix, Poloniex, WEEX, Deribit, Zoomex, Bitrue, Gate US, LeveX, Pionex, BitMart.
- **Liquid Staking:** Save SOL, Lido, Crypto.com, Stronghold, Lantern, Phase, Pico, Japan, Laine, Starke.
- **Risk Curators / Allocator:** Gauntlet, Loopscale Curation, Upshift.
- **Bridge:** NEAR Bridge, StandX Bridge, N1 Exchange Bridge, **SolvBTC** (zie hierboven) en **Orderly Bridge** (zie hierboven).

## Kanttekeningen

- **"Closed source":** ik heb niet uitputtend gezocht. De GitHub-API-limiet (60/uur) liet geen brede zoekopdracht toe, en een repo onder een onverwachte naam kan gemist zijn.
- **Audit-telling:** gebaseerd op de repo (bestanden, commits, branches) en eerdere webzoekopdrachten. Een audit die alleen op een site van de auditor staat, kan ontbreken. Vooral bij Saber en OpenBook is de echte telling mogelijk hoger.
- **Matcht de code de bytecode?** Bij de niet-verified gevallen (Quarry, Saber, Larix, OpenBook) is niet bewezen dat de repo gelijk is aan de bytecode. Ik heb de commit gebruikt die het dichtst vóór de deploydatum ligt.
  - Bij Saber en OpenBook staat er code op `main` die **niet** live is.
  - Scan dus de commit van de deploydatum, niet HEAD.
