# Shortlist 2: schift-ronde DeFiLlama Solana-protocollen

Datum: 2026-10-04.

Methode:
- DeFiLlama-API (github-veld en Solana-TVL).
- Website/docs gescraped op GitHub-links.
- Logische org-namen geprobeerd via de GitHub-API.
- `declare_id!` gezocht in de `src/lib.rs` van eigen crates.
- `livecheck.py` gedraaid (alleen read-only `getAccountInfo`).
- Bij elk ✅-geval: audits geteld (repo + web) en OtterSec verified-build-status opgevraagd.

Er zijn nog geen scans of triage gedaan.

| Protocol | Status | Repo-URL | Program ID | Solana-TVL | Audits | Prioriteit |
|---|---|---|---|---|---|---|
| **Orderly Bridge** | ✅ SCANBAAR | https://github.com/OrderlyNetwork/solana-vault (`packages/solana/contracts/programs/solana-vault`) | `ErBmAD61mGFKvrFNaTJuxoPwqrS8GgtwtqJTJVjFWx9Q` | $7,4M | **GEEN gevonden** voor het Solana-programma (Zellic/Guardian-audits gaan over de EVM-contracten); build **niet** verified | **HOOG** |
| **SolvBTC** | ✅ SCANBAAR | https://github.com/solv-finance/SolvBTC-Solana-Contract | `soLv1S6GsAEVEnXmVY3oz6GtrNJteQ28iTyRQrHXvkz` | $2,7M | **GEEN publiek Solana-audit gevonden** (Solv noemt Quantstamp, Certik, SlowMist e.a. voor EVM). Build verified, HackenProof-bounty dekt dit contract | **HOOG/MIDDEL** |
| **Quarry** | ✅ SCANBAAR | https://github.com/QuarryProtocol/quarry | `QMNeHCGYnLVDn1icRAfQZpjPLBNkfGbSKRB83G5d8KB` (mine), `QMMD16kj…` (merge-mine), `QMWoBmAy…` (mint-wrapper) | $6,9M | **LICHT** (Quantstamp en Soteria, uit 2022). Build niet verified; nog upgradebaar | **MIDDEL** |
| **OpenBook** | ✅ SCANBAAR | https://github.com/openbook-dex/openbook-v2 | `opnb2LAfJYbRMAHHvqjCwQxanZn7ReEHp1k81EohpZb` | $1,2M | **LICHT** (1 audit-PDF in de repo). Build niet verified, maar veel gebruikt en veel bekeken | **LAAG** |
| **Phoenix Spot** | ✅ SCANBAAR | https://github.com/Ellipsis-Labs/phoenix-v1 | `PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY` | $1,1M | **LICHT** (OtterSec). Build verified, bug bounty, veel bekeken | **LAAG** |
| International Stable Currency | GEEN EIGEN PROGRAMMA | https://github.com/TheISCTeam (alleen een JS-bridge) | – | $2,4M | – | – |
| Renzo | GEEN EIGEN PROGRAMMA (Solana) | https://github.com/Renzo-Protocol (alleen EVM, geen Rust/Solana-repo) | – | $5,0M | – | – |
| Invesco USTB (Superstate) | CLOSED SOURCE | (github.com/superstateinc heeft geen Solana-programma) | – | $3,9M | – | – |
| Crypto.com Liquid Staking | CLOSED SOURCE | – | – | $6,2M | – | – |
| Hubble | CLOSED SOURCE | https://github.com/hubbleprotocol (alleen libraries en templates, geen CDP-programma) | – | $1,6M | – | – |
| PancakeSwap AMM | CLOSED SOURCE (Solana-deel) | (github.com/pancakeswap bevat alleen EVM) | – | geen aparte Solana-TVL op DeFiLlama | – | – |
| FluxBeam | CLOSED SOURCE | – | – | $3,0M | – | – |
| HawkFi | CLOSED SOURCE | – | – | $1,0M | – | – |
| DOOAR V2 | CLOSED SOURCE | – | – | $4,7M | – | – |
| Katana | CLOSED SOURCE | – | – | $2,3M | – | – |

## Details bij de ✅-gevallen

| Program | Upgrade authority | Laatste deploy-slot | Verified build (OtterSec) |
|---|---|---|---|
| Orderly `ErBmAD…` | `6aQHPsgaSxCGwf1uAVetEmzuz9bpv9Rn4bq9jTg91RH8` | 409901584 | nee |
| SolvBTC `soLv1S…` | `BsF2mR9brTd7u7wGWrejksQzsdrGFNcddRSYeNpHZixM` | 376935908 | ja (commit `4c8f194`) |
| Quarry mine `QMNe…` | `6Jtj2TDynyyZWkwY5MjWqYqhkQztAdvNFra1HW1BZmKR` | 145136845 | nee |
| OpenBook v2 `opnb2…` | `CZoAmQErbMwhSNA5WtbWLcwGE1mhXEv4hTvyvvHXGkrr` | 250859864 | nee |
| Phoenix `PhoeNiX…` | `8mv7G3fJq5a5ej7E14vgcSGeQKH79emjU9fVfuhyitEq` | 231433470 | ja |

## Kanttekeningen

- **Orderly:**
  - De repo bevat ook een `uln`-programma (`3HUspN…`). Dat is LayerZero-vendored code die niet op mainnet bestaat, dus het telt niet mee.
  - De build is niet verified. Vóór een eventuele melding moet je dus eerst vaststellen of de repo-code gelijk is aan de bytecode.
- **SolvBTC:** controleer bij de triage of het programma zelf geld vasthoudt of alleen de mint authority beheert. De TVL is de token-supply.
- **Quarry:** de laatste commit is uit 2022 en het programma is sindsdien nooit opnieuw gedeployd. Oude, maar beproefde code.
- **"CLOSED SOURCE":** ik vond geen publieke programma-repo via DeFiLlama, de website of logische org-namen. Ik heb niet uitputtend gezocht.
- **Audit-telling:** gebaseerd op de repo-inhoud en een snelle zoekopdracht op het web. Een audit die alleen op een site van de auditor staat, kan gemist zijn.

## Advies

Begin met **Orderly solana-vault**: het meeste geld ($7,4M), geen Solana-audit gevonden en geen verified build. Daarna **SolvBTC**.
