# Triage: Starke vaults

- Repo: https://github.com/starke-labs/vaults.
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC (`getAccountInfo`, `getProgramAccounts`, `getTokenSupply`). Geen exploit, geen transactie.

> **Herbeoordeling volgens het privilege-filter (CLAUDE.md, 2026-10-04): niks GOUD.**
>
> | Kandidaat | Wie kan het | Prioriteit |
> |---|---|---|
> | S-1 | Alleen de manager. Managers moeten door Starke gewhitelist zijn (`create_vault.rs:155`) | **LAAG** |
> | S-2 | Alleen de manager | **LAAG** |
> | S-3 | Vereist de co-sign van `STARKE_AUTHORITY` | **LAAG** |
>
> Geen enkele bevinding is bruikbaar voor een gebruiker of aanvaller zonder rechten.

## 1. Livecheck en sourcecheck

| Programma | ID | Mainnet | Bron |
|---|---|---|---|
| **vaults** | `56gFPCzaTGNJQcZrpfewDDgGYD8SR7G2RCrxy5z26jch` | **LIVE**, upgrade authority `FfypZj9R3RyiqdLRJ8mzrpKH2QdcfEKhFnazFW5XVGxB`, deploy-slot 428559285 (**2026-06-24**) | **VOLLEDIGE BRON**: 45 bronpaden in de bytecode, 33 in de repo, 0 eigen bestanden ontbrekend |
| transfer_hook | `Gk7syLzEbk46Ez6Fr9pApPPhTJMDavKxiN9JHAtfhZCz` | LIVE | VOLLEDIGE BRON (niet gescand; buiten scope) |
| `programs/jupiter` | `JUP6Lkb…` | LIVE | Dit is Jupiters eigen programma, als interface meegekopieerd; sourcecheck zegt terecht PRIVAAT. Telt niet mee. |

Verified build (OtterSec): nee.

**Gescande versie: `06558eb`** ("Add Pyth Pro oracle support", 2026-06-21).

- Dat is de laatste commit die `programs/vaults` wijzigt vóór de deploy van 2026-06-24.
- `git diff 06558eb HEAD -- programs/vaults Cargo.toml` is leeg. HEAD (`95f1f4d`, 2026-09-30) voegt alleen tooling toe, dus HEAD is voor het programma gelijk aan de deploy.

**Audit:** Kudelski Security, scope-commit `fe6f1b8`, rapport van 2025-05-02, fixes t/m `af93838`. Alles erna is post-audit: 54 commits, ~5.100 regels in `programs/vaults`.

## 2. Scan

`scan.py programs/vaults` gaf 13 High en 40 Medium, 53 meldingen in totaal (`starke-report.md`).

| Melding | Oordeel |
|---|---|
| SOL-CFG-201 | **Fout-positief.** De workspace-`Cargo.toml:6` zet `overflow-checks = true`. |
| SOL-ORACLE-301 `pyth_pro_price.rs:176`, `lib.rs:124/157`, `token_price.rs:36` | **Fout-positief.** Zie §3: elke prijs gaat via `validate_oracle_price` (Pyth Pro) of `get_price_no_older_than` + confidence-check (klassieke Pyth). De meldingen zitten op de helpers die die al gevalideerde prijs omrekenen. |
| SOL-CPI-004 `swap_on_jupiter.rs:60`, `swap_to_deposit_token_on_jupiter.rs:62` | Het doelprogramma ligt vast (`Program<'info, Jupiter>`). **Maar zie S-2:** de inhoud van de CPI is niet begrensd. |
| SOL-CPI-004 `token_metadata.rs:47/80` | Metaplex-metadata-CPI met een vast programma. Geen risico. |
| SOL-ARITH-102 `withdraw_token.rs:75/225` | Treft `msg!`-regels; fout-positief. |
| SOL-ARITH-104 (casts) | `u128 → u64` na `x · ratio / PRECISION` met `ratio ≤ PRECISION`, of na prijs-omrekening met checked math. Er kapt niets af in een richting die een aanvaller helpt. Fout-positief. |
| SOL-OWNER-002 `close_vault.rs:88/97` | Transfer-hook-accounts, gecontroleerd via de hook-CPI. Geen risico. |
| SOL-REMACC-007 (`remaining_accounts` voor AUM en withdraw) | Zie S-3: niet uniek of volledig afgedwongen, maar achter de co-sign van `STARKE_AUTHORITY`. |
| SOL-INIT-006 | ATA's van vault, user of manager; er valt niets te resetten. Geen risico. |

## 3. De punten waar je specifiek naar vroeg

**SOL-ORACLE-301 bij Pyth Pro (post-audit):**

- Elke prijs gaat door `verify_pyth_pro_message`. Dat is een CPI naar het getypeerde `pyth_lazer_solana_contract`-programma, dat de ed25519-handtekening via de instructions-sysvar controleert.
- Daarna volgt `get_checked_price` (`pyth_pro_price.rs:118-173`). Die controleert:
  - `channel_id` en `feed_id` tegen de PDA-gebonden `TokenOracleConfig`;
  - `price > 0`;
  - **leeftijd** (`FeedUpdateTimestamp`, anders de payload-timestamp) tussen 0 en `max_age_seconds`;
  - **confidence** (`conf·10⁴/price < confidence_threshold_bps`).
- Het klassieke Pyth-pad (`token_price.rs`) gebruikt `get_price_no_older_than` met een confidence-check (KS-SRK-F-03 is opgelost).
- **In orde.**

**Rekenwerk bij deposit en withdraw:**

- Te minten vtokens = `deposit_value · supply / AUM`, in u128, naar beneden afgerond. Dat is in het voordeel van de vault (`vtoken.rs:69-74`).
- De withdraw-ratio is `amount · PRECISION / supply`, ook naar beneden afgerond (`withdraw_token.rs:73-95`).
- Afrondingsrichting en precisie zijn in orde.

**SOL-CPI-302:** geen balans die na een transfer zonder `reload` wordt gelezen. De nieuwe detector vond ook niets.

**Wie mag wat?**

- Deposit, withdraw, `swap_to_deposit_token` en de oracle-config vereisen **co-sign door `STARKE_AUTHORITY`** (`STRK1me6…`).
- `swap_on_jupiter`, `update_fund` en `mint_management_fees` vereisen **alleen de manager** van de vault.

## 4. Echte kandidaten

### S-1 (HIGH volgens de code; nu latent): de kwartaallimiet op de management fee werkt niet. De manager kan onbeperkt fee-vtokens minten. **POST-AUDIT**

Plaats:

- `programs/vaults/src/instructions/mint_management_fees.rs:17-24` en `:28-45`;
- `programs/vaults/src/state/vault.rs:288-331` (`can_pay_management_fees`);
- `vault.rs:39` (`last_fees_paid_timestamp`).

**Wat er misgaat:**

- `mint_management_fees` mag alleen als `can_pay_management_fees(now)` waar is. Die functie vergelijkt het jaar en kwartaal van `last_fees_paid_timestamp` met nu.
- **`last_fees_paid_timestamp` wordt nergens bijgewerkt.** In de hele git-geschiedenis is het alleen bij `initialize` op `0` gezet (`vault.rs:137`; `git log -G 'last_fees_paid_timestamp\s*='` is leeg).
- De vergelijking is dus altijd "1970-Q1 ≠ nu", oftewel altijd waar.
- Elke aanroep mint `supply · rate / (10000 − rate)` vtokens naar de manager. Dat kan **onbeperkt vaak**, ook meerdere keren in één transactie.

**Versterkende factor:**

- `update_fund` (alleen de manager) mag `management_fee_rate` op elk moment zetten, tot `MAX_MANAGEMENT_FEE_RATE = 10000`, oftewel 100% (`vault.rs:77`, `:84`).
- Bij 100% verdubbelt elke aanroep de supply (`vtoken.rs:80-81`).

**Geldrisico:** verwatering van alle beleggers. De manager krijgt een willekeurig groot deel van de vault-NAV.

- Bij 2% en 50 aanroepen bezit de manager ~64% van de supply.
- Bij 100% en 10 aanroepen bezit de manager ~99,9%.

Uitbetaling verloopt via een withdraw, die de co-sign van `STARKE_AUTHORITY` nodig heeft. Maar de verwatering zelf vermindert direct de claim van elke belegger.

**Huidige blootstelling (read-only gecontroleerd):**

- Er zijn 10 Vault-accounts on-chain. **Alle hebben `management_fees_rate = 0` en `last_fees_paid_timestamp = 0`.**
- Er wordt dus nu nergens een fee gemint. Het risico is latent en ontstaat zodra een manager een fee instelt, of als een manager kwaadwillig is.
- Ook een eerlijke manager of bot die per ongeluk twee keer per kwartaal aanroept, rekent dubbel.

**Geschiedenis:** toegevoegd in `b415cc3` ("feat: add management fees (#13)", 2025-12-08), na de Kudelski-audit. De instructie zit in de live bytecode (`Instruction: MintManagementFees` aanwezig).

### S-2 (MEDIUM, gedeeltelijk bekend): `swap_on_jupiter` begrenst de Jupiter-route niet. **Geaudite code** (Kudelski KS-SRK-F-01, *Acknowledged*)

Plaats: `programs/vaults/src/instructions/swap_on_jupiter.rs:13-73`.

**Wat er misgaat:**

- De manager tekent alleen.
- Het programma roept Jupiter aan met de **vault-PDA als signer**, met door de manager gekozen `data` en `remaining_accounts`.
- De gevalideerde `input_token_account` en `output_token_account` (vault-ATA's van whitelisted mints) worden **niet** aan de route gekoppeld.
- Na de swap wordt niets gecontroleerd: geen minimale output, en niet of het resultaat in de vault-ATA staat.

**Wat Kudelski zei en wat erbij komt:**

- Kudelski rapporteerde dit als "Lack of Slippage Protection" (Medium, Acknowledged).
- De impact lijkt groter dan slippage. Als de Jupiter-route een bestemming buiten de vault toestaat, kan de manager vault-tokens uit de vault sturen in plaats van alleen ongunstig te ruilen. Jupiter v6 heeft varianten met een aparte `destination_token_account`.
- **Dat heb ik niet geverifieerd** en ik bouw geen route om het te testen. Het is dus een vermoeden op basis van de accountstructuur.
- De constraints in de struct laten zien dat het **de bedoeling** is dat de waarde in de vault blijft. De code dwingt dat niet af.

**Geldrisico:** vault-tokens, als de manager kwaadwillig of gecompromitteerd is. De manager is wel door Starke gewhitelist (`manager_whitelist`).

### S-3 (laag, defense-in-depth): de AUM komt uit door de aanroeper geleverde accounts, zonder controle op uniekheid of volledigheid. Post-audit (Pyth Pro) én het oude pad.

Plaats: `controllers/pyth_pro_price.rs:195-246`, `controllers/vault_aum.rs:15-54`, gebruikt in `deposit*.rs` en `withdraw_in_deposit_token*.rs`.

**Wat er misgaat:**

- `remaining_accounts` worden per (mint, tokenaccount, oracle) gelezen.
- Er is geen check dat elke vault-holding **precies één keer** voorkomt.
- **Dubbel** meegeven verhoogt de AUM: er wordt te veel uitbetaald bij `withdraw_in_deposit_token`.
- **Weglaten** verlaagt de AUM: er worden te veel vtokens gemint bij een deposit.

**Waarom het nu niet aanvalbaar is:** alle betrokken instructies vereisen een co-sign van `STARKE_AUTHORITY`. Die handtekening dekt de hele account-lijst, dus een gebruiker kan die niet zelf aanpassen.

**Geldrisico:** ontstaat alleen als de backend-sleutel gecompromitteerd raakt of door gebruikers opgestelde transacties ongecontroleerd tekent. On-chain is er geen tweede verdedigingslinie.

## 5. Conclusie en advies

- **S-1 is een echte bug in post-audit-code.** De bedoelde kwartaallimiet staat in de code, maar het veld dat hem moet afdwingen wordt nooit geschreven. Het risico is latent (alle live vaults hebben nu 0% fee), maar groot zodra fees aan gaan.
- **S-2** is een bekend, geaccepteerd punt (KS-SRK-F-01) waarvan de impact mogelijk groter is dan beschreven.
- **S-3** is alleen verdediging in de diepte.

**Melden?** S-1 komt in aanmerking voor een vrijblijvende, kosteloze melding aan Starke.

Het security-contact staat in de `security.txt` die in de live bytecode zit: `contact@starke.finance` (plus Discord). De policy staat in `SECURITY.md` in de repo.

Vóór contact:

1. **Verified build:** die is er niet. De bronpaden in de bytecode komen wel volledig overeen met `06558eb`, en `Instruction: MintManagementFees` staat in de bytecode.
2. **TVL-toewijzing:** DeFiLlama noemt de listing "Starke Staked SOL" (URL `/rksol`). De on-chain vaults heten "rkShares …". Of de $1,3M TVL in dít programma zit, of in een apart rkSOL-LST, heb ik niet vastgesteld.
3. **Formulering:** "kwartaallimiet niet afgedwongen, en de fee kan tot 100% gezet worden". Geen exploit of transactie meesturen.
