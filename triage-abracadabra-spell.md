# Triage: Abracadabra Spell (EVM, batch 1)

- Adres: `0x9447c1413da928af354a114954bfc9e6114c5646` = **ConvexStakingWrapperAbra** (0.6.12).
  - Etherscan noemt `0xcc8df73215f3983e84fc9896a0d4740183ebab0c` als implementation. Dat is de clone-template, met dezelfde code; er staat geen proxy-slot.
- Fork? Het is een wrapper rond **Convex** (`ConvexStakingWrapper`, Convex' eigen wrapper-template), met een kleine Abra-laag. De triage richt zich op die Abra-laag (`ConvexStakingWrapperAbra`) en op de gebruikerspaden.
- Datum: 2026-10-05. Read-only.

**Scan (na de detector-fix):** High 4 · Medium 10 · Low 24. Ruwe output: `evm-reports/batch1/abracadabra-spell.*`.

## Oordeel: niks echts

| Melding | Privilege | Oordeel |
|---|---|---|
| `initialize(uint256)` "ontbrekende access control" (eigen detector, eerste run) | — | **Fout-positief.** Er is een guard `require(!isInit, "already init")`. Op mainnet geldt **`isInit() == true`** voor `0x9447…` (read-only `eth_call`). De detector herkende `isInit` niet; dat is gerepareerd. |
| `setRewardRedirect(address)` (eigen detector, eerste run) | — | **Fout-positief.** Hij schrijft alleen `rewardRedirect[msg.sender]`, een instelling voor de eigen account. De detector slaat zulke caller-keyed writes nu over. |
| `unchecked-transfer` in `addRewards()` | GOUD-label | Het gaat om `crv.transfer(address(this), 0)`: een transfer van 0 naar zichzelf, dus geen geld. |
| `reentrancy-eth` in `_calcRewardIntegral` (via withdraw) | GOUD-label | De externe calls gaan naar de reward-tokens van de Convex-pool (CRV/CVX en extra rewards die Convex toevoegt). Een gebruiker kan geen eigen token injecteren. Geen pad voor diefstal gevonden. |
| `unchecked-transfer` (Medium) | LAAG | Alleen voor de owner. |

**Hygiëne (geen geldrisico):** de **clone-template `0xcc8d…` is níet geïnitialiseerd** (`isInit() == false`). Iedereen kan daar `initialize` aanroepen. Dat heeft geen gevolg:
- in de eigen code staat geen `selfdestruct` of `delegatecall`;
- `onlyOwner` gebruikt `IOwner(factory).owner()`, niet `_owner`;
- de template heeft 0 ETH en een `totalSupply` van 0;
- clones hebben hun eigen storage.

Hooguit noemen als hygiëne-tip.
