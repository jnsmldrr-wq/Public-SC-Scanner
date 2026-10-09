# Triage: Quarry

- Repo: https://github.com/QuarryProtocol/quarry.
- Datum: 2026-10-04.
- Methode: alleen lezen, read-only RPC. Geen exploit, geen transactie.

## 1. Livecheck: welke programma's draaien live?

| Programma | Program ID | Mainnet | Laatste deploy | Upgrade authority |
|---|---|---|---|---|
| quarry-mine | `QMNeHCGYnLVDn1icRAfQZpjPLBNkfGbSKRB83G5d8KB` | LIVE | 2022-08-08 17:44 UTC (slot 145136845) | `6Jtj2TDynyyZWkwY5MjWqYqhkQztAdvNFra1HW1BZmKR` |
| quarry-merge-mine | `QMMD16kjauP5knBwxNUJRZ1Z5o3deBuFrqVjBVmmqto` | LIVE | 2022-04-19 18:50 UTC | idem |
| quarry-mint-wrapper | `QMWoBmAyJLAsA1Lh9ugMTw2gciTihncciphzdNzdZYV` | LIVE | 2022-04-19 18:52 UTC | idem |
| quarry-operator | `QoP6NfrQbaGnccXQrMLUkog2tQZ4C1RFgJcwDnT8Kmz` | LIVE | 2022-04-19 18:53 UTC | idem |
| quarry-registry | `QREGBnEj9Sa5uR91AV8u3FxThgP5ZCvdZUW2bHAkfNc` | LIVE | 2022-04-19 18:54 UTC | idem |
| quarry-redeemer | `QRDxhMw1P2NEfiw5mYXG79bwfgHTdasY2xNP76XSea9` | LIVE | 2022-04-19 18:57 UTC | idem |

Alle zes zijn live, nog steeds upgradebaar, en geen ervan is verified (OtterSec).

## 2. Welke versie ik heb gescand, en waarom

- HEAD is `df6a75a` = **v5.3.0** (2022-09-28). Die is **niet** gedeployd: de laatste deploy is van 2022-08-08.
- **quarry-mine** is gedeployd op 2022-08-08. Dat past bij **v5.2.0** (`f41219d`, 2022-07-27), de laatste release vóór de deploy.
- **De andere vijf** zijn gedeployd op 2022-04-19. Dat past bij **v5.0.2** (`2e4b5ec`, 2022-04-17).
- **Ik heb `v5.2.0` (`f41219d`) gescand**, via een git worktree (`shortlist/quarry-v5.2.0`). Dat is correct voor alle zes, omdat:
  - de `src/` van merge-mine, mint-wrapper, operator, registry en redeemer **identiek** is tussen v5.0.2 en v5.2.0 (`git diff` leeg);
  - de `src/` van alle programma's ook identiek is tussen v5.2.0 en v5.3.0/HEAD. v5.3.0 wijzigde geen programmacode.
- **Voorbehoud:** de builds zijn niet verified. Dat de bytecode overeenkomt met deze tags volgt alleen uit de datums, niet uit een hash.

## 3. Scan

`scan.py` op `programs/` gaf 1 Critical, 22 High, 1 Medium, 63 meldingen in totaal (`quarry-report.md` / `.json`).

## 4. Triage van elke CRITICAL/HIGH/MEDIUM

| Melding | Oordeel |
|---|---|
| **SOL-CFG-201** (×5) | **Klopt.** Noch de workspace-`Cargo.toml` noch een programma-`Cargo.toml` zet `overflow-checks = true`. Ik heb daarom alle productiecode (zonder `#[cfg(test)]`) handmatig nagelopen op `+ - * /`. Alle rekenwerk op bedragen gebruikt `checked_*`/`U192` met `unwrap_int!`. Raw arithmetic komt alleen voor in compile-time `LEN`-constanten, in `rewards_upperbound + 1` (U192, dat bij overflow panict) en in `32 * max_quarries` in de registry (zie I-3). **Geen exploiteerbare gevolgen.** |
| SOL-AUTH-001 / OWNER-002 `quarry-mine/src/lib.rs:402` `new_pause_authority` | Dit is alleen een pubkey die wordt opgeslagen. De instructie vereist `MutableRewarderWithAuthority` (signer = `rewarder.authority`). Geen risico. |
| SOL-OWNER-002 `unused_*`, `initial_authority`, `admin`, `next_admin`, `new_minter_authority`, `delegate`, `owner` | Allemaal accounts die alleen als pubkey worden opgeslagen of ongebruikt zijn. Alle beveiligde paden controleren signer + `assert_keys_eq` in `account_validators.rs`. Geen risico. |
| SOL-ARITH-101 `quarry.rs:154`, `:331`; SOL-ARITH-104 `rewarder.rs:120` | Staan in `#[cfg(test)] mod tests` (vanaf `quarry.rs:90` en `rewarder.rs:45`). Fout-positief. |

## 5. De punten waar je specifiek naar vroeg

**Rewards-berekening (`payroll.rs`):**

- Het model is dat van Synthetix StakingRewards: `rewards_per_token += Δt · rate · 2⁶⁴ / jaar / total_staked`.
- Alles is in U192 met checked math. Afronding gaat naar beneden, dus in het voordeel van het protocol.
- `sanity_check` legt een bovengrens op wat geclaimd kan worden.
- **Dubbel claimen:** onmogelijk. `rewards_earned` wordt op 0 gezet vóór de mint (`claim_rewards_v2.rs:41`), en `rewards_per_token_paid` wordt bij elke update gelijkgezet.
- **Volgorde bij stake en unstake:** de rewards worden eerst bijgewerkt en daarna verandert het saldo (`quarry.rs:72`). Dat is de juiste volgorde.

**Boekhouding van staking en unstaking:**

- `miner.balance` en `quarry.total_tokens_deposited` worden in dezelfde stap aangepast, met `checked_add`/`checked_sub` (`quarry.rs:74-83`).
- Bij withdraw geldt ook `amount <= miner_vault.amount`.
- Merge-mine houdt `primary_balance == miner.balance` aan als post-check. Primary tokens kunnen alleen worden opgenomen als `replica_balance == 0`, en replica-mints kunnen niet worden opgenomen (`account_validators.rs:66-78`).

**Wie mag rewards-parameters of de mint-wrapper aanpassen?**

- **Rewarder-functies:** `set_annual_rewards`, `set_rewards_share`, `set_famine` en `create_quarry` vereisen signer = `rewarder.authority`. Een authority-overdracht verloopt in twee stappen.
- **Mint-wrapper:**
  - `minter_update` is alleen voor de admin.
  - `perform_mint` vereist signer = `minter.minter_authority` (de rewarder-PDA via CPI) en een allowance, met een hard cap op de supply.
  - Claims controleren mint-wrapper, minter en mint-authority tegen de rewarder (`claim_rewards_v2.rs:165-189`).

**Kan een miner-account of quarry vervalst of hergebruikt worden?**

- Het zijn allemaal `Account<T>` (eigenaar en discriminator gecontroleerd), en de relaties worden expliciet gecontroleerd: `miner.quarry == quarry` en `quarry.rewarder == rewarder`.
- De miner-vault moet bij aanmaak eigendom van de miner-PDA zijn, met de juiste mint, **zonder delegate en zonder close authority** (`create_miner.rs:77-80`). Een vooraf aangemaakte vault met een delegate van de aanvaller wordt dus geweigerd.
- `rescue_tokens` weigert de echte vault.
- De verouderde v1-instructies (`claim_rewards`) hebben identieke validatie en claimlogica als v2.

## 6. Code ná de audit

- Laatste audit: Soteria (2022-03-29); daarvoor Quantstamp (2021-12).
- Tot v5.2.0 is er ~1.100/640 regels in `quarry-mine/src` veranderd en ~440/280 in de andere programma's.
- Het meeste daarvan is herstructurering: v2-instructies, handlers naar `instructions/` verplaatst, `security_txt`. Er zijn ook **extra** constraints bijgekomen (merge-mine `has_one`, redeemer `destination != vault`).
- De enige echte gedragswijziging is **#562 "Fix set_rewards_share"** (2022-07-23):
  - De **geaudite** versie zette bij `set_rewards_share` `last_update_ts = now` zonder eerst `rewards_per_token_stored` bij te werken. Daardoor verloren stakers de opgebouwde rewards. Dat was een echte bug in de geaudite code, en hij is gerepareerd vóór de mine-deploy van 2022-08-08.
  - De fix introduceert punt Q-1 hieronder.

## 7. Echte kandidaten

**Niks gevonden waarmee een buitenstaander gestakete LP-tokens kan stelen of ongelimiteerd rewards kan claimen.**

Er is één punt met beperkt geldrisico en twee informatieve punten:

### Q-1 (laag): permissionless `update_quarry_rewards` tijdens een share-wijziging zet een te hoge rate vast. **POST-AUDIT** (#562)
`programs/quarry-mine/src/lib.rs:169-192` (`set_rewards_share`) en `:203-218` (`update_quarry_rewards`)

- **Wat er misgaat:** sinds #562 past `set_rewards_share` alleen `total_rewards_shares` en `quarry.rewards_share` aan. De rate van elke quarry wordt pas bijgewerkt bij `update_quarry_rewards`, en die kan iedereen aanroepen.
- **Concreet voorbeeld:**
  - Uitgangssituatie: A=50, B=50, totaal 100.
  - De admin wil B naar 25 en een nieuwe quarry C naar 25, en doet dat in twee transacties.
  - Na tx 1 is het totaal 75. Iemand die in A staket roept `update_quarry_rewards(A)` aan.
  - De rate van A wordt dan 50/75 = 66,7% van de jaarlijkse rewards in plaats van 50%.
  - Als de admin daarna alleen B en C bijwerkt (de quarries die hij wijzigde), blijft A te veel uitkeren tot iemand A opnieuw bijwerkt.
- **De ontwikkelaars weten dit:** het staat als `TODO` in de code (`lib.rs:184-186`).
- **Geldrisico:** extra minting van het reward-token, begrensd door de allowance van de minter en de hard cap. Dat is verwatering van de reward-token, niet het stelen van gestakete LP-tokens.
- **Vereist een admin-actie** in meerdere transacties zonder dat daarna alle quarries worden bijgewerkt.

### Q-2 (informatief): `set_famine` legt de opgebouwde rewards niet eerst vast. Oorspronkelijk geaudite code.
`programs/quarry-mine/src/lib.rs:194-200`

- Als de famine-datum al voorbij is en de admin hem later verlengt, betaalt de volgende update met terugwerkende kracht rewards uit over de periode waarin geen rewards hadden mogen lopen.
- Dat gebeurt omdat `last_update_ts` nog op het oude punt staat.
- Alleen de admin kan dit in gang zetten.

### Q-3 (informatief): de grootte van het registry-account gebruikt u16-rekenkunde zonder overflow-checks. Oorspronkelijk geaudite code.
`programs/quarry-registry/src/lib.rs:73` (`32 * max_quarries`, u16)

- Bij `max_quarries ≥ 2048` loopt de waarde over, waardoor er te weinig ruimte wordt gereserveerd.
- Het registry is per rewarder een PDA die iedereen kan aanmaken. Iemand kan het dus vooraf met een te kleine capaciteit aanmaken en zo blokkeren. Dat kan ook zonder overflow (`max_quarries = 1`).
- Het registry is alleen een lijst, er zit geen geld in.

## Conclusie

Geen melding met risico voor gebruikersgeld.

- Het staking- en rewardsdeel is degelijk: checked math overal, en strikte account-relaties.
- Het ontbreken van `overflow-checks` is een echte configuratiefout, maar heeft geen effect, omdat er geen ongecontroleerde rekenkunde op bedragen is.
- Q-1 is het enige punt in post-audit-code met een (beperkt) geldeffect, en het team kent het al (TODO).

Hooguit kun je Q-1 en het ontbreken van `overflow-checks` als vrijblijvende opmerking aan `team@quarry.so` sturen (adres uit hun `security_txt`). Controleer vóór contact wel of de bytecode overeenkomt met de code, want de builds zijn niet verified.
