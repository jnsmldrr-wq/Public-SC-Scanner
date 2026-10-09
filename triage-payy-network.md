# Triage: Payy Network bridge hack (2026-09-24)

- Datum run: 2026-10-09.
- Methode: alleen lezen. Read-only RPC (`eth_getTransactionByHash`, `eth_getCode`,
  `eth_getStorageAt`), keyless Blockscout voor geverifieerde bron, lokale anvil-fork.
  Geen exploit, geen transactie, niets naar mainnet.
- Privilege-filter (CLAUDE.md) toegepast.

## Uitkomst (de kernvraag)

**Nee — noch de statische scanner noch de fuzzer vlagt de daadwerkelijk misbruikte bug.**

De bug is een **soundness-fout in het ZK-bewijssysteem** (de Noir-`agg_agg`-aggregatie­circuit
dwingt de ongebruikte staart van de messages-array niet op nul af), waardoor een prover een
extra, vervalste *burn*-message in een verder geldig aggregaatbewijs kan smokkelen.
`RollupV1.verifyRollup` interpreteert die vervalste burn als echt en betaalt USDC uit.

Classificatie van de miss: **(a) bug in code die onze tool niet leest**, met een sterke
**(c)-component** (ZK-bewijssysteem-soundness valt buiten het bereik van static analysis + invariant-fuzzing).
**Niet (d)** — geen enkel afzonderlijk Solidity-contract bevat, los gelezen, "neem andermans
geld zonder rechten" in een vorm die onze detectoren pakken. De Solidity doet exact wat er staat;
ze vertrouwt een bewijs dat de verifier ten onrechte accepteert.

---

## 1. Identificatie (stap 1)

| Bron | Bevestiging |
|---|---|
| DeFiLlama hacks-API (`api.llama.fi/hacks`) | `name: "Payy Network"`, `date: 1790208000` = **2026-09-24**, chain `Ethereum`, `classification: Bridge & Cross-Chain`, `technique: Bridge Logic Flaw`, `amount: 1 828 589.378132`, `bridgeHack: true`, `language: Solidity` |
| Post-mortem + media (spendnode, cryptoslate, cryptobriefing, gbhackers, unchained, cryptotimes) | Ethereum-bridge van Payy (zk-rollup); invalide burn-proof door de Noir/Barretenberg-verifier als geldig geaccepteerd; ~$1,83M USDC in de eerste burn, in totaal ~$1,92M over twee transacties; opbrengst via Railgun → ~683 ETH |
| On-chain (exploit-tx) | `eth_getTransactionByHash` bevestigt het doel en blok |
| Repo (open source) | `github.com/polybase/payy` — `eth/contracts/rollup3/RollupV1.sol`, `eth/noir/agg_agg.sol` |

DeFiHackLabs heeft (nog) **geen** PoC voor dit incident; identificatie steunt dus op
DeFiLlama + meerdere post-mortems + de on-chain transactie (ruim "ten minste één solide bron").

**Adressen / tx:**

| Rol | Waarde |
|---|---|
| Exploit-tx | `0xf43abdac5422087f645d77923eb1c825178bff3eb86d17d40fa18d89701e1814` |
| Blok exploit | **26044909** (04:21 UTC, 2026-09-24) |
| Afzender (prover-key) | `0x5343b904bf837befb2f5a256b0cd5fbf30503d38` |
| Selector | `0xb8cdbd27` (= `verifyRollup(...)`) |
| Bridge (proxy, `to`) | `0x367c1eaf14aa06b78ce76bd0243297de79d85270` — TransparentUpgradeableProxy |
| Implementatie (RollupV1) | `0x7d8837b547f4fea0053571cb149e845fc58e9b2d` (via EIP-1967-slot) |
| Token | USDC |

## 2. Pin pre-hack state (stap 2)

Fork-blok = **26044908** (het blok vlak vóór de exploit-tx in 26044909). Daarmee krijgen we
de kwetsbare code + state, niet de na de hack gepauzeerde/gepatchte versie.

## 3. Liveness + source-check (stap 3)

- `eth_getCode(0x367c…5270, blok 26044908)` = niet-leeg (~806 bytes, consistent met een minimale
  transparante proxy). **Live op het pin-blok.**
- EIP-1967 implementatieslot op blok 26044908 → `0x7d8837b547f4fea0053571cb149e845fc58e9b2d`.
  Dus de logica op dat blok is **RollupV1**.
- Geverifieerde bron beschikbaar via Blockscout (keyless), compiler `v0.8.20`, 11 bestanden
  (RollupV1 + OpenZeppelin + `IUSDC` + `IVerifier`-interface).
- **Belangrijk:** het eigenlijke verifier-contract (`zkVerifiers[keyHash].verifier`, een apart
  adres) en de `agg_agg`-circuitlogica zitten **niet** in dit bron-bundel. De bridge vertrouwt
  de verifier als black box.

## 4. Pipeline-run (stap 4)

### 4a. Statische scanner (`evm_scan.py`)

Eerste run leverde **geen bruikbaar resultaat**: keyless Blockscout-metadata bevatte de
`viaIR`-vlag niet, waardoor crytic-compile crashte op *"Stack too deep"* en Slither 0 regels zag.
Dat is een **non-resultaat**, geen schone uitslag. (→ tool-gap, zie §6.)

Na handmatig forceren van `--via-ir --optimize --optimize-runs 200` compileert RollupV1 wél en
draait Slither volledig: **61 detector-hits**, waarvan de inhoudelijke:

| Impact | Detector | Waar | Is dit de bug? |
|---|---|---|---|
| Medium | `reentrancy-no-eth` ×5 | `mint`, `mintWithAuthorization`, `verifyBurn`, `substituteBurnTo`, `verifyRollup` | Nee — CEI-volgorde rond een *vertrouwde* USDC-transfer; USDC is niet herintreedbaar |
| Low | `calls-loop` | `executeBurnToAddress` binnen de burn-loop | Nee |
| Low | `shadowing-local` | `initialize(... owner ...)` schaduwt `Ownable.owner()` | Nee |
| Low | `reentrancy-events`/`-benign` | idem mint/rollup | Nee |
| Info/Opt | naming, dead-code, assembly, solc-version, cache-array-length | — | Nee |

Oracle-checks: "Oracle-dekking: nee" — terecht; Payy leest geen externe prijsbron.
`unprotected-sibling` / `missing-access-control`: vuren niet — de waarde-verplaatsende paden
staan achter `onlyProver` / `onlyOwner` / burnSubstitutor-gates.

**Geen van de 61 bevindingen is de misbruikte bug.** De bug staat niet in de Solidity.

### 4b. Fuzzer (`fuzz_scan.py`)

```
[!] contracttype 'unknown' niet ondersteund (lender/vault/amm/token); geef --type op
```

De bridge classificeert als **`unknown`** (geen lender/vault/amm/token/wrapper/mintredeem/queuevault).
Er is geen template voor een zk-rollup-bridge, dus de standaard-invarianten
(SOLVENCY, NO-FREE-WITHDRAW, CONSERVATION, ACCESS) + positieve controle **draaien niet**.

Zelfs mét een bespoke `--type`-template zou de fuzzer dit niet raken: de waarde-uitbetaling
loopt via `verifyRollup`, dat eerst `verifier.verify(aggrProof, publicInputs)` moet laten slagen.
Lokale fuzz-actoren kunnen geen geldig (laat staan subtiel-vervalst) aggregaatbewijs maken op een
fork; `verify` is voor de harnas een black box. De invariant die hier nodig is —
"een geaccepteerd bewijs impliceert dat de messages-array geen ongebonden staart heeft" — is een
**circuit-soundness-eigenschap**, geen contract-invariant.

## 5. Waarom gemist — en zou triage het hebben opgepikt?

**Root cause (uit post-mortem + repo):** in `eth/noir/agg_agg.sol` worden de gecompacteerde
messages naar de publieke messages-lijst doorgezet zónder te bewijzen dat de ongebruikte staart
van de array nul is. Een prover kan daardoor een geldig aggregaatbewijs maken dat ná de
legitieme messages een extra vervalste **burn** bevat. `RollupV1.verifyRollup` (regel 314):

1. `onlyProver` — alleen de prover-key roept het aan;
2. `verifyAllMessages(3, publicInputs, messages_length)` verwerkt de messages (incl. de burn-
   uitbetaling via `executeBurn` → `token.transfer`) op basis van de **publieke inputs**;
3. pas daarna `verifier.verify(aggrProof, publicInputs)`.

De enige wal tegen een oneerlijke prover is dus de **soundness van het bewijs** — en díé wal is lek.

**Zou onze triage het hebben opgepikt?** Nee, en bovendien zou de privilege-filter het juist
**omlaag** halen: het geldpad zit achter `onlyProver` (een vertrouwde co-signer/backend-key) →
label **LAAG** volgens de tabel in CLAUDE.md. De bypass ("bypassable co-signers count as GOLD")
zit hier niet in een ontbrekende `require` maar in de wiskunde van het circuit, en díé bypass is
voor zowel Slither als de fuzzer onzichtbaar. Dat is precies waarom dit géén (d) "should-have-caught-it" is.

**Miss-classificatie:**

- **(a) code die de tool niet leest** — primair. De fout leeft in het Noir-circuit (`agg_agg`) /
  de off-chain prover en het gegenereerde verifier-contract; dat laatste is een apart adres dat
  niet eens in het geverifieerde bron-bundel zat. RollupV1 zelf is correct t.o.v. zijn eigen aannames.
- **(c) buiten huidig bereik** — ZK-bewijssysteem-soundness (ontbrekende range/padding-constraint)
  valt buiten wat een Solidity-static-analyzer of een invariant-fuzzer op een fork kan zien.
- Niet (b) in strikte zin (het is niet "een bestaande invariant net niet geraakt" — er ís geen
  contract-invariant die dit vangt), en **niet (d)**.

## 6. Tool-gaps gevonden tijdens deze run (los van de hack)

1. **`viaIR`-metadata.** Bij keyless Blockscout mist de `viaIR`-vlag, waardoor `viaIR`-gebouwde
   contracten "Stack too deep" geven en de scan stil op 0 bevindingen eindigt. Een
   Etherscan-v2-key levert de exacte metadata (incl. `viaIR`) en lost dit op. Overweeg een
   automatische `--via-ir`-retry bij een "Stack too deep"-compile-fout.
2. **Proxy-resolutie zonder key.** Blockscout gaf `Implementation: None`; de implementatie moest
   handmatig via de EIP-1967-slot. De slot-verificatie zou ook keyless (via de publieke RPC) kunnen.
3. **Geen BSC keyless.** (Opgemerkt bij het eerdere SKYDAO-doel.) Niet relevant voor Payy (eth),
   maar chain 56 heeft geen keyless Blockscout in de map.

---

### Reproductie (read-only)

```bash
# identificatie
curl -s https://api.llama.fi/hacks | grep -i payy
# doel + pin
cast tx 0xf43abdac5422087f645d77923eb1c825178bff3eb86d17d40fa18d89701e1814 --rpc-url https://eth.drpc.org
# static (let op: viaIR nodig zonder key)
python3 evm_scan.py --address 0x7d8837b547f4fea0053571cb149e845fc58e9b2d --chain eth
# fuzz
python3 fuzz_scan.py --address 0x367c1eaf14aa06b78ce76bd0243297de79d85270 --chain eth --name payy_prehack --block 26044908
```
