# Triage: Orderly solana-vault

- Repo: https://github.com/OrderlyNetwork/solana-vault (`main` @ `d13bb81`, 2026-01-25).
- Programma: `packages/solana/contracts/programs/solana-vault` (Anchor, LayerZero-v2-OApp).
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC. Geen exploit, geen transactie.

## 1. Livecheck

| ID | Bron | Mainnet | Oordeel |
|---|---|---|---|
| `ErBmAD61mGFKvrFNaTJuxoPwqrS8GgtwtqJTJVjFWx9Q` | `programs/solana-vault/src/lib.rs` | **LIVE**, BPFLoaderUpgradeable, upgrade authority `6aQHPsgaSxCGwf1uAVetEmzuz9bpv9Rn4bq9jTg91RH8`, deploy-slot 409901584 (**2026-03-30 15:58 UTC**) | gescand |
| `3HUspNHm1sW6YvgqpTemHa8HmjwwqTEXEAh7weEyBZUn` | `programs/uln` (LayerZero-code, vendored) | bestaat niet | genegeerd |

## 2. Scan

Ik heb alleen `programs/solana-vault` gescand. Resultaat: 8 High, 18 Medium, 82 meldingen in totaal (`orderly-report.md` / `orderly-report.json`).

## 3. Triage van elke HIGH/MEDIUM

| Melding | Oordeel |
|---|---|
| SOL-CFG-201 `Cargo.toml` | **Fout-positief.** De workspace-`contracts/Cargo.toml:7` zet `overflow-checks = true`. |
| SOL-ARITH-102 `oapp_lz_receive.rs:136` (`token_amount - fee`) | Wordt vlak ervoor afgedekt door `require!(token_amount >= fee)` (`:132-135`). Dat is de Guardian-fix T1-I-02. Geen risico. |
| SOL-ARITH-101 `oapp_lz_receive.rs:149` (`lamports + amount`) | Een overflow betekent meer dan 1,8·10¹⁹ lamports. Dat is onmogelijk, en overflow-checks staan aan. Geen risico. |
| SOL-ARITH-101 `msg_codec.rs:153` | Dit is het lezen van bytes, geen rekenwerk. Fout-positief. |
| SOL-CPI-004 `oapp_lz_receive.rs:167`, `deposit_sol.rs:105` | Een `system_instruction::transfer` met `system_program: Program<System>`. Het aangeroepen ID ligt dus vast. Geen risico. |
| SOL-TYPE-003 `oapp_lz_receive.rs:233` | Het ATA-adres wordt eerst exact gecontroleerd (`:195-202`), anders is het net aangemaakt. Geen type-verwarring mogelijk. |
| SOL-OWNER-002 `deposit_sol.rs:38` `sol_vault` | PDA met `seeds = [SOL_VAULT_SEED]`. Geen risico. |
| SOL-INIT-006 (`set_*`, `deposit.rs:43`) | Alle `set_*`-instructies vereisen een admin-signer (`has_one = admin`/`owner`) of een `manager_role`-PDA. `deposit.rs:43` is het vault-ATA zelf. Er valt niets te resetten. |
| SOL-REMACC-007 (`remaining_accounts` naar de LZ-endpoint) | Die accounts gaan alleen naar de LayerZero-endpoint-CPI, en de endpoint controleert ze zelf. Geen risico. |
| SOL-ARITH-104 `MsgType::Deposit as u8` | Een enum-cast, geen afkapping. Fout-positief. |

## 4. De punten waar je specifiek naar vroeg

**Rekenwerk en saldo bij deposit en withdraw:**

- **Deposit:** het bedrag uit de parameters wordt precies zo overgemaakt (`deposit.rs:127-130`, `deposit_sol.rs:99-112`). Daarna wordt precies dat bedrag cross-chain gemeld.
- **Token-controle bij deposit:**
  - De token moet `allowed` zijn en `deposit_token == allowed_token.mint_account`.
  - De SOL-hash is uitgesloten bij SPL-deposits (`deposit.rs:92`).
  - Dit is de fix voor Sherlock "any token → USDC" en Guardian T3-C-01.
- **Withdraw:** gebruikt `token_amount − fee` met de require-check ervoor. De SPL- of systeemtransfer faalt vanzelf als het saldo te laag is.

**Wie mag een withdrawal autoriseren?**

- `lz_receive` kan iedereen aanroepen, maar het bericht moet via `endpoint::clear` (`oapp_lz_receive.rs:108-122`) door de LayerZero-endpoint gaan.
- De endpoint controleert of de payload-hash voor (receiver = deze OApp, `src_eid`, `sender`, `nonce`, `guid`) is vastgelegd. Daarna wordt het bericht verwijderd.
- De `?` geeft een fout gewoon door, ondanks de `let _ =`.
- Het endpoint-programma komt uit `oapp_config` en is alleen door de admin te zetten.

**Kan een bericht vervalst of opnieuw afgespeeld worden?**

- Vervalsen kan alleen als de peer of de LayerZero-DVN's gecompromitteerd zijn.
- Replay wordt voorkomen door `clear` (een bericht kan maar één keer verwijderd worden).
- Daarnaast is er optioneel een ordered-nonce-check (`vault_authority.check_nonce`, `:71`).

**Wordt de afzender echt geverifieerd?**

- Ja: `peer.address == params.sender` voor PDA `[PEER, oapp, src_eid]` (`:21-29`).
- `set_peer` is alleen voor de admin.

**Ontvanger:**

- `receiver` moet gelijk zijn aan de receiver uit het bericht (`:60`).
- Het token-ATA moet gelijk zijn aan `ATA(receiver, mint)` (`:195-202`).
- Dit is de fix voor de Sherlock-high "anyone can call lz_receive to steal withdrawn funds".

## 5. Echte kandidaten

**Niks gevonden waarmee een buitenstaander geld kan stelen.** Elke withdrawal vereist een geauthenticeerd LayerZero-bericht van de geregistreerde peer.

Ter info drie observaties (geen meldingen):

- **I-1. Overlap in berichttypes, ingevoerd ná de laatste audit-fix.**
  - Plaats: `msg_codec.rs:6-16`, `oapp_lz_receive.rs:128`.
  - Sinds `83754cd` (2026-01, "solana ceffu integration") accepteert `lz_receive` type `0` (`WithdrawType::FromEvmSender`) én `1` als withdrawal.
  - Voorheen was alleen `1` (`MsgType::Withdraw`) een withdrawal. Type `0` is in dezelfde codec ook `MsgType::Deposit`.
  - Dit is alleen een probleem als de peer ooit een bericht van type 0 met een andere betekenis terugstuurt. De berichten zijn geauthenticeerd, dus het is niet aanvalbaar.
  - Wel fragiel ontwerp, en deze wijziging is (voor zover zichtbaar) niet door een audit gekomen.
- **I-2. Mislukte withdrawals blijven alleen als event achter.**
  - Plaats: `oapp_lz_receive.rs:151-192` en `:235-236`.
  - Als de ontvanger niet rent-exempt is, executable is, of een bevroren ATA heeft, wordt het bericht toch verwijderd. Er volgt alleen `WithdrawSolFailed`/`FrozenWithdrawn`; het geld blijft in de vault.
  - Herstel hangt af van off-chain afhandeling door Orderly. Dit is bewust ontwerp (Guardian H-03: "withdrawals can block the channel") en niet stelen.
- **I-3. `decode_packed`/`decode` gebruiken `.unwrap()` zonder lengtecheck.**
  - Plaats: `msg_codec.rs:57-169`.
  - Een misvormd bericht laat het programma crashen. Alleen de peer kan zo'n bericht sturen, dus het risico is hooguit een DoS door Orderly zelf.

## 6. Verificatie: komt de code overeen met de live versie?

**Niet hard vast te stellen.** Ik heb geen `solana-verify`, `anchor`, `cargo` of Docker, dus ik kan geen reproduceerbare build maken en de hash vergelijken. OtterSec meldt `is_verified: false`.

On-chain:
- ProgramData: `BZcCii22kzi26tT28hxd9f1aGPV7sEgMfubP5bQfb8LM`.
- 891.081 bytes, sha256 `ed0c801de462df535c80d3cab2f149254dacf4e39553308cc8483876f4ead493`.

Read-only aanwijzingen die **sterk** wijzen op `main` (HEAD `d13bb81`):

- **Teksten in de bytecode:** alle 20 fout- en logteksten uit de `main`-source staan in de on-chain bytecode. Daaronder vallen teksten die alleen in de nieuwe code voorkomen ("Manager role is not allowed", "Setting withdraw token index", "Withdraw amount must be no less than withdraw fee", "AccountId is invalid", enzovoort).
- **Oude code past niet:** een tekst die alleen in de oude `fix-otter`-branch voorkomt ("Invalid message type:") ontbreekt in de bytecode.
- **Instructies:** alle instructienamen van `main` komen voor (`Instruction: SetWithdrawBroker`, `SetManagerRole`, `DepositSol`, `LzReceive`, …).
- **Tijdlijn:** de deploy (2026-03-30) is van ná de laatste programmacommit op `main` (2026-01-25, inclusief "set program id for mainnet"). Er is geen nieuwere branch.

> **Correctie (2026-10-04, `sourcecheck.py`).** Ik heb de bronpaden in de bytecode vergeleken met de repo. Daaruit blijkt dat de live bytecode **3 eigen bestanden bevat die in géén publieke branch of commit staan**:
> - `programs/solana-vault/src/instructions/oapp_instr/next_nonce.rs`
> - `programs/solana-vault/src/instructions/oapp_instr/set_nonce.rs`
> - `programs/solana-vault/src/state/oapp_state/nonce.rs`
>
> De gedeployde versie is dus gebouwd uit een **niet-gepubliceerde** versie: publieke `main` plus extra nonce-instructies. De overige 26 eigen paden komen wel overeen.
>
> **Gevolg:**
> - De triage hierboven dekt de publieke code. De nonce-logica die live draait (`set_nonce`/`next_nonce`, raakt de replay- en volgorde-bescherming) is **niet beoordeeld**.
> - Het eerdere oordeel "zeer waarschijnlijk `main`" is daarmee te sterk. Status voor de pijplijn: **LIVE = PRIVAAT (gedeeltelijk)**.

**Oorspronkelijk oordeel (vóór de correctie): zeer waarschijnlijk `main`, maar niet bewezen.** Hard bewijs krijg je met:

```bash
solana-verify get-program-hash ErBmAD61mGFKvrFNaTJuxoPwqrS8GgtwtqJTJVjFWx9Q
solana-verify build packages/solana/contracts --library-name solana_vault
```

Daarna vergelijk je de twee hashes. Let op: `solana-verify build` gebruikt Docker.

## 7. Al geaudit?

**Ja, zwaar (3+ audits).**

| Audit | Wanneer | Bewijs |
|---|---|---|
| Sherlock (contest "Orderly Solana Vault") | okt 2024 | branch `fix-sherlock`; publieke bevindingen o.a. "anyone can call lz_receive to steal", "deposit any token → USDC", "unordered execution" |
| OtterSec | nov–dec 2024 | branches `fix-otter`, `fix-otter-second` |
| Guardian (LayerZero Solana) | 2025 (fixes t/m sep 2025) | commits `Fix-T1/T2/T3-…` in `main` (o.a. T3-C-01, T2-H-01, T2-H-03) |
| Zellic | 2023, 2025 | dekt Orderly EVM en Strategy Vault, **niet** dit Solana-programma |

**Wat niet zichtbaar geaudit is:** alles ná de laatste Guardian-fix (`4582ca7`, 2025-09-15). Dat zijn 4 commits:

- multi-collateral (`522cb01`);
- ceffu-integratie (`83754cd`);
- account-id (`e8a7337`/`d13bb81`).

In totaal ±40 regels in `msg_codec.rs` en `oapp_lz_receive.rs`. Daar komt I-1 vandaan.

## Conclusie

Geen melding. Zwaar geaudit, en de cross-chain authenticatie (endpoint `clear`, peer-check, receiver- en ATA-binding) is correct. De niet-geaudite wijzigingen na september 2025 zijn klein en gaan alleen over geauthenticeerde berichten. Hooguit kun je I-1 als vrijblijvende opmerking via hun security-contact noemen.
