"""Generate a Foundry invariant project for one live contract.

Layout (per target):  fuzz-work/<name>/
    foundry.toml          runs / depth / fork cache settings
    test/Invariants.t.sol generated: Funder + HandlerBase + Handler + FuzzInvariants (regenerated each run)
    test/Custom.t.sol     FuzzCustom extends FuzzInvariants — your own invariant_*() go here (never overwritten)
    target.json           what was generated (type, markets, privileged functions, fork block)
forge-std is shared in fuzz-work/_lib/forge-std.
"""
from __future__ import annotations

import json
import os
import re
import subprocess

from eth_utils import keccak, to_checksum_address

from solscan.evm import etherscan
from solscan.evm.fuzz import detect, templates
from solscan.evm.fuzz.chain import Chain, fetch_abi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WORK = os.path.join(REPO, "fuzz-work")
FORGE_STD = os.path.join(WORK, "_lib", "forge-std")


class GenError(RuntimeError):
    pass


def ensure_forge_std() -> str:
    if not os.path.isdir(os.path.join(FORGE_STD, "src")):
        os.makedirs(os.path.dirname(FORGE_STD), exist_ok=True)
        r = subprocess.run(["git", "clone", "--depth", "1", "https://github.com/foundry-rs/forge-std", FORGE_STD],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise GenError(f"forge-std ophalen faalde: {r.stderr[-300:]}")
    return FORGE_STD


def _event_sig(ev: dict) -> str:
    def t(i):
        return "(" + ",".join(t(c) for c in i["components"]) + ")" if i["type"] == "tuple" else i["type"]
    return f"{ev['name']}(" + ",".join(t(i) for i in ev["inputs"]) + ")"


def lender_markets(chain: Chain, address: str, abi: list) -> list[dict]:
    """Markets from CreateMarket(Id indexed id, MarketParams marketParams) logs (read-only)."""
    ev = next((e for e in abi if e.get("type") == "event" and e["name"] == "CreateMarket"), None)
    if not ev:
        raise GenError("lender zonder CreateMarket-event: markten niet te bepalen (geef --markets op)")
    comps = next(i for i in ev["inputs"] if i["type"] == "tuple")["components"]
    if any(not detect.STATIC.match(c["type"]) for c in comps):
        raise GenError("MarketParams met dynamische velden wordt niet ondersteund")
    topic0 = "0x" + keccak(text=_event_sig(ev)).hex()
    out = []
    for log in chain.logs(address, topic0):
        words = [log["data"][2 + 64 * i: 2 + 64 * (i + 1)] for i in range(len(comps))]
        vals = {}
        for c, w in zip(comps, words):
            vals[c["name"]] = ("0x" + w[24:]) if c["type"] == "address" else int(w, 16)
        out.append({"id": log["topics"][1], "params": vals, "block": int(log["blockNumber"], 16)})
    if not out:
        raise GenError("geen markten gevonden in CreateMarket-logs")
    return out


def supplier_role(chain: Chain, address: str, market: dict, fnames: dict) -> str:
    """Who may supply in this market: a `whitelist` struct field (Fira) or the first entry of
    getWhiteList(id) (Moolah). Empty = anyone. The handler simulates this address as a privileged role."""
    wl = market["params"].get("whitelist")
    if isinstance(wl, str) and int(wl, 16):
        return wl
    if "getWhiteList" in fnames:
        r = chain.call(address, "getWhiteList(bytes32)", market["id"])
        if r and len(r) >= 130 and int(r[66:130], 16) > 0:
            return "0x" + r[130 + 24:130 + 64]
    return ""


def collateral_role(chain: Chain, address: str, market: dict, fnames: dict) -> str:
    """Provider that must deposit collateral on behalf of users (Moolah: providers(id, token)). Empty = user."""
    if "providers" not in fnames:
        return ""
    tok = market["params"].get("collateralToken")
    r = chain.call(address, "providers(bytes32,address)", market["id"], tok)
    return ("0x" + r[-40:]) if r and len(r) >= 66 and int(r, 16) else ""


def _sol_value(c: dict, v) -> str:
    if c["type"] == "address":
        return to_checksum_address(v)
    if c["type"] == "bool":
        return "true" if v else "false"
    return str(v)


def render(kind: str, target: str, block: int, invariants: list[str], actors: int, fund: int,
           markets: list[dict] | None, comps: list[dict] | None, priv: list[dict], fee_bps: int,
           warp: bool, tol: int, price_via_target: bool = False, min_loan_via_target: bool = False) -> str:
    handler, inv_lib, test, actions, warp_actions = templates.TEMPLATES[kind]
    h = handler.replace("__FUND__", str(fund)).replace("__FEE_BPS__", str(fee_bps))

    if kind == "lender":
        fields = "\n".join(f"        {c['type']} {c['name']};" for c in comps)
        h = h.replace("__STRUCT__", f"    struct MarketParams {{\n{fields}\n    }}")
        extra = []
        if min_loan_via_target:
            extra.append("    function minLoan(MarketParams memory) external view returns (uint256);")
            h = h.replace("__MINLOAN_EXPR__", "try T.minLoan(mp) returns (uint256 x) { v = x; } catch { v = 1; }")
        else:
            h = h.replace("__MINLOAN_EXPR__", "mp; v = 1;")
        if price_via_target:
            extra.append("    function getPrice(MarketParams memory) external view returns (uint256);")
        h = h.replace("__EXTRA_IFACE__", "\n".join(extra))
        if price_via_target:
            h = h.replace("__PRICE_EXPR__", "try T.getPrice(mp) returns (uint256 v) { p = v; } catch { p = 0; }")
        else:
            h = h.replace("__PRICE_EXPR__", "try IPriceOracle(mp.oracle).price() returns (uint256 v) { p = v; } catch { p = 0; }")
        lines = []
        for m in markets:
            args = ", ".join(_sol_value(c, m["params"][c["name"]]) for c in comps)
            role = m.get("supplier_role") or "0x0000000000000000000000000000000000000000"
            lines.append(f"        mkts.push(ILender.MarketParams({args}));")
            lines.append(f"        ids.push({m['id']});")
            lines.append(f"        supplierRole.push({to_checksum_address(role)});")
            prov = m.get("collateral_role") or "0x0000000000000000000000000000000000000000"
            lines.append(f"        collateralRole.push({to_checksum_address(prov)});")
        h = h.replace("__MARKETS__", "\n".join(lines))

    plines = []
    for f in priv:
        sel = "0x" + keccak(text=f"{f['name']}(" + ",".join(i["type"] for i in f["inputs"]) + ")")[:4].hex()
        plines.append(f"        privSelectors.push({sel}); privArgTypes.push({len(f['inputs'])}); "
                      f"privNames.push(\"{f['name']}\");")
    h = h.replace("__PRIV__", "\n".join(plines))

    chosen = [i for i in invariants if i in inv_lib]
    inv_code = "\n".join(inv_lib[i] for i in chosen)
    sel_names = actions + (warp_actions if warp else []) + (["tryPrivileged"] if "access" in chosen and priv else [])
    sel_lines = "\n".join(f"        sel[{k}] = {'HandlerBase' if n in ('tryPrivileged', 'warpTime') else 'Handler'}.{n}.selector;"
                          for k, n in enumerate(sel_names))
    t = (test.replace("__INVARIANTS__", inv_code).replace("__BLOCK__", str(block))
         .replace("__TARGET__", to_checksum_address(target)).replace("__ACTORS__", str(actors))
         .replace("__NSEL__", str(len(sel_names))).replace("__SELECTORS__", sel_lines)
         .replace("__TOL__", str(tol))
         .replace("__CONSOLE__", 'console2.log(string.concat("[actie] ", n, " ok/geprobeerd:"), ok, tried);'))
    common = templates.COMMON.replace('import {Test} from "forge-std/Test.sol";',
                                      'import {Test} from "forge-std/Test.sol";\nimport {console2} from "forge-std/console2.sol";')
    return common + h + t


def foundry_toml(runs: int, depth: int) -> str:
    return f"""[profile.default]
src = "test"
test = "test"
out = "out"
libs = ["../_lib"]
remappings = ["forge-std/=../_lib/forge-std/src/"]
optimizer = true
optimizer_runs = 200
via_ir = false
rpc_storage_caching = {{ chains = "all", endpoints = "all" }}
fs_permissions = [{{ access = "read-write", path = "./" }}]
eth_rpc_timeout = 600
no_rpc_rate_limit = true
# setUp funds actors inside the handler constructor (deal's slot search on e.g. stETH is gas-heavy):
# lift the fork's block gas limit for the test environment only.
disable_block_gas_limit = true
gas_limit = "18446744073709551615"

[invariant]
runs = {runs}
depth = {depth}
fail_on_revert = false
call_override = false
shrink_run_limit = 2000
show_metrics = true
"""


def generate(address: str, name: str, chain="eth", rpc: str | None = None, kind: str = "auto",
             invariants: list[str] | None = None, actors: int = 4, fund: int = 10**24, runs: int = 32,
             depth: int = 40, block: int | None = None, warp: bool = False, fee_bps: int = 100,
             tol: int = 1000, privileged: list[str] | None = None) -> dict:
    ch = Chain(chain, rpc)
    logic = address
    impl_note = ""
    try:
        src = etherscan.fetch_source(address, chain)
    except etherscan.ExplorerError:
        # target itself unverified: if it is a proxy with a resolvable, verified implementation, use that for
        # source/ABI while still forking and calling the proxy (where the state and funds live).
        slot_impl, slot = etherscan.read_impl_slot(address, chain)
        if not slot_impl:
            raise
        logic = slot_impl
        impl_note = f"proxy → {logic} (bevestigd via {slot}; proxy zelf niet geverifieerd)"
        src = etherscan.fetch_source(logic, chain)
    if logic == address and src.is_proxy and src.implementation:
        slot_impl, slot = etherscan.read_impl_slot(address, chain)
        logic = slot_impl or src.implementation
        impl_note = f"proxy → {logic}" + (f" (bevestigd via {slot})" if slot_impl else " (explorer, slot niet bevestigd)")
        src = etherscan.fetch_source(logic, chain)
    abi = fetch_abi(logic, chain)
    kind = detect.classify(abi) if kind == "auto" else kind
    if kind not in templates.TEMPLATES:
        raise GenError(f"contracttype '{kind}' niet ondersteund (lender/vault/amm/token); geef --type op")
    invariants = invariants or detect.DEFAULT_INVARIANTS[kind]
    if warp:
        warp_safe = []
        for inv in invariants:
            if inv in ("no-free-withdraw", "conservation", "k-monotonic"):
                continue   # yield/interest makes these move legitimately once time passes
            warp_safe.append("attacker-profit-warp" if inv == "attacker-profit" else inv)
        invariants = warp_safe

    priv = detect.privileged_functions(abi, src.files)
    if privileged:
        by = {f["name"]: f for f in abi if f.get("type") == "function"}
        priv = [by[n] for n in privileged if n in by]

    markets = comps = None
    price_via_target = min_loan_via_target = False
    if kind == "lender":
        comps = detect.struct_components(abi, "supply")
        markets = lender_markets(ch, address, abi)
        fnames = {f["name"]: f for f in abi if f.get("type") == "function"}
        # price: the target's own getPrice(MarketParams) if it has one (Moolah), else Morpho's oracle.price()
        gp = fnames.get("getPrice")
        price_via_target = bool(gp and gp["inputs"] and gp["inputs"][0]["type"] == "tuple")
        ml = fnames.get("minLoan")
        min_loan_via_target = bool(ml and ml["inputs"] and ml["inputs"][0]["type"] == "tuple")
        for m in markets:
            m["supplier_role"] = supplier_role(ch, address, m, fnames)
            m["collateral_role"] = collateral_role(ch, address, m, fnames)

    block = block or (ch.block_number() - 5)
    code = render(kind, address, block, invariants, actors, fund, markets, comps, priv, fee_bps, warp, tol,
                  price_via_target, min_loan_via_target)

    proj = os.path.join(WORK, re.sub(r"[^a-zA-Z0-9_-]", "-", name))
    os.makedirs(os.path.join(proj, "test"), exist_ok=True)
    ensure_forge_std()
    with open(os.path.join(proj, "foundry.toml"), "w") as f:
        f.write(foundry_toml(runs, depth))
    with open(os.path.join(proj, "test", "Invariants.t.sol"), "w") as f:
        f.write(code)
    controls = "".join(templates.CONTROLS[i][kind] for i in invariants
                       if i in templates.CONTROLS and kind in templates.CONTROLS[i])
    with open(os.path.join(proj, "test", "Control.t.sol"), "w") as f:
        f.write(templates.CONTROL.replace("__CONTROLS__", controls))
    custom = os.path.join(proj, "test", "Custom.t.sol")
    if not os.path.exists(custom):
        with open(custom, "w") as f:
            f.write(templates.CUSTOM_STUB)
    meta = {"name": name, "address": address, "logic": logic, "proxy": impl_note, "contract": src.contract_name,
            "chain_id": ch.cid, "type": kind, "invariants": invariants, "block": block, "actors": actors,
            "runs": runs, "depth": depth, "warp": warp,
            "privileged": [f["name"] for f in priv],
            "price_source": ("target.getPrice(MarketParams)" if price_via_target else "oracle.price()") if kind == "lender" else "",
            "markets": [{"id": m["id"], "supplier_role": m.get("supplier_role", ""),
                         "collateral_role": m.get("collateral_role", ""),
                         **{k: str(v) for k, v in m["params"].items()}} for m in (markets or [])]}
    with open(os.path.join(proj, "target.json"), "w") as f:
        json.dump(meta, f, indent=1)
    meta["project"] = proj
    meta["rpc_url"] = ch.url
    return meta
