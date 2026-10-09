# Scan-voortgang (EVM, EIGEN CODE uit evm-inventaris-ethereum.md)

Volgorde: alfabetisch op protocolnaam, alleen status EIGEN CODE uit `shortlist/evm-eth/results.json`.
Een protocol staat hier zodra zijn batch gestart is; status `gescand` = triage-bestand geschreven.

| # | protocol | batch | status | adres (scan) | triage |
|---|---|---|---|---|---|
| 1 | Aave V1 | 1 | gescand | 0x3dfd23a6c5e8bbcfc9581d2e864a68feb6a076d3 | [triage-aave-v1.md](triage-aave-v1.md) |
| 2 | Abracadabra Spell | 1 | gescand | 0x9447c1413da928af354a114954bfc9e6114c5646 | [triage-abracadabra-spell.md](triage-abracadabra-spell.md) |
| 3 | Aera V3 | 1 | gescand | 0x29722cc9a1cacff4a15914f9bc274b46f3b90b4f | [triage-aera-v3.md](triage-aera-v3.md) |
| 4 | Allbridge Classic | 1 | gescand | 0xbbbd1bbb4f9b936c3604906d7592a644071de884 | [triage-allbridge-classic.md](triage-allbridge-classic.md) |
| 5 | Angle | 1 | gescand | 0x0c462dbb9ec8cd1630f1728b2cfd2769d09f0dd5 | [triage-angle.md](triage-angle.md) |
| 6 | Api3 | — | overgeslagen (Gnosis Safe `SafeProxy → Safe`: multisig, geen protocollogica) | 0x5a9aa3219dd1cbef6a18fd221464e071df2677c2 | |
| 7 | Angstrom | 2 | gescand | 0x0000000aa232009084bd71a5797d089aa4edfad4 | [triage-angstrom.md](triage-angstrom.md) |
| 8 | Anvil | 2 | gescand | 0x5d2725fde4d7aa3388da4519ac0449cc031d675f | [triage-anvil.md](triage-anvil.md) |
| 9 | Arrakis V1 | 2 | gescand | 0xea1aff9dbffd1580f6b81a3ad3589e66652db7d9 | [triage-arrakis-v1.md](triage-arrakis-v1.md) |
| 10 | Asymmetry Finance | 2 | gescand | 0xe95a203b1a91a908f9b9ce46459d101078c2c3cb | [triage-asymmetry-finance.md](triage-asymmetry-finance.md) |
| 11 | Aurus | 2 | gescand | 0xe4a6f23fb9e00fca037aa0ea0a6954de0a6c53bf | [triage-aurus.md](triage-aurus.md) |
| 12 | B.Protocol | — | N.V.T. — geen eigen logica (alleen TVL-lezer (view)) | 0x60312e01a2acd1dac68838c949c1d20c609b20cf | |
| 13 | Bancor V2.1 | — | N.V.T. — geen eigen logica (alleen adresregister, geen waardebeweging) | 0x52ae12abe5d8bd778bd5397f99ca900624cfadd4 | |
| 14 | Bancor V3 | 3 | gescand — niks | 0x649765821d9f64198c905ec0b2b037a4a52bc373 | |
| 15 | Baseline Protocol | — | N.V.T. — geen eigen logica (kale token, geen eigen functies) | 0x9fdbde76236998dc2836fe67a9954ede456a1d63 | |
| 16 | Bio Protocol | 3 | gescand — niks | 0xf91a12742aa609d41513a137d3c36b749f56f40c | |
| 17 | Blast Bridge | 3 | gescand — niks | 0xa230285d5683c74935ad14c446e137c8c8828438 | |
| 18 | Blast pre-launch Farm | 3 | gescand — niks | 0x5f6ae08b8aeb7078cf2f96afb089d7c9f51da47d | |
| 19 | Brickken | 3 | gescand — oracle-gat (slapend: 0/52 escrows met oracle → laag, zie brickken-oracle-onderbouwing.md) | 0x91af681c85ca98efc5d69c1b62e6f435030969db | [triage-brickken.md](triage-brickken.md) |
| 20 | Compound V1 | 3 | gescand — niks | 0x3fda67f7583380e67ef93072294a7fac882fd7e7 | |
| 21 | Contango V2 | 3 | gescand — niks | 0x6cae28b3d09d8f8fc74ccd496ac986fc84c0c24e | |
| 22 | deBridge | 3 | gescand — niks | 0x43de2d77bf8027e25dbd179b491e8d64f38398aa | |
| 23 | Decentralized Euro | 3 | gescand — niks | 0x5052d3cc819f53116641e89b96ff4cd1ee80b182 | |
| 24 | Digital Gold | — | N.V.T. — geen eigen logica (token-only (pausable/blacklist)) | 0xa9299c296d7830a99414d1e5546f5171fa01e9c8 | |
| 25 | Dinero (pxETH) | — | N.V.T. — geen eigen logica (token-only) | 0x04c154b66cb340f3ae24111cc767e0184ed00cc6 | |
| 26 | DODO AMM | 3 | gescand — niks | 0x72d220ce168c4f361dd4dee5d826a01ad8598f6c | |
| 27 | Easedefi.org | 4 | gescand — niks (TVL-adres NXMToken = Nexus-token; gescand: arNXMVault achter OwnedUpgradeabilityProxy 0x1337def1…, impl bevestigd via implementation(); deposit/withdraw uitgeschakeld, waardefuncties onlyOwner) | 0xc38bfa29f70b3f0f40784d7861f1665e47f37f2e | |
| 28 | Eigenpie | 4 | gescand — niks (EigenpieConfig + EigenpieStaking + EigenpieWithdrawManager; withdraw-paden nonReentrant, per-user state; wisselkoers via PriceProvider-rol) | 0x24db6717db1c75b9db6ea47164d8730b63875db7 | |
| 29 | Ensuro | — | N.V.T. — geen eigen logica in adapter-adressen (USDO/OpenEden, Aave aToken, Compound Comet, MetaMorpho = externe protocollen) | 0x8238884ec9668ef77b90c6dff4d1a9f4f4823bfe | |
| 30 | Equilibria | 4 | gescand — niks (Convex-Booster-afgeleide voor Pendle; rewardPool owner-gezet, rewardClaimed met !auth) | 0x4d32c8ff2facc771ec7efc70d6a8468bc30c26bf | |
| 31 | Fake World Assets V2 | 4 | gescand — niks; oracle: ok (floor-oracle met maxOracleAge + challenge-periode) | 0x958c41181182e76f221331b2755b77d9e1426a98 | |
| 32 | FermiSwap | 4 | gescand — niks (transferFrom-bron = vaste traderVault of msg.sender; callback met balanscheck) | 0xb1076fe3ab5e28005c7c323bac5ac06a680d452e | |
| 33 | Fira | 4 | gescand — niks; oracle: ok (USLLendingMarket = Morpho-Blue-fork; afwijkingen createMarket/post-maturity-liquidatie zijn rol-gated; oracle = zelfde feed als base én quote → vast 1:1) | 0xa428723ee8ffd87088c36121d72100b43f11fb6a | |
| 34 | Flex | — | N.V.T. — geen eigen logica (Registry: alleen endorse/unendorse; echte logica in Vyper-TroveManagers, buiten Slither-pipeline) | 0x9117440a7d03238905d1c8908157bd7a547c77c8 | |
| 35 | Flying Tulip Lend | 4 | gescand — niks (ftYieldWrapper; alle waardefuncties rol-gated, setters met eigen msg.sender-check) | 0x7127bb9d9ad0f47b8da9087e634d67f3946f840e | |
| 36 | Frax Swap | 4 | gescand — niks; oracle: ok (FPIControllerPool; 'Chainlink'-feed = UniV3-TWAP-adapter 300s die updatedAt=block.timestamp geeft, alleen peg-band-gate; uitbetaling volgt CPI-peg; spot-functie alleen in uitgecommentarieerde code) | 0x2397321b301b80a1c0911d6f9ed4b6033d43cf51 | |
| 37 | GAIB | — | N.V.T. — token-only (AID: rol-gated mint/burn + standaard flashMint met burn in dezelfde call; gecontroleerd) | 0x18f52b3fb465118731d9e0d276d4eb3599d57596 | |
| 38 | Gamma | 4 | gescand — niks (Hypervisor = Visor/Alchemist-Geyser-v2-afgeleide; findings in views/pure) | 0x64fcdd0de44f4bd04c039b0664fb95ef033d4efb | |
| 39 | Gnosis Protocol v1 | 4 | gescand — niks (ConditionalTokens; alleen Low) | 0xc59b0e4de5f1248c1140964e0ff287b192407e0c | |
| 40 | Gro | — | N.V.T. — token-only (NonRebasingGToken: mint/burn via controller/whitelist; GToken-waarde elders) | 0x3adb04e127b9c0a5d36094125669d4603ac52a0c | |
| 41 | IDEX Classic | 5 | gescand — niks (Exchange + Custodian; transferFrom-bron = msg.sender; withdraw/trade via signed orders + dispatcher) | 0xa36972e347e538e6c7afb9f44fb10dda7bba9ba2 | |
| 42 | Idle | 5 | gescand — niks (TrancheWrapper → IdleCDO-code; reentrancy-meldingen achter nonReentrant/_checkSameTx (bewust tx.origin-anti-flash)) | 0x79f05f75df6c156b2b98ac1fbfb3637fc1e6f048 | |
| 43 | InceptionLRT (Isolated Restaking) | 5 | gescand — niks (InVault_E1 + InceptionVault_EL, impl via EIP-1967 bevestigd; claim/updateEpoch bewust permissionless naar vault; uninitialized-state = proxy-storage) | 0x814cc6b8fd2555845541fb843f37418b05977d8d | |
| 44 | Katana Pre-Launch | — | N.V.T. — Vyper / standaard Yearn V3 Vault (geen eigen logica, buiten Slither-pipeline) | 0xf470eb50b4a60c9b069f7fd6032532b8f5cc014d | |
| 45 | Keep3r Network | 5 | gescand — niks (Keep3r V2; FullMath-exp en _period = bekende FP's) | 0xeb02addcfd8b773a5ffa6b9d1fe99c566f8c44cc | |
| 46 | King Protocol | 5 | gescand — niks; oracle: ok (LRTSquaredCore; prijs alleen in onlyDepositors-deposit (LAAG), redeem pro-rata in natura zonder prijs) | 0x8f08b70456eb22f6109f57b8fafe862ed28e6040 | |
| 47 | KUMA Protocol | — | N.V.T. — token-only (KIBToken: rol-gated mint/burn + yield-index; obligatie-logica in KUMASwap, niet in adapter) | 0x01bf66becdcfd6d59a5ca18869f494fea086cdfd | |
| 48 | Latch | 5 | gescand — niks (DepositPool) | 0xfe606eec8eb8e6ad8e8654968a15650f5331a023 | |
| 49 | LendFlare | — | N.V.T. — geen eigen logica in adapter-adres (VirtualBalanceWrapper: owner-only boekhouding, houdt geen fondsen) | 0x10a377ba353cd480e43800018a27742054904c1a | |
| 50 | Lista Lending | 5 | gescand — niks; oracle: ok (Moolah = Morpho-fork; 35 ETH-markten: ResilientOracle/SmartProvider/LendingBroker/PT-lineair; SmartProvider-LP-prijs via get_virtual_price met reentrancy-guard) | 0xf820fb4680712cd7263a0d3d024d5b5aea82fd70 | |
| 51 | Llama Airforce | 5 | gescand — niks materieel (UnionVault; publieke harvest met min_out=0 = bekend patroon, waarde verwaarloosbaar: ~54k cvxCRV TVL, geen harvest sinds blok 22M) → laag | 0x83507cc8c8b67ed48badd1f59f684d5d02884c81 | |
| 52 | LUSD ChickenBonds | 5 | gescand — niks (ChickenBondManager; unchecked-transfer op LUSD (revert-token) = FP) | 0x57619fe9c539f890b19c61812226f9703ce37137 | |
| 53 | MCDEX | 5 | gescand — niks (Perpetual v1 status SETTLED: alleen settle() van eigen account tegen vaste settlementPrice; oracle-pad uit) | 0x220a9f0dd581cbc58fcfb907de0454cbf3777f76 | |
| 54 | Morph Bridge | 6 | gescand — niks (L1CrossDomainMessenger, Scroll-stijl; relay met finalizedWithdrawals + notInExecution-guard; uninitialized-state = proxy-storage) | 0xdc71366effa760804dcfc3edf87fa2a6f1623304 | |
| 55 | mStable CDP | 6 | gescand — niks (MassetBtcV2 + FeederPool; transferReturnBalance-bron = msg.sender; migrateBassets governor-only; geen externe prijsbron) | 0x945facb997494cc2570096c74b5f66a3507330a1 | |
| 56 | mStable V2 | — | N.V.T. — geen eigen logica in adapter-adressen (dHEDGE PoolFactory, Gnosis Safe, Aave V3 Pool = externe protocollen) | 0x96d33bcf84dde326014248e2896f79bbb9c13d6d | |
| 57 | Multichain | 6 | gescand — niks materieel (adres = GeoDB BscBridge, niet Multichain-code; isSigners zonder uniciteitscheck + hash zonder contract/chainId → één signer kan alleen tekenen (LAAG); ~1.300 GEO, inactief sinds blok 13.0M) | 0xc342774492b54ce5f8ac662113ed702fc1b34972 | |
| 58 | NaraUSD | 6 | gescand — niks (NaraUSD + MultiCollateralToken; meldingen = AccessControl-storage-FP's; redeem-silo onlyVault) | 0x5c6263904ccfd3bcf1aaa6e7063ddd29743b3bb7 | |
| 59 | Native Credit Pool | 6 | gescand — niks (CreditVault + NativeLPToken; settle/liquidate/removeCollateral rol-gated) | 0xe3d41d19564922c9952f692c5dd0563030f5f2ef | |
| 60 | NEMO Trading | 6 | gescand — niks (TokenizedVault; mulDiv/datum-math = FP's; claims/fees rol-gated) | 0x955256b31097ddf47a9e47a95adfdfb4460d8522 | |
| 61 | NFTX | 6 | gescand — niks (VaultFactory = beacon, 868 vaults; vault-impl NFTXVaultUpgradeable 0x0fa0fd98… gescand) | 0xbe86f647b167567525ccaafcd6f881f1ee558216 | |
| 62 | Nucleus | 6 | gescand — niks (standaard Veda BoringVault; enter/exit requiresAuth, user-pad via Teller) | 0x52e4d8989fa8b3e1c06696e7b16def5d7707a0d1 | |
| 63 | NUVA | 6 | gescand — niks (DedicatedVaultRouter, impl via EIP-1967 bevestigd) | 0x50ae1e4a612a4623b747aeefb30afba82804e12c | |
| 64 | Orderly Bridge | 6 | gescand — niks (Vault; rebalance/broker-functies onlyCrossChainManager (LAAG)) | 0x816f722424b49cf1275cc86da9840fbd5a6167e9 | |
| 65 | Opyn Gamma | 7 | gescand — oracle-gat ACTIEF pad, impact laag: ChainLinkPricer.getPrice() zonder updatedAt-check gebruikt in naked-margin-berekening (naked pool ≈188,9 WETH + 3.100 USDC); liquidatie/settlement wél beschermd → [triage-opyn-gamma.md] | 0x4ccc2339f87f6c59c6893e1a678c2266ca58dc72 | [triage-opyn-gamma.md](triage-opyn-gamma.md) |
| 66 | Origin ARM | 7 | gescand — niks (OriginARM + LidoARM; swapprijzen door operator gezet (LAAG); 'uninitialized-state' = immutables, transferFrom-bron = msg.sender) | 0x6bac785889a4127db0e0cefee88e0a9f1aaf3cc7 |  |
| 67 | Origin Dollar | 7 | gescand — niks (OUSDVault is nu single-asset USDC 1:1 via scaleBy, geen oracle meer) | 0xe75d77b1865ae93c7eaa3040b038d7aa7bc02f70 |  |
| 68 | Outcome Finance | — | N.V.T. — standaard UMA LongShortPair-template (Creator + LSP = UMA-code; prijs via UMA Optimistic Oracle) | 0x0b8de441b26e36f461b2748919ed71f50593a67b |  |
| 69 | PancakeSwap AMM | 7 | gescand — niks (Uniswap-V2-fork; PancakePair 0x2e8135be…, 8.036 pairs; weak-prng = timestamp-mod FP) | 0x1097053fd2ea711dad45caccc45eff7548fcb362 |  |
| 70 | Panoptic V2 | 7 | gescand — niks; oracle: ok (FactoryV3/V4-bron incl. PanopticPool/CollateralTracker/SFPM; callbacks checken poolManager/pool; solvency via eigen oracle-ticks + MAX_TWAP_DELTA) | 0x0000000000000c51d0f8cf4bd9ade7191372a625 |  |
| 71 | Pirex | 7 | gescand — niks (PirexCvx; PirexFees.distributeFees zonder gate maar ontvangers = treasury/contributors en approvals exact + in dezelfde tx verbruikt: 0 staande allowance → hygiëne/LAAG) | 0x35a398425d9f1029021a92bc3d2557d42c8588d7 |  |
| 72 | Punks Terminal | 7 | gescand — niks (StashFactory + Stash-impl 0x…60d035a8; placeOrder alleen owner via auction, processPunkBid met owner-handtekening + nonces) | 0x000000000000a6fa31f5fc51c1640aac76866750 |  |
| 73 | Ribbon | 7 | gescand — niks; oracle: ok (RibbonThetaVaultWithSwap; settlement via Opyn-expiryprijs met dispute-periode; flagged functies = eigen-gebruiker (initiateWithdraw/pausePosition) of bewust permissionless (closeRound/initRounds)) | 0xdd9d1b7deab1a843a1b584d2ca5903b8a4735def |  |
| 74 | Ribbon Earn | 7 | gescand — niks (RibbonEarnVault; flagged = eigen-gebruiker-functies) | 0x84c2b16fa6877a8ff4f3271db7ea837233dfd6f0 |  |
| 75 | Royco V2 | 7 | gescand — niks (RoycoEntryPoint + RoycoFactory, impl via EIP-1967 bevestigd) | 0x63da1229be88fb4d20210147954a1a3e05f2581b |  |
| 76 | Saddle Finance | 7 | gescand — niks (SwapFlashLoan-pool via PoolRegistry (33 pools); reentrancy-meldingen achter nonReentrant) | 0xacb83e0633d6605c5001e2ab59ef3c745547c8c7 |  |
| 77 | Saffron Vaults | 7 | gescand — niks; oracle: ok (UniV3Vault + UniV3LimitedRangeAdapter; slot0 alleen voor mint-verhouding met user-amount0Min/amount1Min, onlyVault) | 0x84f0c6e5a7ea3bd89249f26a72b6e624344944dd |  |
| 78 | Sierra Protocol | 8 | gescand — niks (BeaconProxy → PoolDynamic, een pool-instance = eigen logica; alleen Medium/Low, geen ongegate waarde-functie) | 0xe1b1252652a2ff0cc3a4214ee73d9fed1fea5b4f |  |
| 79 | Silo V2 | 8 | gescand — niks (SiloFactory; alleen Medium/Low. Let op: dit is de **factory**, de waarde-logica zit in de gedeployede Silo-instances — die zijn hier niet apart gescand) | 0x22a3cf6149bfa611bafc89fd721918ec3cf7b581 |  |
| 80 | SMARDEX USDN | 8 | gescand — niks; 3× High `msg-value-in-nonpayable` op `initiateOpenPosition`/`initiateClosePosition`/`_refundExcessEther` = **FP**: dit zijn `external` library-functies die via de payable delegatecall-dispatcher van het protocol draaien, waar `msg.value` juist de originele waarde is (bewust, o.a. ether-refund) | 0x656cb8c6d154aad29d8771384089be5b5141f01a |  |
| 81 | Stafi | 8 | gescand — niks (RETHToken = token-only: rol-gated mint/burn van de rETH-staking-token; staking-logica elders) | 0x9559aaa82d9649c7a7b220e7c461d2e74c9a3593 |  |
| 82 | StakeStone Berachain Vault | 8 | gescand — niks (StoneBeraVault; alleen Medium/Low, geen ongegate waarde-bypass) | 0x8f88ae3798e8ff3d0e0de7465a0863c9bbb577f0 |  |
| 83 | Stakingverse | 8 | gescand — niks (ERC1967Proxy → EthVault; alleen Medium/Low) | 0x8a93a876912c9f03f88bc9114847cf5b63c89f56 |  |
| 84 | Stargate V1 | 8 | gescand — niks; 2× High `unprotected-sibling` op `addLiquidity`/`swap` = **FP**: beide zijn `nonReentrant` en bewust permissionless; `_safeTransferFrom(..., msg.sender, ...)` haalt alleen van de caller, en het "caller-gekozen" token-adres komt uit `_getPool(_poolId)` (alleen door de owner geregistreerde pools) | 0x8731d54e9d02c286767d56ac03e8037c07e01e98 |  |
| 85 | STONEUSD | 8 | gescand — niks (Token = token-only, 0 findings) | 0x6a6e3a4396993a4ec98a6f4a654cc0819538721e |  |
| 86 | stUSDT | 8 | gescand — niks; 2× High = **FP**: `controlled-delegatecall` is de standaard proxy-fallback naar een admin-gezette `implementation`-slot (niet caller-gekozen); `uninitialized-state` = proxy-storage-patroon | 0x25ec98773d7b4ced4cafab96a2a1c0945f145e10 |  |
| 87 | Superform | — | N.V.T. — adapter-adres wijst naar **Notional** (`nBeaconProxy → PrimeCashProxy` 0x92dc86b9…), niet Superform's eigen code; niet toe te schrijven aan Superform | 0x4a9e282635567cc4d3c6a24e16c2335f10dee9b8 |  |
| 88 | Symbiosis | — | N.V.T. — adapter-adres wijst naar **Puffer** (`ERC1967Proxy → PufferVaultV5` 0x3b2fdfde…), niet Symbiosis' eigen code; de 2× High `reentrancy-eth` zit bovendien in het OZ-ERC20-transfer-patroon (FP) | 0xd9a442856c234a39a81a089c06451ebaa4306a72 |  |
| 89 | Synapse Cross Chain Bridge | 8 | gescand — niks; 4× High `reentrancy-balance` = **FP**: dit is Saddle's `SwapFlashLoan`-code (fork), `flashLoan`/`addLiquidity` staan achter `nonReentrant` — zelfde dispositie als Saddle Finance (#76) | 0x1116898dda4015ed8ddefb84b6e8bc24528af2d8 |  |
| 90 | Syntropia | 8 | gescand — niks; 5× High = **FP**: `arbitrary-from in transferFrom` op `cancelRequestDeposit` is het ERC-7540 silo-patroon — `from` = het protocol-eigen `pendingSilo` (vast adres, pre-approved) en `requestedAmount` is per `msg.sender` gesleuteld, dus geen vreemde fondsen bereikbaar; overige = SafeERC20-reentrancy-FP | 0x1b2cb79a4564206f53ba80b4d780f251b4ae6765 |  |
| 91 | Tangent Finance | 8 | gescand — niks (MarketCreator; 0 High, alleen 1 Low. Let op: creator/factory — markt-logica zit in de gedeployede markten) | 0x214c8a1023b30032a2eded109146658c6d6f2781 |  |
| 92 | The Idols | 8 | gescand — niks (IdolMain; alleen Medium/Low, geen ongegate waarde-bypass) | 0x439cac149b935ae1d726569800972e1669d17094 |  |
