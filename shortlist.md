# Shortlist: schift-ronde DeFiLlama Solana-protocollen

Datum: 2026-10-04.

Methode:
- DeFiLlama-API (`api.llama.fi/protocols`) voor GitHub-veld en TVL.
- Website en docs gescraped op GitHub-links.
- GitHub-repo-lijsten bekeken.
- `declare_id!` gezocht in de `src/lib.rs` van eigen crates.
- `livecheck.py` gedraaid (alleen read-only `getAccountInfo`).

Er zijn nog geen scans of triage gedaan.

TVL is de Solana-TVL volgens DeFiLlama, in miljoen USD.

| Protocol | Status | Repo-URL | Program ID | Solana-TVL | TVL-waard? |
|---|---|---|---|---|---|
| **Privacy Cash** | ✅ SCANBAAR | https://github.com/Privacy-Cash/privacy-cash (`anchor/programs/zkcash`) | `9fhQBbumKEFuXtMBDw8AaQyAjCorLGJQiS3skWZdQyQD` (mainnet-build); `ATZj4j…` is alleen devnet | $1,8M | Ja: klein, maar het programma bewaart zelf het geld van gebruikers (privacy-pool), dus een bug raakt de TVL direct |
| **Solomon USDv** | ✅ SCANBAAR (met kanttekening) | https://github.com/SolomonLabs/chancery | `ChnryP5RcZtMvP8vvVyPGUhwCg6uDJc53vCe3sxr11Sz` | $7,4M | Twijfel. Chancery is Solomons mint/redeem-rail, maar het is niet zeker dat de USDv-TVL daarin zit: de stake- en vault-programma's (Zigtur-audits) staan niet publiek. De code is zwaar geaudit en formeel geverifieerd, dus de kans op een vondst is laag. |
| Laine SOL | GEEN EIGEN PROGRAMMA | https://github.com/laine-sa (alleen governance- en validatortools) | – | $1,5M | – (LST, geen eigen programma-code) |
| Pico Staked SOL | GEEN EIGEN PROGRAMMA | https://github.com/pico-sol (bots/tools, geen staking-programma) | – | $2,3M | – (LST) |
| SoSoValue Indexes | GEEN EIGEN PROGRAMMA (Solana) | https://github.com/SoSoValueLabs/ssi-protocol (alleen Solidity/EVM) | – | $3,4M | – |
| Gauntlet | GEEN EIGEN PROGRAMMA | – | – | $8,0M | – (risk curator op vaults van anderen) |
| Mansory | CLOSED SOURCE | – | – | $3,0M | – |
| Stronghold Staking | CLOSED SOURCE | – | – | $5,1M | – (LST, vermoedelijk stake pool) |
| Save SOL | CLOSED SOURCE | (github.com/solendprotocol heeft geen saveSOL-programma) | – | $7,4M | – (LST, vermoedelijk stake pool) |
| Bumpin Trade | CLOSED SOURCE | https://github.com/bumpin-exchange (alleen assets/forks) | – | $4,6M | – |
| Nirvana V2 | CLOSED SOURCE | – | – | $2,5M | – |
| Vectis Finance | CLOSED SOURCE | (org `vectis-finance` bestaat, maar zonder publieke repos) | – | $4,4M | – |
| Upshift | CLOSED SOURCE | – | – | $8,8M | – |
| Synatra | CLOSED SOURCE | – | – | $2,2M | – |
| Fragmetric | CLOSED SOURCE | https://github.com/fragmetric-labs (alleen docs en forks; restaking-programma niet publiek) | – | $3,2M | – |

## Kanttekeningen

- **Wat "CLOSED SOURCE" hier betekent:** ik vond geen publieke programma-repo via DeFiLlama, de website/docs of voor de hand liggende org-namen op GitHub. Ik heb niet uitputtend gezocht.
  - De GitHub-zoek-API zat aan zijn rate limit, en `gh` is niet geïnstalleerd.
  - Er kan dus nog iets bestaan onder een onverwachte naam.
- **LST's met "vermoedelijk stake pool":** niet on-chain geverifieerd. Ik ben gestopt bij de eerste blokkade (geen publieke repo).
- **Privacy Cash:** de mainnet- en devnet-ID worden met `cfg(feature)` gekozen. De ID zonder feature (`9fhQ…`) is de mainnet-build en is live.
  - Upgrade authority: `AWexibGxNFKTa1b5R5MN4PJr9HWnWRwf8EW9g8cLx3dM`.
  - Laatste deploy-slot: 427378345.
- **Chancery:**
  - Upgrade authority: `934modVoNj5TUV69Ub3YXJAvGxWvpqRiHAydTadJxA2L`.
  - Laatste deploy-slot: 444033132.
  - De repo `chancery-devnet` (`3doMTb…`) staat alleen op devnet.
- **Nog te doen vóór een melding:** controleren of de gedeployde bytecode overeenkomt met de repo (verified build). Dat is buiten deze schift-ronde gebleven.
