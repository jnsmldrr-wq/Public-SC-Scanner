"""Classify a contract from its ABI and find the functions meant to be privileged.

Types (each has a handler template and a default invariant set):
  lender  — Morpho-Blue-style isolated markets (supply/withdraw/borrow/repay/supplyCollateral with a
            MarketParams struct). Covers Morpho Blue and forks (Fira USL, Lista Moolah, ...).
  vault   — ERC-4626 (deposit/mint/withdraw/redeem + asset/totalAssets).
  amm     — Uniswap-V2-style pair (getReserves/swap/mint/burn/token0/token1).
  token   — plain ERC-20 (transfer/transferFrom/approve/balanceOf/totalSupply).
  queuevault — mint + async withdrawal queue with a rebasing oToken (Origin OUSD/OETH vault shape).
  mintredeem — collateral-backed stable with mint/redeem/queue and an MCT collateral book (NaraUSD shape).
  wrapper — Convex-style 1:1 staking wrapper (deposit/stake/withdraw/withdrawAndUnwrap, curveToken/convexPool).
"""
from __future__ import annotations

import re

DEFAULT_INVARIANTS = {
    "lender": ["solvency", "no-free-withdraw", "conservation", "access", "attacker-profit"],
    "vault": ["solvency", "no-free-withdraw", "conservation", "access", "attacker-profit"],
    "amm": ["solvency", "conservation", "k-monotonic", "access", "attacker-profit"],
    "token": ["conservation", "no-free-withdraw", "access", "attacker-profit"],
    "wrapper": ["solvency", "no-free-withdraw", "conservation", "access", "attacker-profit"],
    "mintredeem": ["solvency", "no-free-withdraw", "conservation", "access", "attacker-profit"],
    "queuevault": ["solvency", "no-free-withdraw", "access", "attacker-profit"],
    "sir": ["solvency", "no-free-withdraw", "access", "attacker-profit"],
    "locktoken": ["solvency", "no-free-withdraw", "access", "attacker-profit"],
    "aavebook": ["solvency", "no-free-withdraw", "access", "attacker-profit"],
}
ALL_INVARIANTS = {"solvency", "no-free-withdraw", "conservation", "access", "k-monotonic", "attacker-profit"}


def _fns(abi: list) -> dict:
    return {f["name"]: f for f in abi if f.get("type") == "function"}


def classify(abi: list) -> str:
    fns = _fns(abi)
    names = set(fns)
    if {"supply", "withdraw", "borrow", "repay", "supplyCollateral", "withdrawCollateral"} <= names:
        sup = fns["supply"]["inputs"]
        if sup and sup[0]["type"] == "tuple":
            return "lender"
    if {"deposit", "withdraw", "getUserBalance", "getUserDepositInfo", "factory"} <= names and "claim" not in names:
        return "aavebook"
    if {"deposit", "withdraw", "claim", "cancelWithdraw", "usersBalances", "allowedAssets", "unlockPeriod"} <= names:
        return "locktoken"
    if {"mint", "burn", "numberOfVaults", "paramsById", "totalReserves"} <= names:
        return "sir"
    if {"mint", "requestWithdrawal", "claimWithdrawal", "oToken", "totalValue", "withdrawalClaimDelay"} <= names:
        return "queuevault"
    if {"mintWithCollateral", "redeem", "cancelRedeem", "mct", "redemptionRequests"} <= names:
        return "mintredeem"
    if {"deposit", "withdraw", "withdrawAndUnwrap", "curveToken", "convexPool", "convexToken"} <= names:
        return "wrapper"
    if {"deposit", "withdraw", "redeem", "mint", "asset", "totalAssets", "convertToAssets"} <= names:
        return "vault"
    if {"getReserves", "swap", "mint", "burn", "token0", "token1"} <= names:
        return "amm"
    if {"transfer", "transferFrom", "approve", "balanceOf", "totalSupply"} <= names:
        return "token"
    return "unknown"


GATE_MOD_RE = re.compile(r"\b(only[A-Z]\w*|auth|requiresAuth|onlyRole\s*\()")
GATE_BODY_RE = re.compile(
    r"(require\s*\(\s*(_?msgSender\(\)|msg\.sender)\s*==|if\s*\(\s*(_?msgSender\(\)|msg\.sender)\s*!=[^)]*\)\s*revert|"
    r"_checkOwner\(\)|_checkRole\(|hasRole\([^,]+,\s*(_?msgSender\(\)|msg\.sender)\))")
STATIC = re.compile(r"^(address|bool|bytes([1-9]|[12][0-9]|3[0-2])|u?int\d*)$")


def _modifier_is_gate(text: str, name: str) -> bool:
    """An only*/auth-style modifier counts as an access gate only if it is a known OZ/auth one or its own body checks
    the caller against an authority (msg.sender/_msgSender/_checkOwner/_checkRole/hasRole). `onlyExistingToken`,
    `onlyWhenActive` etc. are input/state checks, not gates."""
    base = name.rstrip("( ").strip()
    if base in ("onlyOwner", "onlyRole", "auth", "requiresAuth", "onlyAdmin", "onlyGovernance", "onlyGovernor"):
        return True
    m = re.search(rf"modifier\s+{re.escape(base)}\b[^{{]*\{{", text)
    if not m:
        return True     # unknown (inherited from an unseen file): stay conservative
    body = _body(text, m.end())
    return bool(re.search(r"msg\.sender|_msgSender\(\)|_checkOwner|_checkRole|hasRole|isAuthorized|_onlyOwner", body))


def _body(text: str, start: int) -> str:
    """The function body from just after its opening brace up to the matching closing brace (max 4000 chars)."""
    depth, i, end = 1, start, min(len(text), start + 4000)
    while i < end and depth:
        c = text[i]
        depth += (c == "{") - (c == "}")
        i += 1
    return text[start:i]


def privileged_functions(abi: list, sources: dict) -> list[dict]:
    """External state-changing functions whose source shows an access gate, with only static params
    (so the handler can encode fuzzed arguments). Heuristic — same spirit as the Slither access map."""
    text = "\n".join(sources.values())
    out = []
    for f in _fns(abi).values():
        if f.get("stateMutability") in ("view", "pure"):
            continue
        if not all(STATIC.match(i["type"]) for i in f["inputs"]):
            continue
        # every definition with this name and arity must be gated: a gated `mint` on some other contract in the
        # sources (e.g. a tranche token's onlyMinter mint) must not make a public ERC-4626 mint "privileged"
        defs = []
        for m in re.finditer(rf"function\s+{re.escape(f['name'])}\s*\(([^)]*)\)([^{{;]*)\{{", text):
            params = [x for x in m.group(1).split(",") if x.strip()]
            if len(params) != len(f["inputs"]):
                continue
            body = _body(text, m.end())
            pnames = {x.split()[-1] for x in params if x.split()}
            gated = any(_modifier_is_gate(text, name) for name in GATE_MOD_RE.findall(m.group(2)))
            for g in GATE_BODY_RE.finditer(body):
                # `msg.sender == _account` against a function PARAMETER is a per-user check, not an authority gate
                cmp = re.search(r"(?:==|!=)\s*([A-Za-z_]\w*)", body[g.start(): g.start() + 120])
                if cmp and cmp.group(1) in pnames:
                    continue
                gated = True
                break
            defs.append((gated, "override" in m.group(2)))
        # gated if all definitions are gated, OR the overriding (most-derived) definition is gated while the
        # ungated ones are only virtual bases (JUSD: Whitelistable.setAllowed virtual vs AccountableVault override)
        if defs and (all(g for g, _ in defs) or any(g and ov for g, ov in defs)):
            out.append(f)
    return out


def struct_components(abi: list, fn: str, arg_index: int = 0) -> list[dict]:
    """Components (name/type) of a tuple argument, e.g. MarketParams of supply()."""
    f = _fns(abi)[fn]
    return f["inputs"][arg_index]["components"]
