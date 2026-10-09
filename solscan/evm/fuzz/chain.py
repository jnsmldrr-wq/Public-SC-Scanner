"""Read-only chain access for the fuzz generator: ABI, eth_call, logs, block number.

Prefers a JSON-RPC endpoint (ETH_RPC_URL or --rpc); falls back to Etherscan v2's proxy module.
Only view calls (eth_call / eth_getLogs / eth_blockNumber / eth_getCode) — never a transaction.
The Etherscan key is read from ETHERSCAN_API_KEY and never printed.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from eth_utils import keccak

from solscan.evm import etherscan

# Defaults must serve historical state: the fork stays pinned to one block for the whole campaign.
PUBLIC_RPC = {1: "https://eth.drpc.org", 8453: "https://base-rpc.publicnode.com",
              42161: "https://arbitrum-one-rpc.publicnode.com", 10: "https://optimism-rpc.publicnode.com",
              56: "https://bsc-rpc.publicnode.com", 137: "https://polygon-bor-rpc.publicnode.com"}


# Public mainnet nodes that serve historical state AND that anvil accepts as fork upstream (checked
# 2026-10-07: 1rpc.io and rpc.flashbots.net serve old state but fail anvil's genesis requests).
# anvil spreads fork requests over all of them, which keeps a long campaign alive when one times out.
# (rpc.mevblocker.io dropped 2026-10-08: repeated Cloudflare 504s during anvil genesis.)
ARCHIVE_RPCS = {1: ["https://eth.drpc.org", "https://eth-mainnet.public.blastapi.io"]}


def fork_upstreams(chain, override: str | None = None) -> list[str]:
    """Upstream RPCs for the local anvil fork: --rpc / ETH_RPC_URL alone, else all known archive nodes."""
    if override:
        return [override]
    if os.environ.get("ETH_RPC_URL"):
        return [os.environ["ETH_RPC_URL"]]
    cid = etherscan.chain_id(chain)
    return ARCHIVE_RPCS.get(cid) or [rpc_url(chain)]


def rpc_url(chain, override: str | None = None) -> str:
    """The JSON-RPC endpoint used for forking: --rpc, then ETH_RPC_URL, then a public node."""
    if override:
        return override
    if os.environ.get("ETH_RPC_URL"):
        return os.environ["ETH_RPC_URL"]
    cid = etherscan.chain_id(chain)
    if cid not in PUBLIC_RPC:
        raise etherscan.ExplorerError(f"geen publieke RPC bekend voor chain {cid}; zet ETH_RPC_URL of --rpc")
    return PUBLIC_RPC[cid]


def describe_rpc(url: str) -> str:
    """Host only — a private RPC URL often embeds a key in its path."""
    return urllib.parse.urlparse(url).netloc or "rpc"


class Chain:
    def __init__(self, chain="eth", rpc: str | None = None):
        self.cid = etherscan.chain_id(chain)
        self.url = rpc_url(chain, rpc)

    def _rpc(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(self.url, body, {"Content-Type": "application/json",
                                                      "User-Agent": "solscan-fuzz/1.0"})
        last = ""
        for _ in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30, context=etherscan._ctx()) as r:
                    data = json.loads(r.read().decode())
                if "error" in data:
                    last = str(data["error"])[:200]
                    break
                return data.get("result")
            except Exception as e:   # network hiccup: retry, then report
                last = str(e)
        raise etherscan.ExplorerError(f"RPC {describe_rpc(self.url)}: {method} faalde: {last}")

    def block_number(self) -> int:
        try:
            return int(self._rpc("eth_blockNumber", []), 16)
        except etherscan.ExplorerError:   # public node rate-limited: ask Etherscan (read-only)
            key = os.environ.get("ETHERSCAN_API_KEY")
            if not key:
                raise
            q = urllib.parse.urlencode({"chainid": self.cid, "module": "proxy", "action": "eth_blockNumber", "apikey": key})
            return int(etherscan._get(f"{etherscan.ETHERSCAN_V2}?{q}")["result"], 16)

    def code(self, address: str) -> str:
        return self._rpc("eth_getCode", [address, "latest"]) or "0x"

    def call(self, to: str, sig: str, *args, block="latest") -> str:
        data = "0x" + keccak(text=sig)[:4].hex() + "".join(
            format(a, "064x") if isinstance(a, int) else a.lower().removeprefix("0x").rjust(64, "0") for a in args)
        try:
            return self._rpc("eth_call", [{"to": to, "data": data}, block if isinstance(block, str) else hex(block)])
        except etherscan.ExplorerError:
            return "0x"

    def addr(self, to: str, sig: str, *args) -> str:
        r = self.call(to, sig, *args)
        return "0x" + r[-40:] if r and len(r) >= 66 else ""

    def uint(self, to: str, sig: str, *args) -> int | None:
        r = self.call(to, sig, *args)
        return int(r[:66], 16) if r and len(r) >= 66 else None

    def logs(self, address: str, topic0: str, from_block: int = 0, to_block: int | str = "latest") -> list:
        """Logs via Etherscan v2 (key from env, paged), else eth_getLogs chunked on the RPC."""
        key = os.environ.get("ETHERSCAN_API_KEY")
        if key:
            out, page = [], 1
            while True:
                q = urllib.parse.urlencode({"chainid": self.cid, "module": "logs", "action": "getLogs",
                                            "address": address, "topic0": topic0, "fromBlock": from_block,
                                            "toBlock": to_block, "page": page, "offset": 1000, "apikey": key})
                res = etherscan._get(f"{etherscan.ETHERSCAN_V2}?{q}").get("result")
                if not isinstance(res, list):
                    break
                out += res
                if len(res) < 1000:
                    return out
                page += 1
        out, start = [], from_block
        end = self.block_number() if to_block == "latest" else to_block
        step = end - start + 1
        while start <= end:
            stop = min(start + step - 1, end)
            try:
                res = self._rpc("eth_getLogs", [{"address": address, "topics": [topic0],
                                                 "fromBlock": hex(start), "toBlock": hex(stop)}])
                out += res or []
                start = stop + 1
            except etherscan.ExplorerError:
                if step <= 10_000:
                    raise
                step //= 8
        return out


def fetch_abi(address: str, chain="eth", api_key: str | None = None) -> list:
    """Verified ABI via Etherscan v2 (key from env), Blockscout as keyless fallback."""
    cid = etherscan.chain_id(chain)
    key = api_key or os.environ.get("ETHERSCAN_API_KEY")
    if key:
        q = urllib.parse.urlencode({"chainid": cid, "module": "contract", "action": "getabi",
                                    "address": address, "apikey": key})
        data = etherscan._get(f"{etherscan.ETHERSCAN_V2}?{q}")
        if str(data.get("status")) == "1":
            return json.loads(data["result"])
    base = etherscan.BLOCKSCOUT.get(cid)
    if base:
        q = urllib.parse.urlencode({"module": "contract", "action": "getabi", "address": address})
        data = etherscan._get(f"{base}?{q}")
        if str(data.get("status")) == "1":
            return json.loads(data["result"])
    raise etherscan.ExplorerError(f"geen geverifieerde ABI voor {address}")
