#!/usr/bin/env python3
"""
Technical inventory of EVM (Ethereum) protocols: is the on-chain logic own code, or a fork/standard?

Read-only: Etherscan v2 getsourcecode / eth_getStorageAt / eth_getCode (key from ETHERSCAN_API_KEY).
Resumable: results are appended to results.json per protocol.

Run:  python3 shortlist/evm-eth/inventory.py
"""
import json
import os
import re
import sys
import threading
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
from solscan.evm import etherscan  # noqa: E402

OUT = os.path.join(HERE, "results.json")

# Well-known base assets / tokens: listed in many adapters as the asset held, not the protocol's own logic.
KNOWN_TOKENS = {
    "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "0xdac17f958d2ee523a2206206994597c13d831ec7", "0x6b175474e89094c44da98b954eedeac495271d0f",
    "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
    "0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0", "0xae78736cd615f374d3085123a210448e74fc6393",
    "0xbe9895146f7af43049ca1c1ae358b0541ea49704", "0x853d955acef822db058eb8505911ed77f175b99e",
    "0x5f98805a4e8be255a32880fdec7f6728c6568ba0", "0xf939e0a03fb07f59a73314e73794be0e57ac1b4e",
    "0x4c9edd5852cd905f086c759e8383e09bff1e68b3", "0x9d39a5de30e57443bff2a8307a4256c8797a3497",
    "0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee", "0x35fa164735182de50811e8e2e824cfb9b6118ac2",
    "0x6c3ea9036406852006290770bedfcaba0e23a0e8", "0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f",
    "0xdc035d45d973e3ec169d2276ddab16f1e407384f", "0x83f20f44975d03b1b09e64809b757c47f942beea",
    "0x9f8f72aa9304c8b593d555f12ef6589cc3a579a2", "0x514910771af9ca656af840dff83e8264ecf986ca",
    "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984", "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
    "0xd533a949740bb3306d119cc777fa900ba034cd52", "0x4e3fbd56cd56c3e72c1403e103b45db9da5b9d2b",
    "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "0x0000000000000000000000000000000000000000",
    "0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf", "0x18084fba666a33d37592fa2633fd49a74dd93a88",
    "0x8236a87084f8b84306f72007f36f2618a5634494", "0xc96de26018a54d51c097160568752c4e3bd6c364",
}
TOKEN_NAMES = re.compile(r"^(FiatToken\w*|TetherToken|WETH9|Dai|WBTC|Lido|WstETH|RocketTokenRETH|StakedTokenV1|"
                         r"FRAXStablecoin|LUSDToken|USDe|StakedUSDe\w*|EETH|WeETH|GhoToken|PYUSD\w*)$")

LIB_PATH = re.compile(r"(^|/)(@openzeppelin|openzeppelin-contracts[^/]*|lib/|node_modules|solmate|solady|"
                      r"@uniswap|@balancer-labs|@chainlink|@aave|forge-std|@layerzerolabs|@morpho-org|"
                      r"interfaces?/|libraries/)", re.I)

# (family label, pattern on contract name, pattern on source/paths)
FAMILIES = [
    ("Uniswap V2", r"^(UniswapV2(Pair|Factory|Router0?2?)|\w*Pair)$", r"MINIMUM_LIQUIDITY.*\n[\s\S]*function getReserves\(\)|IUniswapV2Callee"),
    ("Uniswap V3", r"^(UniswapV3(Pool|Factory)|NonfungiblePositionManager)$", r"SqrtPriceMath|IUniswapV3PoolActions|TickBitmap"),
    ("Uniswap V4", r"^PoolManager$", r"IPoolManager|v4-core"),
    ("Curve (Vyper)", r"(StableSwap|Curve|CurveTokenV\d|LiquidityGauge|Vyper_contract)", r"@version|StableSwap"),
    ("Balancer V2", r"(WeightedPool|ComposableStablePool|Vault)$", r"@balancer-labs|IBasePool"),
    ("Compound V2", r"^(CErc20\w*|CEther|Comptroller\w*|Unitroller)$", r"CTokenInterface|ComptrollerInterface"),
    ("Compound III (Comet)", r"^(Comet\w*|Configurator)$", r"CometMainInterface|CometCore"),
    ("Aave V2/V3", r"^(AToken|LendingPool|Pool|PoolInstance|VariableDebtToken\w*)$", r"IPoolAddressesProvider|ILendingPoolAddressesProvider"),
    ("Morpho / MetaMorpho", r"^(MetaMorpho\w*|Morpho\w*|VaultV2)$", r"IMetaMorpho|IMorpho\b|morpho-blue"),
    ("Euler V2 (EVK / Earn)", r"^(EVault|EulerEarn|GenericFactory)$", r"IEVC|ethereum-vault-connector|EVCUtil"),
    ("Yearn", r"^(Vault|VaultV3|Yearn\w*|TokenizedStrategy)$", r"yearn|ITokenizedStrategy|@version"),
    ("Gnosis Safe", r"^(GnosisSafe\w*|Safe\w*Proxy|SafeL2|Safe)$", r"GnosisSafe|ISafe\b"),
    ("Synthetix StakingRewards", r"^StakingRewards\w*$", r"RewardsDistributionRecipient"),
    ("MasterChef (Sushi)", r"^MasterChef\w*$", r"MasterChef"),
    ("Convex", r"^(BaseRewardPool\w*|Booster)$", r"IConvex|BaseRewardPool"),
    ("Liquity", r"^(TroveManager|BorrowerOperations|StabilityPool)$", r"ITroveManager"),
    ("MakerDAO", r"^(Vat|Jug|DssPsm|Pot|Join\w*)$", r"VatLike"),
    ("LayerZero OFT", r"(OFT\w*|ProxyOFT\w*)$", r"@layerzerolabs|OFTCore"),
    ("Pendle", r"^(PendleMarket\w*|PendleYieldToken\w*)$", r"IPMarket|PendleERC20"),
    ("Spark / sUSDS", r"^(SUsds|SavingsDai)$", r"ISUsds"),
]
ERC4626_RE = re.compile(r"\bERC4626(Upgradeable)?\b")
PROXY_NAMES = re.compile(r"(TransparentUpgradeableProxy|ERC1967Proxy|BeaconProxy|InitializableImmutableAdminUpgradeabilityProxy|"
                         r"AdminUpgradeabilityProxy|UUPSProxy|\w*Proxy)$")

_lock = threading.Lock()
_last = [0.0]


def throttle(rate=4.0):
    with _lock:
        wait = _last[0] + 1.0 / rate - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()


_raw_get = etherscan._get


def _throttled_get(url, retries=5):
    throttle()
    return _raw_get(url, retries)


etherscan._get = _throttled_get  # every Etherscan call (incl. slot reads) goes through the limiter


def get_code(addr):
    q = urllib.parse.urlencode({"chainid": 1, "module": "proxy", "action": "eth_getCode", "address": addr,
                                "tag": "latest", "apikey": os.environ["ETHERSCAN_API_KEY"]})
    try:
        r = etherscan._get(f"{etherscan.ETHERSCAN_V2}?{q}").get("result", "")
        return r if isinstance(r, str) else ""
    except etherscan.ExplorerError:
        return ""


def fetch(addr):
    try:
        return etherscan.fetch_source(addr, "eth"), None
    except etherscan.ExplorerError as e:
        return None, str(e)


def own_share(src):
    tot = own = 0
    for path, text in src.files.items():
        n = text.count("\n") + 1
        tot += n
        if not LIB_PATH.search(path):
            own += n
    return (own / tot) if tot else 0.0, tot, own


def classify(src):
    """FORK/STANDAARD only on a contract-NAME match with a known family (imports alone = integration).
    Templates (OZ-only, ERC-4626) only when the own code is small in absolute lines."""
    name = src.contract_name
    blob = "\n".join(src.files.values())
    paths = " ".join(src.files)
    share, lines, own_lines = own_share(src)
    for fam, name_re, src_re in FAMILIES:
        if re.search(name_re, name) and re.search(src_re, blob + paths):
            return f"FORK/STANDAARD: {fam}", share, lines
    if TOKEN_NAMES.match(name):
        return "STANDAARD: bekende token", share, lines
    if ERC4626_RE.search(blob) and own_lines < 300:
        return "STANDAARD-template: ERC-4626 vault (OpenZeppelin/solmate)", share, lines
    if own_lines < 150 and re.search(r"@openzeppelin", paths):
        return "STANDAARD-template: OpenZeppelin-only (dunne eigen laag)", share, lines
    # "integreert X" only from import statements and file paths, not from generic code terms
    imports = "\n".join(re.findall(r"^\s*import\s[^;]+;", blob, re.M)) + " " + paths
    integrates = [fam for fam, _, src_re in FAMILIES if re.search(src_re, imports)]
    return ("EIGEN CODE" + (f" (integreert {', '.join(integrates[:2])})" if integrates else "")), share, lines


def reclassify():
    """Re-run the classifier on already-inventoried, verified protocols (re-fetches their source)."""
    done = json.load(open(OUT))
    for name, rec in done.items():
        if rec.get("verified") != "ja" or not rec.get("class", "").startswith(("EIGEN", "FORK", "STANDAARD")):
            continue
        addr = rec.get("implementation") or rec.get("address")
        src, err = fetch(addr)
        if not src:
            continue
        cls, share, lines = classify(src)
        if cls != rec["class"]:
            print(f"{name[:28]:28} {rec['class'][:45]:45} -> {cls[:60]}")
        rec.update(**{"class": cls}, own_share=round(share, 2), lines=lines)
        json.dump(done, open(OUT, "w"), indent=1)


def inventory(row, cand_addrs, token_addr):
    rec = {"protocol": row["name"], "category": row["cat"], "candidates": cand_addrs[:4],
           "address": "", "verified": "", "proxy": "", "contract": "", "implementation": "",
           "class": "", "compiler": "", "own_share": None, "note": ""}
    if row["cat"] == "CEX":
        rec.update(verified="n.v.t.", note="CEX (geen on-chain protocolcontract)")
        rec["class"] = "n.v.t. (CEX)"
        return rec
    tried = []
    chosen = None
    pool = [a for a in cand_addrs if a not in KNOWN_TOKENS][:4]
    fallback_token = token_addr if token_addr and token_addr not in KNOWN_TOKENS else None
    if not pool:
        rec.update(verified="—", **{"class": "ADRES ONBEKEND"},
                   note=("alleen governance-token gevonden (" + fallback_token + "); protocollogica-adres onbekend")
                   if fallback_token else "geen contractadres in DeFiLlama-adapter")
        return rec
    for addr in pool:
        src, err = fetch(addr)
        tried.append((addr, src, err))
        if src and not TOKEN_NAMES.match(src.contract_name):
            chosen = (addr, src)
            if addr != fallback_token:
                break
    if not chosen:
        verified = [t for t in tried if t[1]]
        if verified:
            chosen = (verified[0][0], verified[0][1])
            rec["note"] = "alleen een (token)contract gevonden"
    if not chosen:
        if not tried:
            rec.update(verified="—", **{"class": "ADRES ONBEKEND"})
            return rec
        addr = tried[0][0]
        code = get_code(addr)
        rec["address"] = addr
        if code in ("0x", ""):
            rec.update(verified="—", **{"class": "ADRES ONBEKEND"},
                       note="kandidaat-adressen zijn EOA's/niet op Ethereum")
        else:
            rec.update(verified="NEE", **{"class": "GEEN VERIFIED SOURCE"},
                       note="contract met bytecode, maar niet geverifieerd op Etherscan")
        return rec

    addr, src = chosen
    rec.update(address=addr, verified="ja", contract=src.contract_name, compiler=src.compiler_raw)
    # Explicit on-chain liveness: the scanned entry point must actually have deployed bytecode right now,
    # so a later finding is about live code (not a self-destructed / never-deployed verified address).
    rec["live"] = get_code(addr) not in ("0x", "")
    if fallback_token and addr == fallback_token and not rec["note"]:
        rec["note"] = "token-adres uit DeFiLlama (geen adapter-adres)"
    # proxy → implementation (storage slot first, explorer second)
    is_proxy = src.is_proxy or bool(PROXY_NAMES.search(src.contract_name))
    impl, slot = etherscan.read_impl_slot(addr, "eth")
    impl = impl or (src.implementation if src.is_proxy else "")
    if is_proxy or impl:
        rec["proxy"] = "ja" + (f" ({slot})" if slot else "")
        if not impl:
            rec.update(**{"class": "PROXY (implementation niet bepaald)"},
                       note="proxy herkend, maar geen implementation-slot/beacon/explorer-implementation gevonden")
            return rec
        if impl:
            isrc, ierr = fetch(impl)
            rec["implementation"] = impl
            if isrc:
                src = isrc
                rec["contract"] = f"{rec['contract']} → {isrc.contract_name}"
                rec["compiler"] = isrc.compiler_raw
            else:
                rec.update(**{"class": "GEEN VERIFIED SOURCE (implementation)"}, note=f"implementation niet geverifieerd: {ierr}")
                return rec
    else:
        rec["proxy"] = "nee"
    cls, share, lines = classify(src)
    rec.update(**{"class": cls}, own_share=round(share, 2), lines=lines, language=src.language)
    return rec


def main():
    if not os.environ.get("ETHERSCAN_API_KEY"):
        sys.exit("ETHERSCAN_API_KEY ontbreekt (source ~/.zshrc)")
    rows = json.load(open(os.path.join(HERE, "list.json")))
    adapter = json.load(open(os.path.join(HERE, "adapter_addrs.json")))
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    limit = int(os.environ.get("INVENTORY_LIMIT", "0")) or len(rows)
    for i, row in enumerate(rows[:limit], 1):
        if row["name"] in done:
            continue
        tok = (row.get("address") or "")
        tok = tok.split(":")[-1].lower() if tok else ""
        tok = tok if re.fullmatch(r"0x[0-9a-f]{40}", tok) else ""
        try:
            rec = inventory(row, adapter.get(row["name"], {}).get("addrs", []), tok)
        except Exception as e:  # keep going; record honestly
            rec = {"protocol": row["name"], "category": row["cat"], "class": "FOUT", "note": str(e)[:200]}
        done[row["name"]] = rec
        json.dump(done, open(OUT, "w"), indent=1)
        print(f"[{i}/{len(rows)}] {row['name'][:30]:30} {rec.get('class','')[:60]}", flush=True)


if __name__ == "__main__":
    if "--reclassify" in sys.argv:
        reclassify()
    else:
        main()
