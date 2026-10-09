# Reflect-fork: verificatie (stap 5)

Datum: 2026-10-04.

Methode: alleen lezen. Ik heb publieke GitHub-repos gekloond en read-only `getAccountInfo`-queries gedaan op mainnet-beta en devnet, en de OtterSec verify-API geraadpleegd. Er is geen transactie verstuurd en geen exploit geschreven.

## 1. Officiële repo

- **De fork.** `donjne/reflect-program-library`, laatste push 2025-01-10.
  - GitHub-beschrijving: "Reflect Protocol fork of the Solana-Program Library for internal development".
  - GitHub ziet hem niet als fork (`fork: false`), dus er is geen upstream gekoppeld.
- **De officiële organisatie.** **`palindrome-eng`**.
  - Gevonden via Reflect's docs (docs.reflect.money) en de `agent-skills`-repo van palindrome-eng.
- **Geen publieke kopie in de officiële org.**
  - Ik vond geen `reflect-program-library`, `insurance-fund` of `tokenised-bonds`.
  - Ik heb `protocol-v2` (een Drift-fork), `contract-interfaces` en `audits` gekloond en doorzocht.
  - Geen van de drie bestanden (`calculate_receipts_on_mint.rs`, `withdraw.rs` en `lockup.rs` van tokenised-bonds) komt erin voor.
  - Er staat ook geen verwijzing in naar de program IDs van de fork.
- **Wat de officiële org wél publiek beschrijft.**
  - `contract-interfaces`: `reflect-core`, `reflect-proxy-program`, `rlp`, `reflect-tranches` en `kamino-pool-wrapper`.
  - `audits` (OffsideLabs): DeltaNeutral (sep 2025), Proxy (nov 2025) en CoreYieldRouting (feb 2026).
  - Dat is een andere, nieuwere codebase. Insurance-fund en tokenised-bonds komen er niet in voor.

**Conclusie:** er is geen officiële versie van deze code gevonden om mee te vergelijken. Of de bugs "nog steeds" in officiële code zitten, valt niet vast te stellen. Er is in elk geval geen publieke officiële bron die ze bevat.

## 2. Draaien de programma's live?

| Programma | Program ID | mainnet-beta | devnet |
|---|---|---|---|
| insurance-fund | `2MN1Dbnu7zM9Yj4ougn6ZCNNKevrSvi9AR56iawzkye8` | **bestaat niet** (`value: null`, slot 453289989) | bestaat niet |
| tokenised-bonds | `6ZZ1sxKGuXUBL8HSsHqHaYCg92G9VhMNTcJv1gFURCop` | **bestaat niet** (`value: null`, slot 453289990) | bestaat niet |
| solana-stake-market (ter info) | `sSmYaKe6tj5VKjPzHhpakpamw1PYoJFLQNyMJD3PU37` | bestaat niet | – |
| reflect-single-pool (ter info) | `rFLUicC93hnZMVZc2hhd4oetXEDG4ja6TaFVSAftsVe` | bestaat niet | – |

Geen van deze accounts bestaat. Daarom zijn er ook geen gegevens over executable, owner, upgrade authority of ProgramData-slot.

Een valse aanwijzing die ik heb uitgesloten: in de officiële org staat `SBondMDrcV3K4kxZR1HNVT7osZxAHVHgYXL5Ze1oMUv` (live, BPFLoaderUpgradeable, laatst gedeployed in slot 420822344). Dat is het **Switchboard On-Demand**-oracleprogramma uit de Drift-fork. Het heeft niets met bonds te maken.

## 3. Komt de gedeployde code overeen met de source?

- **OtterSec verify-API (`verify.osec.io/status/<id>`):** voor beide IDs `is_verified: false`, met lege `on_chain_hash`. Er staat geen programma on-chain om te verifiëren.
- **`solana-verify`:** niet geïnstalleerd, en ook niet nodig: er is geen on-chain bytecode om te hashen.
- Ik kan niet uitsluiten dat Reflect deze code ooit onder een **ander** program ID heeft gedeployd. Dat zou alleen blijken uit hun eigen deploy-overzicht of IDL's. Ik heb geen live programma gevonden dat erbij past.

## 4. Conclusie per bug

| Bug | In officiële code? | Programma live? | Build geverifieerd/match? | Oordeel |
|---|---|---|---|---|
| Insurance-fund: omgekeerde mint-ratio (`calculate_receipts_on_mint.rs:22`) | Niet gevonden in de publieke officiële repos | **Nee**: ID bestaat niet op mainnet of devnet | n.v.t. (geen on-chain code) | **NIET MELDEN** |
| Bonds: `total_receipt_supply` daalt nooit (`withdraw.rs:36-38`) | Niet gevonden | **Nee** | n.v.t. | **NIET MELDEN** |
| Bonds: lockup-PDA botst voor alle gebruikers (`lockup.rs:70-73`) | Niet gevonden | **Nee** | n.v.t. | **NIET MELDEN** |

Volgens de regel in CLAUDE.md is dit een test- of dev-repo, en een melding zou je geloofwaardigheid kosten.

Wil je er toch iets mee? Een vrijblijvend, kort bericht kan alleen als je het expliciet als hygiëne-tip brengt en niet als kwetsbaarheid in live code. Bijvoorbeeld: "jullie publieke dev-fork bevat deze rekenfout; als dit ontwerp ooit in productie komt, let hierop."
