# Kandidaten voor invariant-fuzzing (uit scan-voortgang.md)

Bron: de 77 eigen-code-protocollen uit `scan-voortgang.md`. Er is geen nieuwe zoektocht gedaan.

**Selectie.** Een protocol komt op de lijst als het:
- een echte geldstroom heeft, met interne boekhouding (vault, lender, AMM, CDP, staking met rewards);
- eigen, live en geverifieerde code heeft.

**Uitgesloten:**
- bridges;
- pure tokens;
- registries, factories zonder eigen rekenwerk en governance/ve-locks;
- wrappers waarvan alle geldfuncties alleen voor een rol zijn: daar kan een
  onbevoegde actor niets fuzzen;
- uitgeschakelde en gesettelde systemen;
- Fira: al opgezet. Die campagne was onvolledig door een RPC-time-out (zie `fuzz-voortgang.md`).

**Rangschikking.** Bovenaan staat een fork met eigen afwijkingen en een echte
geldstroom. Daarna telt mee of het harnas het type al ondersteunt (✓) of dat er
eerst een template nodig is.

| # | protocol | type | fork van | adres (geldcontract) | harnas | waarom geschikt |
|---|---|---|---|---|---|---|
| 1 | **Lista Lending** | lender | Morpho Blue | `0xf820fb4680712cd7263a0d3d024d5b5aea82fd70` (Moolah) | ✓ lender | Morpho-fork met eigen afwijkingen (brokers, providers, whitelists per markt, `minLoan`, eigen `getPrice`), 35 live ETH-markten |
| 2 | **PancakeSwap AMM** | AMM | Uniswap V2 | pair `0x2e8135be71230c6b1b4045696d41c09db0414226` (factory `0x1097…b362`, 8.036 pairs) | ✓ amm | V2-fork met afwijkende fee (0,25%) en protocol-fee; k-, reserve- en conservatie-regels zijn hard te formuleren |
| 3 | **Decentralized Euro** | CDP | Frankencoin | `0x5052d3cc819f53116641e89b96ff4cd1ee80b182` (FPSWrapper; MintingHub/Positions apart) | ✗ CDP-template nodig | Frankencoin-fork: posities, minten tegen collateral, equity-pool; solvabiliteit is precies wat telt |
| 4 | **Equilibria** | staking + rewards | Convex Booster (voor Pendle) | `0x4d32c8ff2facc771ec7efc70d6a8468bc30c26bf` (PendleBooster) | ✗ staking-template | Booster-afgeleide met eigen EQB/xEQB-mint; deposit/withdraw/reward-verdeling over pools |
| 5 | **Gamma** | staking + rewards | Alchemist Geyser v2 / Visor | `0x64fcdd0de44f4bd04c039b0664fb95ef033d4efb` (Hypervisor) | ✗ staking-template | Geyser-fork: stake-units, reward-schedules; "rewards ≤ gefund" en "unstake ≤ stake" |
| 6 | **Saddle Finance** | stableswap-AMM | Curve StableSwap (Solidity-port) | `0xacb83e0633d6605c5001e2ab59ef3c745547c8c7` (SwapFlashLoan) | ✗ stableswap-template | Curve-port met flashLoan; virtual price mag niet dalen en balances moeten de LP-supply dekken |
| 7 | **mStable CDP** | stableswap/basket | eigen (mStable) | `0x945facb997494cc2570096c74b5f66a3507330a1` (MassetBtcV2), FeederPool `0x48c59199…` | ✗ basket-template | Eigen invariant-AMM (mint/redeem/swap in een basket); conservatie en solvabiliteit goed te toetsen |
| 8 | **Abracadabra Spell** | staking-wrapper | Convex StakingWrapper + Abra-laag | `0x9447c1413da928af354a114954bfc9e6114c5646` | ✗ staking-template | Convex-wrapper-fork met eigen Abra-laag; reward-integralen per gebruiker |
| 9 | **Idle** | vault (ERC-4626) | eigen (op IdleCDO) | `0x79f05f75df6c156b2b98ac1fbfb3637fc1e6f048` (TrancheWrapper) | ✓ vault | 4626-wrapper rond tranches; share/asset-omrekening met tranche-prijs |
| 10 | **NaraUSD** | mint/redeem (stable) | eigen | `0x5c6263904ccfd3bcf1aaa6e7063ddd29743b3bb7` + MultiCollateralToken | ✗ mint/redeem-template | Multi-collateral mint en redeem-silo; "uitgegeven ≤ gedekt" |
| 11 | **Origin Dollar** | mint/redeem (rebasing) | eigen | `0xe75d77b1865ae93c7eaa3040b038d7aa7bc02f70` (OUSDVault) | ✗ mint/redeem-template | Rebasing-supply versus vault-backing (USDC 1:1); rebase- en redeem-boekhouding |
| 12 | **InceptionLRT** | LRT-vault | eigen | `0x814cc6b8fd2555845541fb843f37418b05977d8d` (InVault_E1) | ✗ LRT-template | deposit/redeem tegen een ratio en een flash-withdraw-capaciteit |
| 13 | **Eigenpie** | LRT-staking | eigen | `0x24db6717db1c75b9db6ea47164d8730b63875db7` (EigenpieStaking) + WithdrawManager | ✗ LRT-template | Mint tegen exchange-rate, opname via schedules |
| 14 | **Native Credit Pool** | LP-vault | eigen | `0xe3d41d19564922c9952f692c5dd0563030f5f2ef` (CreditVault/NativeLPToken) | ✗ (4626-achtig) | LP-token deposit/redeem met exchange-rate; settle en liquidate zijn privileged |
| 15 | **Llama Airforce** | vault + harvest | eigen | `0x83507cc8c8b67ed48badd1f59f684d5d02884c81` (UnionVault) | ✗ (niet-4626 vault) | deposit/withdraw/harvest met fees; kleine TVL |
| 16 | **Origin ARM** | redemption-AMM | eigen | `0x6bac785889a4127db0e0cefee88e0a9f1aaf3cc7` (OriginARM) | ✗ ARM-template | Swaps tegen operator-prijzen plus LP-deposits en een redeem-queue |
| 17 | **LUSD ChickenBonds** | bonding | eigen (Liquity-team) | `0x57619fe9c539f890b19c61812226f9703ce37137` | ✗ bonding-template | Bucket-boekhouding (pending/reserve/permanent) als harde invariant |
| 18 | **Frax Swap** | mint/redeem (FPI) | eigen | `0x2397321b301b80a1c0911d6f9ed4b6033d43cf51` (FPIControllerPool) | ✗ mint/redeem-template | mint/redeem tegen CPI-peg met fees en caps; ~620k FRAX in het contract |
| 19 | **NFTX** | NFT-vault | eigen | vault-impl `0x0fa0fd98727c443dd5275774c44d27cff9d279ed` (868 vaults) | ✗ NFT-template | "supply vToken = #NFT's × 1e18" is een harde invariant |
| 20 | **Compound V1** | lender | eigen (origineel) | `0x3fda67f7583380e67ef93072294a7fac882fd7e7` (MoneyMarket) | ✗ legacy-lender | Legacy-lender met echte saldi; supply en borrow onder één contract |
| 21 | **Aave V1** | lender | eigen (origineel) | `0x3dfd23a6c5e8bbcfc9581d2e864a68feb6a076d3` (LendingPoolCore) | ✗ legacy-lender | Reserve-boekhouding (liquidity, borrows, aTokens) |
| 22 | **Bancor V3** | AMM | eigen | `0x649765821d9f64198c905ec0b2b037a4a52bc373` (MasterVault) | ✗ AMM-template | Pool-collection met single-sided liquiditeit; master-vault-solvabiliteit |
| 23 | **DODO AMM** | PMM-AMM | eigen (origineel) | DVM-pools via `0x72d220ce168c4f361dd4dee5d826a01ad8598f6c` | ✗ PMM-template | PMM-curve; reserves ≤ balances en conservatie |
| 24 | **Saffron Vaults** | split-vault | eigen | `0x84f0c6e5a7ea3bd89249f26a72b6e624344944dd` (UniV3Vault) | ✗ | fixed- en variable-kant op een UniV3-positie |
| 25 | **Gnosis Protocol v1** | escrow (CTF) | eigen | `0xc59b0e4de5f1248c1140964e0ff287b192407e0c` | ✗ CTF-template | split/merge: "collateral = som van outcome-posities" |
| 26 | **Panoptic V2** | options-AMM | eigen | `0x0000000000000c51d0f8cf4bd9ade7191372a625` | ✗ (complex) | CollateralTracker (4626-achtig) is fuzzbaar; positie-logica zwaar |
| 27 | **Opyn Gamma** | options-margin | eigen | `0x4ccc2339f87f6c59c6893e1a678c2266ca58dc72` (Controller) | ✗ (complex) | naked-margin-boekhouding, live (zie `triage-opyn-gamma.md`) |
| 28 | **Ribbon / Ribbon Earn** | options-vault | eigen | `0xdd9d1b7d…`, `0x84c2b16f…` | ✗ (keeper-rondes) | round-boekhouding; veel stappen zijn keeper-gedreven, dus beperkt user-fuzzbaar |
| 29 | **Pirex** | staking/redemption | eigen | `0x35a398425d9f1029021a92bc3d2557d42c8588d7` (PirexCvx) | ✗ | deposit en redeem met epochs en futures |
| 30 | **Latch** | deposit-pool | eigen | `0xfe606eec8eb8e6ad8e8654968a15650f5331a023` | ✗ | deposit/withdraw-boekhouding |

## Niet geschikt (kort)

| categorie | protocollen |
|---|---|
| Bridges | Allbridge, Blast Bridge, deBridge, Morph, Orderly Bridge, Multichain |
| Tokens | Aurus, Asymmetry (Ankr aETH), Digital Gold, Dinero, GAIB, Gro, KUMA, Baseline |
| Registries, factories en ve/governance | B.Protocol, Bancor V2.1, Flex, Arrakis-factory (vaults apart), Aera-factory, Angle-veANGLE, Bio-veBIO, Keep3r, Outcome (UMA-template), mStable V2, Ensuro, Royco-entrypoint |
| Alleen rol-gated geldfuncties | King (onlyDepositors), Nucleus (enter/exit requiresAuth), Flying Tulip, Brickken (escrow per rol) |
| Uitgeschakeld of gesettled | MCDEX (SETTLED), Easedefi arNXM (deposit/withdraw uit) |
| Anders | Fake World Assets (NFT-loterij, VRF), FermiSwap (RFQ met MM-vault), Punks Terminal (signed bids), IDEX (signed orders), Angstrom (UniV4-hook), Contango (derivaten via externe venues), Blast pre-launch farm, Api3, Katana (Vyper/Yearn) |
