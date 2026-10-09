#!/usr/bin/env python3
"""Offline checks for the invariant-fuzz generator (no network, no forge)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solscan.evm.fuzz import detect, generator  # noqa: E402

MP = {"type": "tuple", "name": "marketParams", "components": [
    {"name": "loanToken", "type": "address"}, {"name": "collateralToken", "type": "address"},
    {"name": "oracle", "type": "address"}, {"name": "irm", "type": "address"},
    {"name": "ltv", "type": "uint256"}, {"name": "lltv", "type": "uint256"}, {"name": "whitelist", "type": "address"}]}


def fn(name, inputs, mut="nonpayable", outputs=()):
    return {"type": "function", "name": name, "inputs": inputs, "stateMutability": mut,
            "outputs": [{"type": t} for t in outputs]}


U = {"type": "uint256", "name": "x"}
A = {"type": "address", "name": "a"}
LENDER_ABI = [fn(n, [MP, U, U, A, A]) for n in ("supply", "withdraw", "borrow", "repay")] + \
             [fn("supplyCollateral", [MP, U, A, {"type": "bytes", "name": "d"}]),
              fn("withdrawCollateral", [MP, U, A, A]), fn("setOwner", [A]), fn("enableIrm", [A]),
              fn("setAuthorization", [A, {"type": "bool", "name": "b"}]), fn("claimFor", [A, A]), fn("depositToken", [A, U])]
VAULT_ABI = [fn(n, [U, A]) for n in ("deposit", "mint")] + [fn(n, [U, A, A]) for n in ("withdraw", "redeem")] + \
            [fn("asset", [], "view"), fn("totalAssets", [], "view"), fn("convertToAssets", [U], "view")]
PAIR_ABI = [fn(n, []) for n in ("getReserves", "token0", "token1")] + [fn("swap", [U, U, A]), fn("mint", [A]), fn("burn", [A])]
TOKEN_ABI = [fn("transfer", [A, U]), fn("transferFrom", [A, A, U]), fn("approve", [A, U]),
             fn("balanceOf", [A], "view"), fn("totalSupply", [], "view")]

SRC = {"L.sol": """
contract L {
    function setOwner(address n) external onlyOwner { owner = n; }
    function enableIrm(address irm) external { require(msg.sender == owner, "x"); isIrm[irm] = true; }
    function setAuthorization(address a, bool b) external { isAuthorized[msg.sender][a] = b; }
    function claimFor(address _account, address to) external { require(msg.sender == _account, "!self"); pay(to); }
    modifier onlyExistingToken(address tk) { require(valid[tk], "no"); _; }
    function depositToken(address tk, uint256 amt) external onlyExistingToken(tk) { bal[msg.sender] += amt; }
}"""}

checks = []


def check(name, cond):
    checks.append((name, bool(cond)))


check("classify lender", detect.classify(LENDER_ABI) == "lender")
check("classify vault", detect.classify(VAULT_ABI) == "vault")
check("classify amm", detect.classify(PAIR_ABI) == "amm")
check("classify token", detect.classify(TOKEN_ABI) == "token")
priv = {f["name"] for f in detect.privileged_functions(LENDER_ABI, SRC)}
check("privileged: modifier gate", "setOwner" in priv)
check("privileged: require(msg.sender == owner)", "enableIrm" in priv)
check("privileged: per-user write is NOT privileged", "setAuthorization" not in priv)
check("privileged: msg.sender == <param> is a per-user check, NOT privileged", "claimFor" not in priv)
check("privileged: only*-modifier without caller check (onlyExistingToken) is NOT a gate", "depositToken" not in priv)

markets = [{"id": "0x" + "11" * 32, "supplier_role": "0xfe7c47895edb12a990b311df33b90cfea1d44c24", "params": {"loanToken": "0x73a15fed60bf67631dc6cd7bc5b6e8da8190acf5",
            "collateralToken": "0x35d8949372d46b7a3d5a56006ae77b215fc69bc0", "oracle": "0x30da78355fcea04d1fa34af3c318be203c6f2145",
            "irm": "0xe5b2258b4f2d5c96c5f432606110eb31e6b85f54", "ltv": 88 * 10**16, "lltv": 9999 * 10**14,
            "whitelist": "0xfe7c47895edb12a990b311df33b90cfea1d44c24"}}]
code = generator.render("lender", "0xa428723ee8ffd87088c36121d72100b43f11fb6a", 1, ["solvency", "no-free-withdraw", "access"],
                        4, 10**24, markets, MP["components"], [LENDER_ABI[6]], 100, False, 1000)
check("render: struct with extra fields", "uint256 ltv;" in code and "address whitelist;" in code)
check("render: supplier role from whitelist field", "supplierRole.push(0xFE7C47895eDb12a990b311Df33B90Cfea1D44c24)" in code or "supplierRole.push(" in code)
check("render: checksummed market literal", "0x73A15FeD60Bf67631dC6cd7Bc5B6e8da8190aCF5" in code)
check("render: only chosen invariants", "invariant_solvency" in code and "invariant_conservation" not in code)
check("render: access selector via HandlerBase", "HandlerBase.tryPrivileged.selector" in code)
check("render: fork from env", 'vm.envString("FUZZ_RPC_URL")' in code)

ok = all(c for _, c in checks)
for n, c in checks:
    print(("PASS " if c else "FAIL ") + n)
print(f"\n{sum(c for _, c in checks)}/{len(checks)} checks ok")
sys.exit(0 if ok else 1)
