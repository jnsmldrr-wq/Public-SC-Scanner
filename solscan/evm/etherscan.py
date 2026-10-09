"""
Fetch verified source code per address (read-only), multi-chain.

Primary: Etherscan API v2 (one endpoint for all chains, `chainid=` parameter, needs an API key).
Fallback without a key: Blockscout, which serves an Etherscan-compatible `getsourcecode` API,
so the same parser is used.

Verified source = the explorer recompiled it and matched the deployed bytecode, so you know
the source IS the live code (no sourcecheck step needed, unlike Solana).
"""
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"

CHAINS = {  # name -> chain id
    "eth": 1, "ethereum": 1, "mainnet": 1, "sepolia": 11155111, "holesky": 17000,
    "bsc": 56, "polygon": 137, "arbitrum": 42161, "arb": 42161, "optimism": 10, "op": 10,
    "base": 8453, "avalanche": 43114, "avax": 43114, "linea": 59144, "scroll": 534352,
    "blast": 81457, "gnosis": 100, "fantom": 250, "zksync": 324, "mantle": 5000,
    "celo": 42220, "sonic": 146, "unichain": 130, "berachain": 80094,
}
BLOCKSCOUT = {  # chain id -> Etherscan-compatible API base (no key needed)
    1: "https://eth.blockscout.com/api", 11155111: "https://eth-sepolia.blockscout.com/api",
    10: "https://optimism.blockscout.com/api", 8453: "https://base.blockscout.com/api",
    42161: "https://arbitrum.blockscout.com/api", 100: "https://gnosis.blockscout.com/api",
    137: "https://polygon.blockscout.com/api", 534352: "https://scroll.blockscout.com/api",
    59144: "https://explorer.linea.build/api", 324: "https://zksync.blockscout.com/api",
    42220: "https://celo.blockscout.com/api",
}

ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class ExplorerError(RuntimeError):
    pass


@dataclass
class VerifiedSource:
    address: str
    chain_id: int
    contract_name: str
    compiler: str                 # e.g. "0.8.24" ("" for Vyper/unknown)
    compiler_raw: str             # as reported, e.g. "v0.8.24+commit.e11b9ed9"
    files: dict                   # path -> source text
    remappings: list = field(default_factory=list)
    optimizer: bool = False
    optimizer_runs: int = 200
    evm_version: str = ""
    is_proxy: bool = False
    implementation: str = ""
    language: str = "Solidity"
    source_api: str = ""          # which explorer answered
    key_source: str = ""          # where the API key came from (never the key itself)


def chain_id(chain: str | int) -> int:
    if isinstance(chain, int) or str(chain).isdigit():
        return int(chain)
    try:
        return CHAINS[str(chain).lower()]
    except KeyError:
        raise ExplorerError(f"onbekende chain '{chain}'. Bekend: {', '.join(sorted(set(CHAINS)))} of een chain-id")


def _ctx():
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats()["x509_ca"] and os.path.exists("/etc/ssl/cert.pem"):
        ctx = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ctx


def _get(url: str, retries: int = 5) -> dict:
    last = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "solscan-evm/1.0"})
            with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
                data = json.loads(r.read().decode())
            msg = str(data.get("result", "")) if isinstance(data.get("result"), str) else ""
            if "rate limit" in msg.lower() or "max calls" in msg.lower():
                last = msg
                time.sleep(1.5 * (attempt + 1))
                continue
            return data
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code == 429 or e.code >= 500:   # rate limit / server error: back off and retry
                wait = e.headers.get("Retry-After")
                time.sleep(min(float(wait) if wait and wait.isdigit() else 5.0 * (attempt + 1), 30))
                continue
            break
        except Exception as e:  # network/JSON errors: retry, then report honestly
            last = str(e)
            time.sleep(1.0 * (attempt + 1))
    raise ExplorerError(f"explorer niet bereikbaar: {last}")


def _sanitize(path: str) -> str:
    p = path.replace("\\", "/").lstrip("/")
    parts = [x for x in p.split("/") if x not in ("", ".", "..")]
    return "/".join(parts) or "Contract.sol"


def _strip_machine_prefix(files: dict) -> dict:
    """Drop a shared absolute-path prefix from the deployer's machine (Users/<name>/..., home/...).

    Only the common prefix of the non-package paths is removed, identically for every file,
    so relative imports keep working. Package paths (@openzeppelin/...) are left alone.
    """
    local = [k for k in files if not k.startswith("@") and "/" in k]
    if len(local) < 1:
        return files
    first = local[0].split("/")[0]
    if first not in ("Users", "home", "root", "mnt", "tmp", "private", "var", "workspace", "app"):
        return files
    parts = [k.split("/")[:-1] for k in local]
    common = []
    for segs in zip(*parts):
        if len(set(segs)) != 1:
            break
        common.append(segs[0])
    # keep the project's own top-level dir (e.g. contracts/) rather than stripping everything
    if "contracts" in common:
        common = common[:common.index("contracts")]
    if not common:
        return files
    pre = "/".join(common) + "/"
    return {(k[len(pre):] if k.startswith(pre) else k): v for k, v in files.items()}


def parse_source_field(source: str, contract_name: str) -> tuple[dict, dict]:
    """Return (files, settings) from an explorer `SourceCode` field (all three formats)."""
    s = (source or "").strip()
    if s.startswith("{{") and s.endswith("}}"):
        s = s[1:-1]  # Etherscan wraps standard-JSON input in an extra pair of braces
    if s.startswith("{"):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict):
            sources = obj.get("sources", obj)
            files = {_sanitize(k): (v.get("content", "") if isinstance(v, dict) else str(v))
                     for k, v in sources.items()}
            return files, obj.get("settings", {}) if "sources" in obj else {}
    return {f"{contract_name or 'Contract'}.sol": source}, {}


def _parse_result(item: dict, address: str, cid: int, api: str) -> VerifiedSource:
    if not item.get("SourceCode"):
        raise ExplorerError(f"{address} is niet geverifieerd op {api} (geen broncode)")
    name = item.get("ContractName") or "Contract"
    files, settings = parse_source_field(item["SourceCode"], name)
    # Blockscout: main file's real path is in FileName (must be applied BEFORE the
    # AdditionalSources, otherwise relative imports like "./X.sol" break)
    fname = (item.get("FileName") or "").strip()
    if fname and os.path.basename(fname) not in ("", ".sol") and len(files) == 1 and f"{name}.sol" in files:
        files = {_sanitize(fname): files[f"{name}.sol"]}
    for extra in item.get("AdditionalSources") or []:  # Blockscout multi-file format
        if extra.get("Filename") and extra.get("SourceCode"):
            files.setdefault(_sanitize(extra["Filename"]), extra["SourceCode"])
    files = _strip_machine_prefix(files)
    raw = item.get("CompilerVersion") or ""
    lang = "Vyper" if raw.lower().startswith("vyper") else "Solidity"
    m = re.search(r"(\d+\.\d+\.\d+)", raw)
    impl = (item.get("Implementation") or item.get("ImplementationAddress") or "").strip()
    return VerifiedSource(
        address=address, chain_id=cid, contract_name=name,
        compiler=m.group(1) if (m and lang == "Solidity") else "",
        compiler_raw=raw, files=files,
        remappings=list(settings.get("remappings", []) or []),
        optimizer=str(item.get("OptimizationUsed", "0")) in ("1", "true", "True")
        or bool((settings.get("optimizer") or {}).get("enabled")),
        optimizer_runs=int((settings.get("optimizer") or {}).get("runs")
                           or (str(item.get("Runs") or "").isdigit() and item.get("Runs")) or 200),
        evm_version=re.sub(r"^default$", "", (settings.get("evmVersion") or item.get("EVMVersion") or "").strip().lower()),
        is_proxy=str(item.get("Proxy", "0")) in ("1", "true", "True") or bool(ADDRESS_RE.match(impl)),
        implementation=impl if ADDRESS_RE.match(impl) else "",
        language=lang, source_api=api,
    )


def fetch_source(address: str, chain: str | int = "eth", api_key: str | None = None) -> VerifiedSource:
    if not ADDRESS_RE.match(address):
        raise ExplorerError(f"ongeldig adres: {address}")
    cid = chain_id(chain)
    key_source = "--api-key" if api_key else ("ETHERSCAN_API_KEY (env)" if os.environ.get("ETHERSCAN_API_KEY") else "")
    api_key = api_key or os.environ.get("ETHERSCAN_API_KEY")
    errors = []
    if api_key:
        q = urllib.parse.urlencode({"chainid": cid, "module": "contract", "action": "getsourcecode",
                                    "address": address, "apikey": api_key})
        data = _get(f"{ETHERSCAN_V2}?{q}")
        if str(data.get("status")) == "1" and isinstance(data.get("result"), list) and data["result"]:
            src = _parse_result(data["result"][0], address, cid, "etherscan-v2")
            src.key_source = key_source
            return src
        # never echo the request URL (it contains the key); only the explorer's message
        errors.append(f"etherscan-v2 ({key_source}): {data.get('message')} — {str(data.get('result'))[:160]}")
    base = BLOCKSCOUT.get(cid)
    if base:
        q = urllib.parse.urlencode({"module": "contract", "action": "getsourcecode", "address": address})
        data = _get(f"{base}?{q}")
        if isinstance(data.get("result"), list) and data["result"]:
            src = _parse_result(data["result"][0], address, cid, "blockscout")
            src.key_source = "geen (keyless fallback)" + (f"; etherscan faalde: {errors[-1]}" if errors else "")
            return src
        errors.append(f"blockscout: {data.get('message')}")
    elif not api_key:
        errors.append(f"geen API-key en geen keyless Blockscout-instantie voor chain {cid}")
    raise ExplorerError("; ".join(errors) or "geen broncode gevonden")


def write_tree(src: VerifiedSource, out_dir: str) -> str:
    """Write all source files under out_dir; return the path of the file defining the main contract."""
    main = None
    decl = re.compile(rf"\b(contract|library|interface|abstract\s+contract)\s+{re.escape(src.contract_name)}\b")
    for rel, text in src.files.items():
        path = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        if main is None and decl.search(text):
            main = path
    if main is None:
        main = os.path.join(out_dir, next(iter(src.files)))
    return main


def base_path_args(version: str) -> list:
    """`--base-path .` is only reliable from solc 0.8.8; older solc crashes with it in
    combination with --combined-json ast ("Given source file not found") and resolves
    non-relative imports from the working directory anyway."""
    try:
        v = tuple(int(x) for x in version.split(".")[:3])
    except ValueError:
        v = (0, 8, 8)
    return (["--base-path", "."] if v >= (0, 8, 8) else []) + ["--allow-paths", "."]


def solc_args_for(src: VerifiedSource) -> str:
    """solc arguments that reproduce the verified build (base path + optimizer + EVM version)."""
    args = base_path_args(src.compiler)
    if src.optimizer:
        args += ["--optimize", "--optimize-runs", str(src.optimizer_runs)]
    if src.evm_version and re.fullmatch(r"[a-z]+", src.evm_version):
        args += ["--evm-version", src.evm_version]
    return " ".join(args)


# Proxy implementation storage slots (read-only check via eth_getStorageAt)
BEACON_SLOT = "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
IMPL_SLOTS = {
    "EIP-1967": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
    "ZeppelinOS (legacy)": "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",
    "EIP-1822 (UUPS proxiable)": "0xc5f16f0fcc639fa48a6947836d9850f504798523bf8c9a3a87d5876cf622bcf7",
}


def read_impl_slot(address: str, chain: str | int = "eth", api_key: str | None = None) -> tuple[str, str]:
    """Return (implementation, slot_name) read from a proxy storage slot, or ("", "") if none / no key.

    Uses Etherscan v2's proxy module (eth_getStorageAt) — a read-only RPC call.
    """
    api_key = api_key or os.environ.get("ETHERSCAN_API_KEY")
    if not api_key:
        return "", ""
    cid = chain_id(chain)
    def storage(slot):
        q = urllib.parse.urlencode({"chainid": cid, "module": "proxy", "action": "eth_getStorageAt",
                                    "address": address, "position": slot, "tag": "latest", "apikey": api_key})
        try:
            val = str(_get(f"{ETHERSCAN_V2}?{q}").get("result") or "")
        except ExplorerError:
            return ""
        return "0x" + val[-40:] if re.fullmatch(r"0x[0-9a-fA-F]{64}", val) and int(val, 16) != 0 else ""

    for name, slot in IMPL_SLOTS.items():
        impl = storage(slot)
        if impl:
            return impl, name
    # EIP-1967 beacon proxy: slot holds the beacon; ask the beacon for implementation() (read-only eth_call)
    beacon = storage(BEACON_SLOT)
    if beacon:
        q = urllib.parse.urlencode({"chainid": cid, "module": "proxy", "action": "eth_call", "to": beacon,
                                    "data": "0x5c60da1b", "tag": "latest", "apikey": api_key})
        try:
            val = str(_get(f"{ETHERSCAN_V2}?{q}").get("result") or "")
        except ExplorerError:
            val = ""
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", val) and int(val, 16) != 0:
            return "0x" + val[-40:], f"EIP-1967 beacon {beacon}"
    return "", ""
