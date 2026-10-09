# EVM-inventaris Ethereum: eigen code of fork/standaard

Bron: DeFiLlama (`api.llama.fi/protocols`), Ethereum-TVL $1M–$20M, 278 protocollen. Adressen uit de DeFiLlama-TVL-adapters (contracten waar de TVL staat); verified source en proxy-implementation via Etherscan v2 (read-only: getsourcecode, eth_getStorageAt, eth_call op beacon, eth_getCode). Classificatie: heuristiek op contractnamen, imports/paden en kenmerkende code, plus aandeel eigen regels t.o.v. library-code.

| protocol | verified source? | proxy? | EIGEN CODE / FORK-van-X / STANDAARD-template | compiler | contract (→ implementation) | adres | opmerking |
|---|---|---|---|---|---|---|---|
| 1212 Capital | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| 1inch Swap | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x111111111117dc0aa78b770fa6a738034120c302); protocollogica-adres onbekend |
| 3Jane Lending | ja | ja (EIP-1967) | FORK/STANDAARD: Morpho / MetaMorpho | v0.8.22 | TransparentUpgradeableProxy → MorphoCredit | 0xde6e08ac208088cc62812ba30608d852c6b0ecbc |  |
| Aave V1 | ja | ja (EIP-1967) | EIGEN CODE | v0.5.17 | InitializableAdminUpgradeabilityProxy → LendingPoolCore | 0x3dfd23a6c5e8bbcfc9581d2e864a68feb6a076d3 |  |
| Abracadabra Spell | ja | ja | EIGEN CODE (integreert Convex) | v0.6.12 | ConvexStakingWrapperAbra → ConvexStakingWrapperAbra | 0x9447c1413da928af354a114954bfc9e6114c5646 |  |
| ADI Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x8b1484d57abbe239bb280661377363b03c89caea); protocollogica-adres onbekend |
| Aera V3 | ja | nee | EIGEN CODE | v0.8.29 | MultiDepositorVaultFactory | 0x29722cc9a1cacff4a15914f9bc274b46f3b90b4f |  |
| Aevo Perps | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xb528edbef013aff855ac3c50b381f253af13b997); protocollogica-adres onbekend |
| Agua | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Allbridge Classic | ja | nee | EIGEN CODE | v0.8.9 | Bridge | 0xbbbd1bbb4f9b936c3604906d7592a644071de884 |  |
| alphagrowth | ja | ja (EIP-1967 beacon 0x29a56a1b8214d9cf7c5561811750d5cbdb45cc8e) | FORK/STANDAARD: Euler V2 (EVK / Earn) | v0.8.24 | BeaconProxy → EVault | 0x05e09415398659b19c5aef202289270b37f1fb31 |  |
| AlphaPing | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Ammalgam Vaults | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Angle | ja | ja (EIP-1967) | EIGEN CODE | vyper:0.2.16 | TransparentUpgradeableProxy → Voting Escrow | 0x0c462dbb9ec8cd1630f1728b2cfd2769d09f0dd5 |  |
| Angstrom | ja | nee | EIGEN CODE (integreert Uniswap V4) | v0.8.26 | Angstrom | 0x0000000aa232009084bd71a5797d089aa4edfad4 |  |
| Anvil | ja | nee | EIGEN CODE | v0.8.25 | CollateralVault | 0x5d2725fde4d7aa3388da4519ac0449cc031d675f |  |
| Apex Omni | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| ApeX Pro | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x52a8845df664d76c69d2eea607cd793565af42b8); protocollogica-adres onbekend |
| Api3 | ja | ja | EIGEN CODE | v0.7.6 | SafeProxy → Safe | 0x5a9aa3219dd1cbef6a18fd221464e071df2677c2 |  |
| Apostro | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Arbitrum Nova Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x912ce59144191c1204e64559fe8253a0e49e6548); protocollogica-adres onbekend |
| Arrakis V1 | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | EIP173ProxyWithReceive → ArrakisFactoryV1 | 0xea1aff9dbffd1580f6b81a3ad3589e66652db7d9 |  |
| Asymmetry Finance | ja | ja (EIP-1967) | EIGEN CODE | v0.6.11 | AdminUpgradeabilityProxy → AETH_R21 | 0xe95a203b1a91a908f9b9ce46459d101078c2c3cb |  |
| Augur | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x221657776846890989a759ba2973e427dff5c9bb); protocollogica-adres onbekend |
| Aura | ja | nee | FORK/STANDAARD: Convex | v0.6.12 | Booster | 0x7818a1da7bd1e64c199029e86ba244a9798eee10 |  |
| Aurus | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | TransparentUpgradeableProxy → TokenizedGold | 0xe4a6f23fb9e00fca037aa0ea0a6954de0a6c53bf |  |
| Avantgarde | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| B.Protocol | ja | nee | EIGEN CODE | v0.5.16 | BTVL | 0x60312e01a2acd1dac68838c949c1d20c609b20cf |  |
| Backpack | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Badger DAO | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x3472a5a71965499acd81997a54bba8d852c6e53d); protocollogica-adres onbekend |
| Balancer V1 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xba100000625a3754423978a60c9317c58a424e3d); protocollogica-adres onbekend |
| Balancer V2 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xba100000625a3754423978a60c9317c58a424e3d); protocollogica-adres onbekend |
| Balancer V3 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xba100000625a3754423978a60c9317c58a424e3d); protocollogica-adres onbekend |
| Bancor V2.1 | ja | nee | EIGEN CODE | v0.4.24 | ContractRegistry | 0x52ae12abe5d8bd778bd5397f99ca900624cfadd4 |  |
| Bancor V3 | ja | ja (EIP-1967) | EIGEN CODE | v0.8.13 | TransparentUpgradeableProxyImmutable → MasterVault | 0x649765821d9f64198c905ec0b2b037a4a52bc373 |  |
| Baseline Protocol | ja | nee | EIGEN CODE | v0.8.30 | BToken | 0x9fdbde76236998dc2836fe67a9954ede456a1d63 | token-adres uit DeFiLlama (geen adapter-adres) |
| BendDAO APE Staking | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x0d02755a5700414b26ff040e1de35d337df56218); protocollogica-adres onbekend |
| Bifrost Liquid Staking | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| BigONE | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Bio Protocol | ja | ja (EIP-1967) | EIGEN CODE | v0.8.23 | ERC1967Proxy → VeBIO | 0xf91a12742aa609d41513a137d3c36b749f56f40c |  |
| Bitlo | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| BitMart | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Bitrue | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| BitVenus | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Bitwise | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Blast Bridge | ja | ja (EIP-1967) | EIGEN CODE | v0.8.15 | L1ChugSplashProxy → USDYieldManager | 0xa230285d5683c74935ad14c446e137c8c8828438 |  |
| Blast pre-launch Farm | ja | ja (EIP-1967) | EIGEN CODE | v0.8.15 | ERC1967Proxy → LaunchBridge | 0x5f6ae08b8aeb7078cf2f96afb089d7c9f51da47d |  |
| Blur Bids | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x5283d291dbcf85356a21ba090e6db59121208b44); protocollogica-adres onbekend |
| Blur Lending | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x5283d291dbcf85356a21ba090e6db59121208b44); protocollogica-adres onbekend |
| BOB Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xc9746f73cc33a36c2cd55b8aefd732586946cedd); protocollogica-adres onbekend |
| Boba Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| BounceBit Prime | ja | ja (EIP-1967) | GEEN VERIFIED SOURCE (implementation) | v0.8.10 | TransparentUpgradeableProxy | 0x6f776d791612a22a70e206602cff96185695c580 | implementation niet geverifieerd: 0xf17c30ccb9f247de42b61f31d33c9d62eb934208 is niet geverifieerd op etherscan-v2 (geen broncode) |
| Brickken | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | ERC1967Proxy → STOFactoryManagedUpgradeable | 0x91af681c85ca98efc5d69c1b62e6f435030969db |  |
| BYDFi | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Byte Exchange | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Capyfi | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| cBridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x4f9254c83eb525f9fcf346490bbb3ed28a81c667); protocollogica-adres onbekend |
| CEX.IO | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Chain Fusion | — |  | ADRES ONBEKEND |  |  | 0xb25ea1d493b49a1ded42ac5b1208cc618f9a9b80 | kandidaat-adressen zijn EOA's/niet op Ethereum |
| ClayStack ETH | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| CLever | ja | nee | FORK/STANDAARD: Balancer V2 | v0.7.1 | Vault | 0xba12222222228d8ba445958a75a0704d566bf2c8 |  |
| Compound V1 | ja | nee | EIGEN CODE | v0.4.24 | MoneyMarket | 0x3fda67f7583380e67ef93072294a7fac882fd7e7 |  |
| Contango V2 | ja | ja (EIP-1967) | EIGEN CODE | v0.8.27 | ERC1967Proxy → Contango | 0x6cae28b3d09d8f8fc74ccd496ac986fc84c0c24e |  |
| Convergence Fi | ja | ja (EIP-1967) | STANDAARD-template: OpenZeppelin-only (dunne eigen laag) | v0.8.24 | TransparentUpgradeableProxy → CvgControlTowerV2 | 0xb0afc8363b8f36e0cce5d54251e20720ffaeaee7 |  |
| CRETH2 | ja | nee | STANDAARD-template: OpenZeppelin-only (dunne eigen laag) | v0.8.7 | CreamEth2 | 0x49d72e3973900a195a155a46441f0c08179fdb64 |  |
| cVault Finance | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x62359ed7505efc61ff1d56fef82158ccaffa23d7); protocollogica-adres onbekend |
| Cyclone | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x8861cff2366c1128fd699b68304ad99a0764ef9a); protocollogica-adres onbekend |
| DAMM Capital | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| deBridge | ja | ja (EIP-1967) | EIGEN CODE | v0.8.17 | TransparentUpgradeableProxy → DeBridgeGate | 0x43de2d77bf8027e25dbd179b491e8d64f38398aa |  |
| Decentralized Euro | ja | nee | EIGEN CODE | v0.8.19 | FPSWrapper | 0x5052d3cc819f53116641e89b96ff4cd1ee80b182 |  |
| Defi Swap | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xa0b73e1ff0b80914ab6fe0444e65848c4c34450b); protocollogica-adres onbekend |
| DeFIL | ja | nee | FORK/STANDAARD: Uniswap V2 | v0.5.16 | UniswapV2Pair | 0xd372a3221021df72eda38f77117d3a95f057e163 |  |
| Dialectic | ja | ja (EIP-1967) | STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate) | v0.8.27 | VaultProxy → ConcreteAsyncVaultImpl | 0xcd9f5907f92818bc06c9ad70217f089e190d2a32 |  |
| Digital Gold | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | TransparentUpgradeableProxy → DGLDTokenV3 | 0xa9299c296d7830a99414d1e5546f5171fa01e9c8 |  |
| Dinero (pxETH) | ja | nee | EIGEN CODE | v0.8.19 | PxEth | 0x04c154b66cb340f3ae24111cc767e0184ed00cc6 |  |
| DODO AMM | ja | nee | EIGEN CODE | v0.6.9 | DVMFactory | 0x72d220ce168c4f361dd4dee5d826a01ad8598f6c |  |
| Easedefi.org | ja | nee | EIGEN CODE | v0.5.7 | NXMToken | 0xd7c49cee7e9188cca6ad8ff264c1da2e69d4cf3b |  |
| Eclipse Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x6055dc6ff1077eebe5e6d2ba1a1f53d7ef8430de); protocollogica-adres onbekend |
| edgeX Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xb0076de78dc50581770bba1d211ddc0ad4f2a241); protocollogica-adres onbekend |
| Eigenpie | ja | ja (EIP-1967) | EIGEN CODE | v0.8.21 | TransparentUpgradeableProxy → EigenpieConfig | 0x20b70e4a1883b81429533fed944d7957121c7cab |  |
| Ekubo | ja | nee | FORK/STANDAARD: Uniswap V3 (kenmerken in code) | v0.8.28 | Core | 0xe0e0e08a6a4b9dc7bd67bcb7aade5cf48157d444 |  |
| Ensuro | ja | ja (EIP-1967) | EIGEN CODE | v0.8.18 | ERC1967Proxy → USDO | 0x8238884ec9668ef77b90c6dff4d1a9f4f4823bfe |  |
| Equilibria | ja | ja (EIP-1967) | EIGEN CODE (integreert Convex) | v0.8.17 | TransparentUpgradeableProxy → PendleBoosterMainchain | 0x4d32c8ff2facc771ec7efc70d6a8468bc30c26bf |  |
| ETH Strategy | ja | nee | STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate) | v0.8.20 | EthStrategyPerpetualNote | 0xb250c9e0f7be4cff13f94374c993ac445a1385fe |  |
| Ethereal Season Zero | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| EtherFlip | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| eva Markets | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Fake World Assets V2 | ja | nee | EIGEN CODE | v0.8.26 | FWAV2 | 0x958c41181182e76f221331b2755b77d9e1426a98 |  |
| FermiSwap | ja | nee | EIGEN CODE | v0.8.28 | FermiSwapper | 0xb1076fe3ab5e28005c7c323bac5ac06a680d452e |  |
| Fira | ja | ja (EIP-1967) | EIGEN CODE | v0.8.20 | TransparentUpgradeableProxy → Usd0PP | 0x35d8949372d46b7a3d5a56006ae77b215fc69bc0 |  |
| Flex | ja | nee | EIGEN CODE (integreert Curve (Vyper), Yearn) | vyper:0.4.3 | Registry | 0x9117440a7d03238905d1c8908157bd7a547c77c8 |  |
| Flexa | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xff20817765cb7f73d4bde2e66e067e58d11095c2); protocollogica-adres onbekend |
| Flipster | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| FlokiFi Locker | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xcf0c122c6b73ff809c693db761e7baebe62b6a2e); protocollogica-adres onbekend |
| Flying Tulip Lend | ja | ja (EIP-1967) | EIGEN CODE | v0.8.30 | ERC1967Proxy → ftYieldWrapper | 0x7127bb9d9ad0f47b8da9087e634d67f3946f840e |  |
| Fomo3D | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Frax Swap | ja | nee | EIGEN CODE (integreert Uniswap V2) | v0.8.13 | FPIControllerPool | 0x2397321b301b80a1c0911d6f9ed4b6033d43cf51 |  |
| Fuel Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| GAIB | ja | ja (EIP-1967) | EIGEN CODE | v0.8.22 | ERC1967Proxy → AID | 0x18f52b3fb465118731d9e0d276d4eb3599d57596 |  |
| Gamma | ja | nee | EIGEN CODE | v0.7.6 | Hypervisor | 0x64fcdd0de44f4bd04c039b0664fb95ef033d4efb |  |
| Gate US | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Gnosis Protocol v1 | ja | nee | EIGEN CODE | v0.5.10 | ConditionalTokens | 0xc59b0e4de5f1248c1140964e0ff287b192407e0c |  |
| Goldfinch | ja | ja (EIP-1967) | GEEN VERIFIED SOURCE (implementation) | v0.7.6 | EIP173Proxy | 0x8481a6ebaf5c7dabc3f7e09e44a89531fd31f822 | implementation niet geverifieerd: 0x656cc68d76c7dea07b477ffd26f6c9766d154e5e is niet geverifieerd op etherscan-v2 (geen broncode) |
| Gondi V3 | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Gravity by Galxe | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x9c7beba8f6ef6643abd725e45a4e8387ef260649); protocollogica-adres onbekend |
| Gro | ja | nee | EIGEN CODE | v0.6.12 | NonRebasingGToken | 0x3adb04e127b9c0a5d36094125669d4603ac52a0c |  |
| Hakka Finance | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x0e29e5abbb5fd88e28b2d355774e73bd47de3bcd); protocollogica-adres onbekend |
| Harvest Finance | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xa0246c9032bc3a600820415ae600c6388619a14d); protocollogica-adres onbekend |
| HashKey Global | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Hashport | ja | ja | STANDAARD-template: OpenZeppelin-only (dunne eigen laag) | v0.8.3 | Router → RouterFacet | 0x367e59b559283c8506207d75b0c5d8c66c4cd4b7 |  |
| Hegic | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x584bc13c7d411c00c01a62e8019472de68768430); protocollogica-adres onbekend |
| Hemi | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xeb964a1a6fab73b8c72a0d15c7337fa4804f484d); protocollogica-adres onbekend |
| Hibt | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Hop Protocol | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xc5102fe9359fd9a28f877a67e36b0f050d81a3cc); protocollogica-adres onbekend |
| Hub Capital | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Hyperlane | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xc9d23ed2adb0f551369946bd377f8644ce1ca5c4); protocollogica-adres onbekend |
| IDEX Classic | ja | nee | EIGEN CODE | v0.6.8 | Custodian | 0xe5c405c5578d84c5231d3a9a29ef4374423fa0c2 |  |
| Idle | ja | nee | EIGEN CODE (integreert Uniswap V3) | v0.8.10 | TrancheWrapper | 0xcf96f4b91c6d424fb34aa9a33855b5c8ed1fe66d |  |
| InceptionLRT (Isolated Restaking) | ja | ja (EIP-1967) | EIGEN CODE | v0.8.28 | TransparentUpgradeableProxy → InVault_E1 | 0x814cc6b8fd2555845541fb843f37418b05977d8d |  |
| Index Coop | ja | nee | FORK/STANDAARD: Aave V2/V3 (kenmerken in code) | v0.6.10 | AaveV3LeverageModule | 0x9d08cced85a68bf8a19374ed4b5753ae3be9f74f |  |
| Injective Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xe28b3b32b6c345a34ff64674606124dd5aceca30); protocollogica-adres onbekend |
| Interest Protocol | ja | ja (EIP-1967) | GEEN VERIFIED SOURCE (implementation) | v0.8.9 | TransparentUpgradeableProxy | 0x4aae9823fb4c70490f1d802fc697f3fff8d5cbe3 | implementation niet geverifieerd: 0xffc8c49c5b38bc9bafd0bb0f5f189eecd35e35e2 is niet geverifieerd op etherscan-v2 (geen broncode) |
| Inverse Finance Frontier | ja | ja | FORK/STANDAARD: Compound V2 | v0.5.17 | Unitroller → Comptroller | 0x4dcf7407ae5c07f8681e1659f626e114a7667339 |  |
| Juicebox V1 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x3abf2a4f8452ccc2cf7b4c1e4663147600646f66); protocollogica-adres onbekend |
| K2 | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Kamui | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Katana Pre-Launch | ja | ja | EIGEN CODE (integreert Curve (Vyper), Yearn) | vyper:0.3.7 | Yearn V3 Vault → Yearn V3 Vault | 0xf470eb50b4a60c9b069f7fd6032532b8f5cc014d |  |
| Keep3r Network | ja | nee | EIGEN CODE | v0.8.7 | Keep3r | 0xeb02addcfd8b773a5ffa6b9d1fe99c566f8c44cc |  |
| Keyrock | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| King Protocol | ja | ja (EIP-1967) | EIGEN CODE | v0.8.25 | UUPSProxy → LRTSquaredCore | 0x8f08b70456eb22f6109f57b8fafe862ed28e6040 |  |
| KUMA Protocol | ja | ja (EIP-1967) | EIGEN CODE | v0.8.17 | ERC1967Proxy → KIBToken | 0x01bf66becdcfd6d59a5ca18869f494fea086cdfd |  |
| LandX Finance | ja | nee | FORK/STANDAARD: Uniswap V3 (kenmerken in code) | v0.8.16 | XToken | 0x8a78c1042f24349595f36f1a83091163487f2241 |  |
| Latch | ja | nee | EIGEN CODE | v0.8.24 | DepositPool | 0xfe606eec8eb8e6ad8e8654968a15650f5331a023 |  |
| LBank | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| LendFlare | ja | nee | EIGEN CODE | v0.6.12 | VirtualBalanceWrapper | 0x10a377ba353cd480e43800018a27742054904c1a |  |
| LeveX | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Lista DEX | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xfceb31a79f71ac9cbdcf853519c1b12d379edc46); protocollogica-adres onbekend |
| Lista Lending | ja | ja (EIP-1967) | EIGEN CODE | v0.8.28 | ERC1967Proxy → Moolah | 0xf820fb4680712cd7263a0d3d024d5b5aea82fd70 |  |
| Llama Airforce | ja | nee | EIGEN CODE | v0.8.9 | UnionVault | 0x83507cc8c8b67ed48badd1f59f684d5d02884c81 |  |
| LUSD ChickenBonds | ja | nee | EIGEN CODE (integreert Yearn) | v0.8.15 | ChickenBondManager | 0x57619fe9c539f890b19c61812226f9703ce37137 |  |
| MCDEX | ja | nee | EIGEN CODE | v0.5.15 | Perpetual | 0x220a9f0dd581cbc58fcfb907de0454cbf3777f76 |  |
| MegaETH Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Mento V2 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x7ff62f59e3e89ea34163ea1458eebcc81177cfb6); protocollogica-adres onbekend |
| Metronome Synth | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x2ebd53d035150f328bd754d6dc66b99b0edb89aa); protocollogica-adres onbekend |
| MEV Capital | ja | nee | FORK/STANDAARD: Morpho / MetaMorpho | v0.8.21 | MetaMorpho | 0xd63070114470f685b75b74d60eec7c1113d33a3d |  |
| Mezo Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x7b7c000000000000000000000000000000000001); protocollogica-adres onbekend |
| Mode Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Morph Bridge | ja | ja (EIP-1967) | EIGEN CODE | v0.8.24 | TransparentUpgradeableProxy → L1CrossDomainMessenger | 0xdc71366effa760804dcfc3edf87fa2a6f1623304 |  |
| mStable CDP | ja | ja (EIP-1967) | EIGEN CODE | v0.8.0 | MassetProxy → MusdV3_deprecated | 0xe2f2a5c287993345a840db3b0845fbc70f5935a5 |  |
| mStable V2 | ja | ja (EIP-1967) | EIGEN CODE (integreert Uniswap V4, Gnosis Safe) | v0.7.6 | TransparentUpgradeableProxy → PoolFactory | 0x96d33bcf84dde326014248e2896f79bbb9c13d6d |  |
| Mt Pelerin | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Multichain | ja | nee | EIGEN CODE | v0.6.10 | BscBridge | 0xc342774492b54ce5f8ac662113ed702fc1b34972 |  |
| NaraUSD | ja | ja | EIGEN CODE | v0.7.6 | SafeProxy → Safe | 0xab05c0db9d26e96a9dcedcafca23341316f6fe6f |  |
| Native Credit Pool | ja | nee | EIGEN CODE | v0.8.28 | CreditVault | 0xe3d41d19564922c9952f692c5dd0563030f5f2ef |  |
| NEMO Trading | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | TransparentUpgradeableProxy → TokenizedVault | 0x955256b31097ddf47a9e47a95adfdfb4460d8522 |  |
| NFTX | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | AdminUpgradeabilityProxy → NFTXVaultFactoryUpgradeable | 0xbe86f647b167567525ccaafcd6f881f1ee558216 |  |
| Niza | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Notional V2 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xcfeaead4947f0705a14ec42ac3d44129e1ef3ed5); protocollogica-adres onbekend |
| Nucleus | ja | nee | EIGEN CODE | v0.8.21 | BoringVault | 0x52e4d8989fa8b3e1c06696e7b16def5d7707a0d1 |  |
| NUVA | ja | ja (EIP-1967) | EIGEN CODE | v0.8.28 | ERC1967Proxy → DedicatedVaultRouter | 0x50ae1e4a612a4623b747aeefb30afba82804e12c |  |
| Odyssey Digital AM | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Odyssey Finance | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Okcoin | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| OpenGDP Shared Security | ja | ja (EIP-1967) | STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate) | v0.8.25 | VaultSupervisor → VaultSupervisor | 0x54e44dbb92dba848ace27f44c0cb4268981ef1cc |  |
| Opyn Gamma | ja | nee | EIGEN CODE | v0.6.10 | Whitelist | 0xa5ea18ac6865f315ff5dd9f1a7fb1d41a30a6779 |  |
| OrangeX | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Orderly Bridge | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | TransparentUpgradeableProxy → Vault | 0x816f722424b49cf1275cc86da9840fbd5a6167e9 |  |
| Origin ARM | ja | ja (EIP-1967) | EIGEN CODE | v0.8.28 | OETHProxy → OETH | 0x856c4efb76c1d1ae02e20ceb03a2a6a08b0b8dc3 |  |
| Origin Dollar | ja | ja (EIP-1967) | EIGEN CODE | v0.8.10 | ExponentialStakingProxy → ExponentialStaking | 0x63898b3b6ef3d39332082178656e9862bee45c57 |  |
| Ourbit | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Outcome Finance | ja | nee | EIGEN CODE | v0.8.4 | LongShortPairCreator | 0x0b8de441b26e36f461b2748919ed71f50593a67b |  |
| P2PB2B | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| PancakeSwap AMM | ja | nee | EIGEN CODE (integreert Uniswap V2) | v0.5.16 | PancakeFactory | 0x1097053fd2ea711dad45caccc45eff7548fcb362 |  |
| Panoptic V2 | ja | nee | EIGEN CODE (integreert Uniswap V3, Uniswap V4) | v0.8.28 | PanopticFactoryV3 | 0x0000000000000adc9a108591e718f2aee963a2a7 |  |
| Penpie | ja | ja (EIP-1967) | FORK/STANDAARD: Convex (kenmerken in code) | v0.8.19 | TransparentUpgradeableProxy → MasterPenpie | 0x16296859c15289731521f199f0a5f762df6347d0 |  |
| Pickle | ja | nee | FORK/STANDAARD: Curve (Vyper) | vyper:0.3.0 | Vyper_contract | 0xed4064f376cb8d68f770fb1ff088a3d0f3ff5c4d |  |
| PinkSale | ja | nee | FORK/STANDAARD: Uniswap V2 (kenmerken in code) | v0.8.4 | PinkLock | 0x33d4cc8716beb13f814f538ad3b2de3b036f5e2a |  |
| Pionex | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Pirex | ja | nee | EIGEN CODE (integreert Synthetix StakingRewards) | v0.8.12 | PirexCvx | 0x35a398425d9f1029021a92bc3d2557d42c8588d7 |  |
| pNetwork | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x89ab32156e46f46d02ade3fecbe5fc4243b9aaed); protocollogica-adres onbekend |
| PoolTogether V3 | — |  | ADRES ONBEKEND |  |  | 0x887e17d791dcb44bfdda3023d26f7a04ca9c7ef4 | kandidaat-adressen zijn EOA's/niet op Ethereum |
| PoWH3D | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Presto | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Privacy Pools | ja | ja (EIP-1967) | STANDAARD-template: OpenZeppelin-only (dunne eigen laag) | v0.8.28 | ERC1967Proxy → Entrypoint | 0x6818809eefce719e480a7526d76bd3e561526b46 |  |
| ProBit Global | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Punks Terminal | ja | nee | EIGEN CODE | v0.8.23 | StashFactory | 0x000000000000a6fa31f5fc51c1640aac76866750 |  |
| Rainbow Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Rari Capital | ja | ja | PROXY (implementation niet bepaald) | v0.5.17 | RariFundProxy | 0x4a785fa6fcd2e0845a24847beb7bddd26f996d4d | proxy herkend, maar geen implementation-slot/beacon/explorer-implementation gevonden |
| Re7 Labs | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Reflexer | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x6243d8cea23066d098a15582d81a598b4e8391f4); protocollogica-adres onbekend |
| Reservoir Protocol | ja | nee | STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate) | v0.8.24 | MorphoUnderlyingAdapter | 0x99a95a9e38e927486fc878f41ff8b118eb632b10 |  |
| Resolv USR | ja | ja (EIP-1967) | STANDAARD-template: OpenZeppelin-only (dunne eigen laag) | v0.8.25 | TransparentUpgradeableProxy → SimpleToken | 0x66a1e37c9b0eaddca17d3662d6c05f4decf3e110 |  |
| Revert Lend | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Reya Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Rezerve Lending | ja | ja (EIP-1967 beacon 0x29a56a1b8214d9cf7c5561811750d5cbdb45cc8e) | FORK/STANDAARD: Euler V2 (EVK / Earn) | v0.8.24 | BeaconProxy → EVault | 0xc42d337861878baa4dc820d9e6b6c667c2b57e8a |  |
| Ribbon | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | AdminUpgradeabilityProxy → RibbonThetaVaultWithSwap | 0xdd9d1b7deab1a843a1b584d2ca5903b8a4735def |  |
| Ribbon Earn | ja | ja (EIP-1967) | EIGEN CODE | v0.8.4 | AdminUpgradeabilityProxy → RibbonEarnVault | 0x84c2b16fa6877a8ff4f3271db7ea837233dfd6f0 |  |
| Ronin Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xe514d9deb7966c8be0ca922de8a064264ea6bcd4); protocollogica-adres onbekend |
| Rook | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xfa5047c9c78b8877af97bdcb85db743fd7313d4a); protocollogica-adres onbekend |
| Royco V2 | ja | ja (EIP-1967) | EIGEN CODE | v0.8.34 | ERC1967Proxy → RoycoFactory | 0x7cc6fb28ec7b5e7afc3cb3986141797ffc27253c |  |
| Rysk V12 | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Sablier Lockup | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Saddle Finance | ja | nee | EIGEN CODE | v0.6.12 | MasterRegistry | 0xc5ad17b98d7fe73b6dd3b0df5b3040457e68c045 |  |
| Saffron Vaults | ja | nee | EIGEN CODE | v0.8.18 | RestrictedVaultFactory | 0x7fe802b891734db681b7353bff9e6c85ce0ab200 |  |
| SATO | ja | nee | FORK/STANDAARD: Uniswap V4 (kenmerken in code) | v0.8.26 | SatoHook | 0x0000f07d2b5f1ddf3244b8780f972f306efd2888 |  |
| Seamless V2 | ja | ja (EIP-1967) | STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate) | v0.8.30 | ERC1967Proxy → LeverageManager | 0x5c37eb148d4a261acd101e2b997a0f163fb3e351 |  |
| Set Protocol | ja | nee | FORK/STANDAARD: Compound V2 | v0.5.8 | CErc20 | 0x39aa39c021dfbae8fac545936693ac917d5e7563 |  |
| Shape Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| SharpByte Capital | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| ShibaSwap V1 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x9813037ee2218799597d83d4a5b6f3b6778218d9); protocollogica-adres onbekend |
| Sierra Protocol | ja | ja (EIP-1967 beacon 0x0a3b7bb45ac8e267cc4e4b2cbdb52b967d82df18) | EIGEN CODE | v0.8.36 | BeaconProxy → PoolDynamic | 0xe1b1252652a2ff0cc3a4214ee73d9fed1fea5b4f |  |
| Silo V2 | ja | nee | EIGEN CODE | v0.8.28 | SiloFactory | 0x22a3cf6149bfa611bafc89fd721918ec3cf7b581 |  |
| SingularX | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| SMARDEX USDN | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | ERC1967Proxy → UsdnProtocolImpl | 0x656cb8c6d154aad29d8771384089be5b5141f01a |  |
| Solv Strategies | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| SolvBTC | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x256f2d67e52fe834726d2ddcd8413654f5eb8b53); protocollogica-adres onbekend |
| Sophon Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Sorare Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Stafi | ja | nee | EIGEN CODE | v0.6.12 | RETHToken | 0x9559aaa82d9649c7a7b220e7c461d2e74c9a3593 |  |
| Stake DAO Curator | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x73968b9a57c6e53d41345fd57a6e6ae27d6cdb2f); protocollogica-adres onbekend |
| StakeStone Berachain Vault | ja | nee | EIGEN CODE | v0.8.26 | StoneBeraVault | 0x8f88ae3798e8ff3d0e0de7465a0863c9bbb577f0 |  |
| Stakingverse | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | ERC1967Proxy → EthVault | 0x8a93a876912c9f03f88bc9114847cf5b63c89f56 |  |
| Stargate V1 | ja | nee | EIGEN CODE (integreert LayerZero OFT) | v0.7.6 | Router | 0x8731d54e9d02c286767d56ac03e8037c07e01e98 |  |
| Steer Protocol | — |  | ADRES ONBEKEND |  |  | 0xd5532a58e4abb6485ff4e7bcf5bed278e32a516e | kandidaat-adressen zijn EOA's/niet op Ethereum |
| STONEUSD | ja | nee | EIGEN CODE | v0.8.26 | Token | 0x6a6e3a4396993a4ec98a6f4a654cc0819538721e |  |
| STRATO Bridge | — |  | ADRES ONBEKEND |  |  | 0x4d9e9c39180a75091b9c35bbb9064d67c7fdde5a | kandidaat-adressen zijn EOA's/niet op Ethereum |
| stUSDT | ja | ja | EIGEN CODE | v0.8.18 | StUSDTProxy → StUSDTG1 | 0x25ec98773d7b4ced4cafab96a2a1c0945f145e10 |  |
| Summer.fi Pro | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x194f360d130f2393a5e9f3117a6a1b78abea1624); protocollogica-adres onbekend |
| SunX Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Superfluid | — |  | ADRES ONBEKEND |  |  | 0x441bb79f2da0daf457bad3d401edb68535fb3faa | kandidaat-adressen zijn EOA's/niet op Ethereum |
| Superform | ja | ja (EIP-1967 beacon 0x1f681977af5392d9ca5572fb394bc4d12939a6a9) | EIGEN CODE (integreert Compound V2) | v0.7.6 | nBeaconProxy → PrimeCashProxy | 0x4a9e282635567cc4d3c6a24e16c2335f10dee9b8 |  |
| Swaap Maker V2 | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Switcheo Finance | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| SX Rollup Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Symbiosis | ja | ja (EIP-1967) | EIGEN CODE | v0.8.28 | ERC1967Proxy → PufferVaultV5 | 0xd9a442856c234a39a81a089c06451ebaa4306a72 |  |
| Synapse Cross Chain Bridge | ja | ja | EIGEN CODE | v0.6.12 | SwapFlashLoan → SwapFlashLoan | 0x1116898dda4015ed8ddefb84b6e8bc24528af2d8 |  |
| Syntropia | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | OptinProxy → Vault | 0x1b2cb79a4564206f53ba80b4d780f251b4ae6765 |  |
| Taiko Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x10dea67478c5f8c5e2d90e5e9b26dbe60c54d800); protocollogica-adres onbekend |
| Tangent Finance | ja | nee | EIGEN CODE (integreert Convex) | v0.8.28 | MarketCreator | 0x214c8a1023b30032a2eded109146658c6d6f2781 |  |
| TAU Labs | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Templar Protocol | ja | ja (EIP-1967) | FORK/STANDAARD: LayerZero OFT | v0.8.27 | TransparentUpgradeableProxy → FXRPOFT | 0xce6170ea245dc8d1f275a710a062b70f125f0110 |  |
| TermFinance Lend | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| The Idols | ja | nee | EIGEN CODE | v0.8.9 | IdolMain | 0x439cac149b935ae1d726569800972e1669d17094 |  |
| Theo Network thBill | ja | ja (EIP-1967) | EIGEN CODE | v0.8.19 | ERC1967Proxy → Ultra | 0x50293dd8889b931eb3441d2664dce8396640b419 |  |
| THORChain DEX | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Threshold thUSD | ja | nee | FORK/STANDAARD: Liquity | v0.8.17 | BorrowerOperations | 0xf5e4ffeb7d2183b61753aa4074d72e51873c1d0a |  |
| TokenStore | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| TokenWorks | ja | nee | EIGEN CODE (integreert Uniswap V4) | v0.8.30 | NFTStrategyFactory | 0xa1a196b5be89be04a2c1dc71643689ce013c22e5 |  |
| Twyne | ja | ja | FORK/STANDAARD: Euler V2 (EVK / Earn) | v0.8.24 | GenericFactory → EVault | 0xb5eb1d005e389bef38161691e2083b4d86ff647a |  |
| UNCX Network V3 | ja | nee | EIGEN CODE (integreert Uniswap V3) | v0.8.19 | UNCX_ProofOfReservesUniV3 | 0x231278edd38b00b07fbd52120cef685b9baebcc1 |  |
| UNCX Network V4 | ja | nee | EIGEN CODE (integreert Uniswap V4) | v0.8.26 | PositionManager | 0xbd216513d74c8cf14cf4747e6aaa6420ff64ee9e |  |
| Unichain Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Uniswap V1 | ja | nee | EIGEN CODE | vyper:0.1.0b4 | Vyper_contract | 0xc0a47dfe034b400b47bdad5fecda2621de6c4d95 |  |
| Unitus | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x3b6564b5da73a41d3a66e6558a98fd0e9e1e77ad); protocollogica-adres onbekend |
| Universal Bridge | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Universe XYZ | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x618679df9efcd19694bb1daa8d00718eacfa2883); protocollogica-adres onbekend |
| Unslashed | ja | ja (EIP-1967) | EIGEN CODE | v0.6.12 | VaultProxy → VaultLib | 0x86fb84e92c1eedc245987d28a42e123202bd6701 |  |
| Usual ETH0 | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xc4441c2be5d8fa8126822b9929ca0b81ea0de38e); protocollogica-adres onbekend |
| Vault Street | ja | ja (EIP-1967) | EIGEN CODE | v0.8.35 | TransparentUpgradeableProxy → PermissionedToken | 0x7ea76108975ec0998b9bc2db04b4eca986400dd7 |  |
| Veno Finance | ja | ja (EIP-1967) | EIGEN CODE | v0.8.24 | ERC1967Proxy → ZkCro | 0x28ff2e4dd1b58efeb0fc138602a28d5ae81e44e2 |  |
| Venus Core Pool | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0xcf6bb5389c92bdda8a3747ddb454cb7a64626c63); protocollogica-adres onbekend |
| vfat.io | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Wan Bridge | ja | ja | GEEN VERIFIED SOURCE (implementation) | v0.4.26 | CrossProxy | 0xfceaaaeb8d564a9d0e71ef36f027b9d162bc334e | implementation niet geverifieerd: 0x86ec03f7bafab24f69ebc456cc429b6f389ea4e4 is niet geverifieerd op etherscan-v2 (geen broncode) |
| Webot | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Wildcat Protocol | ja | nee | EIGEN CODE | v0.8.22 | WildcatArchController | 0xfeb516d9d946dd487a9346f6fee11f40c6945ee4 |  |
| WOO X | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Y10K Capital | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| Yamato Protocol | — |  | ADRES ONBEKEND |  |  |  | geen contractadres in DeFiLlama-adapter |
| YieldFi | ja | ja (EIP-1967) | EIGEN CODE | v0.8.26 | TransparentUpgradeableProxy → YToken | 0x19ebd191f7a24ece672ba13a302212b5ef7f35cb |  |
| YO Protocol | ja | ja (EIP-1967) | EIGEN CODE | v0.8.34 | TransparentUpgradeableProxy → YoVault | 0x0000000f2eb9f69274678c76222b35eec7588a65 |  |
| Yuzu Money | ja | ja (EIP-1967) | EIGEN CODE | v0.8.36 | TransparentUpgradeableProxy → YuzuILPV3 | 0x224e90591a2d63fb66e677d0561ea4a6ad1f098d |  |
| ZEROBASE CeDeFi | ja | nee | EIGEN CODE | v0.8.28 | Vault | 0x9ef52d8953d184840f2c69096b7b3a7da7093685 |  |
| ZeroLend Vaults | ja | ja (EIP-1967 beacon 0x29a56a1b8214d9cf7c5561811750d5cbdb45cc8e) | FORK/STANDAARD: Euler V2 (EVK / Earn) | v0.8.24 | BeaconProxy → EVault | 0xc42d337861878baa4dc820d9e6b6c667c2b57e8a |  |
| Zircuit | ja | ja (EIP-1967) | EIGEN CODE | v0.8.15 | Proxy → OptimismPortal2 | 0x17bfafa932d2e23bd9b909fd5b4d2e2a27043fb1 |  |
| zkLink Nova | ja | ja (EIP-1967) | EIGEN CODE | v0.8.18 | ERC1967Proxy → ZkLink | 0x5fd9f73286b7e8683bab45019c94553b93e015cf |  |
| Zoomex | n.v.t. |  | n.v.t. (CEX) |  |  |  | CEX (geen on-chain protocolcontract) |
| Zora Bridge | — |  | ADRES ONBEKEND |  |  |  | alleen governance-token gevonden (0x1111111111166b7fe7bd91427724b487980afc69); protocollogica-adres onbekend |
| ZTLN-P | ja | ja (EIP-1967) | EIGEN CODE | v0.8.27 | ERC1967Proxy → ZTLNPrime | 0xfed3d6557dc46a1b25d0a6f666513cb33835864b |  |

## Telling

- eigen code: **108**
- fork/standaard: **30**
- geen verified source: **4**
- proxy, implementation niet bepaald: **1**
- adres onbekend: **110**
- n.v.t. (CEX): **25**

Fork/standaard per familie: OpenZeppelin-only 5, ERC-4626 vault 5, Euler V2 4, Morpho / MetaMorpho 2, Convex 2, Uniswap V2 2, Uniswap V3 2, Compound V2 2, Balancer V2 1, Aave V2/V3 1, Curve 1, Uniswap V4 1, LayerZero OFT 1, Liquity 1

## Beperkingen

- Het 'hoofdcontract' is het eerste geverifieerde, niet-basistoken-contract uit de DeFiLlama-adapter. Bij protocollen met veel contracten kan een ander contract meer eigen logica bevatten.
- De familie-heuristiek herkent bekende namen en code-kenmerken; een sterk aangepaste fork kan als EIGEN CODE eindigen, en eigen code die een bekende interface importeert krijgt de notitie 'integreert X'.
- 'ADRES ONBEKEND' betekent: geen contractadres in de adapter (vaak API- of off-chain-gebaseerde TVL), of alleen een governance-token.
