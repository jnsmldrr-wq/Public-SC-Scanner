# Triage: Allbridge Classic (EVM, batch 1)

- Adres: `0xbbbd1bbb4f9b936c3604906d7592a644071de884` = **Bridge** (0.8.9, optimizer uit). Geen proxy. Het bestand bevat ook het `Staking`-contract (ABR).
- Fork? Nee, eigen code.
- Datum: 2026-10-05. Read-only.

**Scan:** High 2 · Medium 3 · Low 3 (14 verlaagd: validator/admin). Ruwe output: `evm-reports/batch1/allbridge-classic.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| 2× `unchecked-transfer` in `Staking.deposit/withdraw` (`Bridge.sol:1335/1345`) | GOUD-label | **Fout-positief.** Het gaat om `ABR.transferFrom` en `ABR.transfer` op de eigen ABR-token, een standaard ERC-20 die bij een fout revert. Geen niet-gecontroleerd faalpad. |
| `incorrect-equality` | GOUD-label | Een strikte vergelijking, zonder pad waarmee een aanvaller geld onttrekt. |
| `arbitrary-send-eth`, `reentrancy-eth` (Medium) | LAAG | Alleen in validator- of beheerfuncties (`unlock`/administratie). |

De beveiliging van de bridge rust op validator-handtekeningen. Dat is een vertrouwensmodel en valt buiten het privilege-filter (LAAG).
