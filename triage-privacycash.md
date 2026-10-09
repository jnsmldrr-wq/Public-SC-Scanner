# Triage: Privacy Cash (zkcash)

- Repo: https://github.com/Privacy-Cash/privacy-cash. Gescand op HEAD `f79b82f` (2026-09-29).
- Programma: `anchor/programs/zkcash` (Anchor, Tornado-Nova-ontwerp: Groth16 met 2 inputs en 2 outputs, Poseidon-Merkle-boom met hoogte 26).
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC. Geen exploit, geen transactie.

## 1. Livecheck

| ID | Mainnet | Devnet | Hoort bij |
|---|---|---|---|
| `9fhQBbumKEFuXtMBDw8AaQyAjCorLGJQiS3skWZdQyQD` | **LIVE**, BPFLoaderUpgradeable, upgrade authority `AWexibGxNFKTa1b5R5MN4PJr9HWnWRwf8EW9g8cLx3dM`, deploy-slot 427378345 | live | build **zonder** `devnet`/`localnet`-features (`lib.rs:12-13`) |
| `ATZj4jZ4FFzkvAcvk27DW9GRkgSbFnHo49fKKPQXU7VS` | bestaat niet | live | alleen `devnet`/`localnet`-builds (`lib.rs:9-10`) |

**De bytecode komt overeen met de source.** OtterSec meldt `is_verified: true` voor `9fhQ…`:

- Hash `4f0a26e6…5989bd` op commit `06ce337`, geverifieerd op 2026-09-30.
- `git diff 06ce337 HEAD -- anchor/programs/zkcash/src` is leeg. De gescande code is dus precies de live code.

Ik heb alleen het mainnet-pad beoordeeld:

- `ADMIN_PUBKEY = AWex…`, gelijk aan de upgrade authority.
- `ALLOW_ALL_SPL_TOKENS = false`.
- Mainnet-`ALLOWED_TOKENS`: USDC, USDT, ORE, ZEC, stORE en jl-tokens.

## 2. Scan

Scanner-uitvoer: 5 High, 10 Medium, 4 Low (`pc-report.md` / `pc-report.json`).

## 3. Triage van elke HIGH/MEDIUM

| Melding | Oordeel |
|---|---|
| SOL-CFG-201 `programs/zkcash/Cargo.toml` | **Fout-positief.** De workspace-`anchor/Cargo.toml:8` zet `overflow-checks = true`. |
| SOL-OWNER-002 `lib.rs:653` `recipient` (SOL) | **Zo bedoeld.** Hij mag elk account zijn. De key zit in `ext_data_hash` (`lib.rs:229-242`) en is daarmee via het bewijs vastgelegd. Een relayer kan hem dus niet omwisselen. |
| SOL-OWNER-002 `lib.rs:657` `fee_recipient_account` | Zit ook in `ext_data_hash`. Zie kandidaat F-1 (informatief). |
| SOL-OWNER-002 `lib.rs:732` `recipient` (SPL) | Wordt alleen gebruikt als `token::authority` van `recipient_token_account`, en die key zit in de hash. Geen risico. |
| SOL-OWNER-002 `lib.rs:758` `fee_recipient_ata` | Zit in de hash, en SPL `transfer` dwingt een gelijke mint af. Zie F-1. |
| SOL-INIT-006 `lib.rs:601/614/677/690` | **Fout-positief.** De scanner heeft het woord in een commentaar gevonden. Deze nullifier-accounts gebruiken juist `init`, wat de bescherming tegen dubbel uitgeven is. |
| SOL-INIT-006 `lib.rs:747` `tree_ata` | Dit is het ATA van de `global_config`-PDA voor deze mint. Bij een bestaand account wordt niets gereset. Geen risico. |
| SOL-ARITH-104 `utils.rs:161-199` | Casts van u128 naar u64 op `x * rate / 10000` met `rate ≤ 10000`. Het resultaat is dus `≤ x ≤ u64::MAX` en kapt nooit af. Geen risico. |

## 4. De punten waar je specifiek naar vroeg

**Dubbel uitgeven (nullifiers): correct afgedwongen.**

- **Nullifier-PDA's:** `nullifier0` en `nullifier1` worden aangemaakt met `init` (`lib.rs:604-624`). Een tweede uitgave van dezelfde nullifier mislukt, omdat het account al bestaat.
- **Andere slot:** dezelfde nullifier in de andere slot is afgedekt door `nullifier2`/`nullifier3` (`lib.rs:626-636`). Die moeten nog `SystemAccount` zijn; als de PDA al in de andere slot is aangemaakt, mislukt de check.
- **Twee keer dezelfde nullifier in één transactie:** het circuit dwingt af dat ze verschillen (`circuits/transaction.circom:115-123`).
- **Malleabiliteit:** `N` en `N + p` geven dezelfde veldwaarde maar een andere PDA. Dat is afgevangen, omdat `verify_proof` `verify()` gebruikt met `CHECK = true` (`groth16.rs:93`, `utils.rs:267`). Elke publieke input moet dan kleiner zijn dan de veldmodulus.
- **Bindende gegevens:** de nullifier bevat het pad-indexnummer en een handtekening (`transaction.circom:69-73`).

**Merkle-root:**

- `is_known_root` weigert een root van alleen nullen (`merkle_tree.rs:80`).
- De root-geschiedenis bevat de laatste 100 roots.
- Inputs met bedrag 0 slaan de membership-check over (`transaction.circom:84-86`). Dat is Nova-standaard en levert niets op.

**Rekenwerk bij deposit en withdraw:**

- `check_public_amount` (`utils.rs`) rekent in het veld en bindt `publicAmount = extAmount − fee`. Het weigert `i64::MIN`, en een deposit die niet groter is dan de fee.
- Het circuit eist `sumIns + publicAmount === sumOuts`, met een 248-bits bereikcheck op de outputs.
- Bij een SOL-withdraw wordt eerst `ext + fee + rent-minimum` gecontroleerd (`lib.rs:297-306`) en daarna alles met checked math gedaan.
- Als de recipient gelijk is aan het pool-account zelf, laat de lamport-balanscheck van de runtime de transactie mislukken.
- Ik vond geen manier om meer op te nemen dan in de notes zit.

**Eigenaarschap en signers:**

- **Admin-functies:** `has_one = authority`, plus een `ADMIN_PUBKEY`-check bij `initialize`.
- **SPL-deposit:** `signer_token_account.owner == signer` en de mint wordt gecontroleerd (`lib.rs:378-385`).
- **SPL-pool:** `tree_account` en `tree_ata` zijn allebei aan dezelfde `mint` gekoppeld. Een bewijs uit boom X kan dus geen tokens uit pool Y halen.

## 5. Echte kandidaten

**Niks gevonden met risico voor gebruikersgeld.**

Er is één informatief punt dat alleen protocol-inkomsten raakt:

### F-1 (laag/informatief): de ontvanger van de withdrawal-fee is vrij te kiezen
`lib.rs:655-657`, `lib.rs:754-758`, `lib.rs:320-344`, `lib.rs:480-498`

- **Wat het programma afdwingt:** een minimale fee via `global_config.withdrawal_fee_rate`, standaard 0,25% (`utils::validate_fee`).
- **Wat het niet afdwingt:** dat de fee naar het protocol gaat. `fee_recipient_account`/`fee_recipient_ata` worden alleen via `ext_data_hash` gekozen door wie het bewijs maakt.
- **Code die op een check wijst, maar zonder check:**
  - `ErrorCode::InvalidFeeRecipient` ("Fee recipient does not match global configuration") bestaat, maar wordt nergens gebruikt.
  - Het commentaar "CHECK: Validated in the instruction logic" bij `fee_recipient_ata` klopt niet.
- **Gevolg:** wie zelf een transactie indient (eigen signer, geen relayer) kan `fee_recipient` op een eigen adres zetten. De 0,25% gaat dan terug naar zichzelf.
- **Geldrisico:** alleen gemiste protocol-fee. Het geld van gebruikers in de pool loopt geen risico.
- **Voorbehoud:** dit kan een bewuste keuze zijn (het relayer-fee-model van Tornado Nova). Het staat er al sinds de eerste commit en is waarschijnlijk bekend bij de 6 audits (Accretion, HashCloak, Kriko, Sherlock, Veridise, Zigtur). Die PDF's heb ik niet doorzocht (geen pdf-tool aanwezig).
- **Advies:** niet als kwetsbaarheid melden. Hooguit als vraag ("is dit bedoeld?"), en alleen als het niet al in een audit staat.

## Conclusie

Zwaar geaudit en geverifieerd. De kritieke onderdelen (nullifiers, het binden van bedragen, root-checks en de range van publieke inputs) zijn correct. Dit protocol is geen kandidaat voor een melding.
