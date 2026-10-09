#!/usr/bin/env python3
"""
Slither worker — runs INSIDE the EVM venv (.venv-evm, Python 3.13 + slither-analyzer).

It is executed as a subprocess by slither_runner.py, so the rest of SolScan can run on
any Python. Output (stdout) is one JSON document:

  {
    "results":   [...Slither detector results (JSON form)...],
    "detectors": {check: {title, recommendation, wiki}},
    "access":    {contract: {function_signature: AccessInfo}},
    "custom":    [...SolScan's own EVM findings (missing access control)...],
    "errors":    [...]
  }

AccessInfo classifies each function for the privilege filter:
  kind: "constructor" | "init" | "admin" | "external" | "internal"
  gates: why it is considered gated (modifier names, _checkOwner/_checkRole/hasRole, msg.sender check)
  reachable_unprotected: for internal/private functions, whether any ungated external/public
                         entry point can reach it (then it is effectively externally reachable)

Read-only analysis. Nothing is deployed or sent anywhere.
"""
import argparse
import inspect
import json
import re
import sys
import traceback

from slither import Slither
from slither.detectors import all_detectors
from slither.detectors.abstract_detector import AbstractDetector

# Modifier names that indicate an access gate (Ownable, AccessControl, custom auth).
GATE_MODIFIER_RE = re.compile(
    r"(only|auth|role|admin|owner|govern|guardian|keeper|operator|restricted|"
    r"whitelist|allowlist|manager|minter|pauser|controller|requiresAuth|isAuthorized)",
    re.I,
)
# Modifiers that look like gates by name but are not access control.
NOT_A_GATE_RE = re.compile(r"(nonReentrant|whenNotPaused|whenPaused|lock|noDelegateCall|onlyProxy|notDelegated)", re.I)
# One-time initialisation (OpenZeppelin Initializable and look-alikes).
INIT_MODIFIER_RE = re.compile(r"^(initializer|reinitializer|onlyInitializing|notInitialized|whenNotInitialized|"
                              r"onlyUninitialized|uninitialized|initOnce|notInit)$", re.I)
# Internal calls that perform an access check (OpenZeppelin v4/v5 and common patterns).
CHECK_CALL_RE = re.compile(
    r"^(_checkOwner|_checkRole|hasRole|_onlyOwner|_checkAdmin|_checkAuth\w*|_authorize\w*|"
    r"_requireOwner|_requireAdmin|_requireCallerIs\w*|_onlyRole\w*|requireAuth\w*|"
    r"_checkSender\w*|_validateCaller\w*|isAuthorized|canCall)$"
)
# State-variable names that typically hold authority.
AUTHORITY_VAR_RE = re.compile(
    r"(owner|admin|governance|governor|guardian|operator|authority|controller|"
    r"pendingOwner|implementation|minter|pauser|treasury|feeRecipient|role)",
    re.I,
)
# Function names that are usually meant to be privileged.
PRIVILEGED_NAME_RE = re.compile(
    # note: plain withdraw/mint/deposit are normal user actions and deliberately not listed
    r"^(set|update|change|transferOwnership|renounceOwnership|grant|revoke|sweep|"
    r"rescue|recover|burnFrom|pause|unpause|upgrade|kill|destroy|emergency|"
    r"configure|initialize|init|add\w*(Admin|Owner|Minter|Operator)|remove\w*(Admin|Owner|Minter|Operator))",
    re.I,
)


def _callee(c):
    """Slither >=0.10.x returns InternalCall objects; older versions return the function."""
    return getattr(c, "function", c)


def _name(x):
    return getattr(x, "name", str(x))


def _internal_calls(func):
    try:
        return [_callee(c) for c in func.all_internal_calls()]
    except Exception:
        return []


def _gates_of(func, _seen=None):
    """Return (gates, is_init) for a function, including what its modifiers do."""
    _seen = _seen or set()
    if id(func) in _seen:
        return [], False
    _seen.add(id(func))
    gates, is_init = [], False

    for m in getattr(func, "modifiers", []) or []:
        mname = _name(m)
        if INIT_MODIFIER_RE.match(mname):
            is_init = True
            continue
        if NOT_A_GATE_RE.search(mname):
            continue
        if GATE_MODIFIER_RE.search(mname):
            gates.append(f"modifier {mname}")
            continue
        # a modifier with an unrecognised name can still enforce access internally
        sub, _ = _gates_of(m, _seen)
        if sub or _protected(m):
            gates.append(f"modifier {mname} (controleert caller)")

    for callee in _internal_calls(func):
        cname = _name(callee)
        if CHECK_CALL_RE.match(cname):
            gates.append(f"call {cname}()")
    if _protected(func) and not any("msg.sender" in g for g in gates):
        gates.append("msg.sender-check")
    return sorted(set(gates)), is_init


SENDER = r"(?:msg\.sender|_msgSender\(\))"
# msg.sender compared with ONE authority (a bare state variable or a no-arg getter like owner()).
# Per-user checks such as positions[id].owner == msg.sender or balances[msg.sender] >= x are NOT gates.
_OPERAND = r"(?<![\w.\]\)])([A-Za-z_]\w*(?:\(\))?)(?![\w.\[(])"
SENDER_EQ_RE = re.compile(rf"{_OPERAND}\s*[!=]=\s*{SENDER}|{SENDER}\s*[!=]=\s*{_OPERAND}")
# authority mappings indexed by the caller: isOperator[msg.sender], admins[msg.sender], ...
AUTH_MAP_RE = re.compile(
    rf"\b\w*(admin|owner|operator|auth|whitelist|allowlist|keeper|minter|guardian|manager|"
    rf"governor|governance|trusted|controller|pauser|executor|relayer)\w*\s*\[\s*{SENDER}\s*\]",
    re.I,
)
# names that are user balances/approvals, never authority
USER_STATE_RE = re.compile(r"^(balance|balances|_balances|allowance|allowances|_allowances|nonces|deposits|shares|amount|from|to|spender|recipient|user|account|sender)$", re.I)


def _gate_operands(node):
    """Authority operands a node compares msg.sender against (empty list = no gate here).

    require/assert: only `==` (or a non-negated authority mapping) is a gate;
                    `require(msg.sender != admin)` EXCLUDES the admin and is not a gate.
    if:             `==` and `!=` both count (`if (owner() != _msgSender()) revert`).
    """
    try:
        is_req = node.contains_require_or_assert()
        is_if = node.contains_if()
    except Exception:
        return []
    if not (is_req or is_if):
        return []
    expr = str(getattr(node, "expression", "") or "")
    found = []
    for m in AUTH_MAP_RE.finditer(expr):
        if is_req and expr[:m.start()].rstrip().endswith("!"):
            continue  # require(!isOperator[msg.sender]) excludes, does not gate
        name = re.match(r"\w+", m.group(0)).group(0)
        found.append(name)
    for m in SENDER_EQ_RE.finditer(expr):
        op_text = m.group(0)
        if is_req and "!=" in op_text:
            continue
        operand = (m.group(1) or m.group(2) or "")
        if operand and not USER_STATE_RE.match(operand.rstrip("()")):
            found.append(operand)
    return found


def _node_has_sender_gate(node):
    return bool(_gate_operands(node))


def _protected(func, depth=0, seen=None):
    """True if func (or a modifier/internal call it uses) compares msg.sender with an authority."""
    seen = seen if seen is not None else set()
    if id(func) in seen or depth > 4:
        return False
    seen.add(id(func))
    for node in getattr(func, "nodes", []) or []:
        if _node_has_sender_gate(node):
            return True
    subs = list(getattr(func, "modifiers", []) or [])
    try:
        subs += [_callee(c) for c in func.internal_calls]
    except Exception:
        pass
    return any(_protected(s, depth + 1, seen) for s in subs if hasattr(s, "nodes"))


INIT_NAME_RE = re.compile(r"^_?(initialize|init|reinitialize)\w*$", re.I)
INIT_VAR_RE = re.compile(r"(initiali[sz]ed|initializing|initializedVersion|_version|version|isInit|inited|_init|initDone)$", re.I)
# proxy-style one-time initializer: require(_implementation() == address(0))
INIT_EXPR_RE = re.compile(r"_implementation\(\)\s*==\s*address\(0\)|_getImplementation\(\)\s*==\s*address\(0\)")


def _own_init_guard(func):
    """initialize-style function protected by its own one-time flag (require(!initialized), version checks)."""
    if not INIT_NAME_RE.match(_name(func)):
        return False
    try:
        for node in func.nodes:
            if node.contains_require_or_assert() or node.contains_if():
                if any(INIT_VAR_RE.search(v.name) for v in node.state_variables_read):
                    return True
                if INIT_EXPR_RE.search(str(getattr(node, "expression", "") or "")):
                    return True
    except Exception:
        pass
    return False


def _sig(func):
    return getattr(func, "full_name", None) or getattr(func, "name", "?")


def _is_constructor(func):
    return bool(getattr(func, "is_constructor", False)) or _name(func) == "constructor"


def _visibility(func):
    return getattr(func, "visibility", "internal")


def _only_caller_keyed_writes(func):
    """True if every state write in func is to a mapping slot keyed by msg.sender (incl. nonReentrant's lock)."""
    writes = []
    try:
        for node in func.nodes:
            if node.state_variables_written:
                writes.append(str(node.expression or ""))
    except Exception:
        return False
    user_writes = [w for w in writes if re.search(SENDER, w)]
    other = [w for w in writes if not re.search(SENDER, w)]
    return bool(user_writes) and not other


def build_access_map(slither):
    access = {}
    custom = []
    for contract in slither.contracts_derived:
        if getattr(contract, "is_interface", False):
            continue
        funcs = [f for f in contract.functions if not getattr(f, "is_shadowed", False)]
        info = {}
        # 1) direct classification
        for f in funcs:
            gates, is_init = _gates_of(f)
            vis = _visibility(f)
            if _is_constructor(f):
                kind = "constructor"
            elif is_init or _own_init_guard(f):
                kind = "init"
            elif gates:
                kind = "admin"
            elif vis in ("public", "external"):
                kind = "external"
            else:
                kind = "internal"
            info[_sig(f)] = {
                "function": _name(f),
                "visibility": vis,
                "kind": kind,
                "gates": gates,
                "view": bool(getattr(f, "view", False) or getattr(f, "pure", False)),
                "declared_in": _name(getattr(f, "contract_declarer", contract)),
            }
        for m in getattr(contract, "modifiers", []) or []:
            info.setdefault(_sig(m), {"function": _name(m), "visibility": "internal", "kind": "modifier",
                                      "gates": [], "view": False,
                                      "declared_in": _name(getattr(m, "contract_declarer", contract))})
        access[contract.name] = info

        # 3) SolScan custom detector: missing access control on authority-bearing state.
        #    authority vars = state vars read inside gated functions' conditions / modifiers
        authority_vars = set()
        state_names = {v.name: v for v in contract.state_variables}
        getters = {_name(g): g for g in funcs}
        scan = list(funcs) + list(getattr(contract, "modifiers", []) or [])
        for fn in scan:
            for node in getattr(fn, "nodes", []) or []:
                for op in _gate_operands(node):
                    base = op.rstrip("()")
                    if base in state_names:
                        authority_vars.add(base)
                    elif op.endswith("()") and base in getters:      # owner() -> _owner
                        try:
                            authority_vars.update(v.name for v in getters[base].state_variables_read)
                        except Exception:
                            pass
        for v in contract.state_variables:
            t = str(getattr(v, "type", ""))
            if AUTHORITY_VAR_RE.search(v.name) and (t == "address" or t.startswith("mapping(address => bool")):
                authority_vars.add(v.name)

        for f in funcs:
            rec = info[_sig(f)]
            if rec["kind"] != "external" or rec["view"]:
                continue
            try:
                written = {v.name for v in f.all_state_variables_written()}
            except Exception:
                written = set()
            if _only_caller_keyed_writes(f):
                continue  # e.g. rewardRedirect[msg.sender] = to: a per-user setting, not admin state
            hit = sorted(written & authority_vars)
            sm = getattr(f, "source_mapping", None)
            loc = {
                "file": getattr(getattr(sm, "filename", None), "relative", None) or getattr(getattr(sm, "filename", None), "absolute", ""),
                "line": (sm.lines[0] if sm and sm.lines else 0),
            }
            if hit:
                custom.append({
                    "check": "solscan-missing-access-control",
                    "impact": "High",
                    "confidence": "Medium",
                    "contract": contract.name,
                    "function": _sig(f),
                    "description": (
                        f"{contract.name}.{_sig(f)} is {rec['visibility']} en heeft geen access-gate, "
                        f"maar schrijft autoriteits-state: {', '.join(hit)}. Iedereen kan dit aanroepen."
                    ),
                    **loc,
                })
            elif written and PRIVILEGED_NAME_RE.match(_name(f)):
                custom.append({
                    "check": "solscan-unguarded-privileged-name",
                    "impact": "Medium",
                    "confidence": "Low",
                    "contract": contract.name,
                    "function": _sig(f),
                    "description": (
                        f"{contract.name}.{_sig(f)} heeft een typisch beheerdersnaam en wijzigt state "
                        f"({', '.join(sorted(written))}), maar heeft geen access-gate. Controleer of dit bedoeld is."
                    ),
                    **loc,
                })
    _global_reachability(slither, access)
    return access, custom


def _library_calls(func):
    """[(library_contract_name, function)] — Slither returns LibraryCall objects or (contract, func) tuples."""
    out = []
    try:
        for c in func.all_library_calls():
            if isinstance(c, tuple) and len(c) == 2:
                out.append((_name(c[0]), c[1]))
            else:
                fn = getattr(c, "function", c)
                out.append((_name(getattr(c, "destination", None) or getattr(fn, "contract", None)), fn))
    except Exception:
        pass
    return out


def _global_reachability(slither, access):
    """Mark internal/private functions reachable from an UNGATED entry point, across contracts.

    Edges: internal calls (same derived contract) and library calls (into the library contract).
    Without the library edges a bug in e.g. UniswapV2Library would wrongly look admin-only.
    """
    callers = {}  # (contract, sig) -> {(contract, sig)}
    for contract in slither.contracts_derived:
        for f in contract.functions:
            me = (contract.name, _sig(f))
            for callee in _internal_calls(f):
                callers.setdefault((contract.name, _sig(callee)), set()).add(me)
            for lib, fn in _library_calls(f):
                if lib:
                    callers.setdefault((lib, _sig(fn)), set()).add(me)

    def kind_of(key):
        return ((access.get(key[0]) or {}).get(key[1]) or {}).get("kind")

    def via_unprotected(key, seen):
        for caller in callers.get(key, ()):
            if caller in seen:
                continue
            seen.add(caller)
            k = kind_of(caller)
            if k == "external":
                return caller
            if k == "internal":
                r = via_unprotected(caller, seen)
                if r:
                    return r
        return None

    for cname, fs in access.items():
        for sig, rec in fs.items():
            if rec["kind"] == "internal":
                via = via_unprotected((cname, sig), set())
                rec["reachable_unprotected"] = via is not None
                rec["reachable_via"] = (f"{via[0]}.{via[1]}" if via and via[0] != cname else (via[1] if via else None))


def export_functions(slither):
    """Per-function facts for SolScan's own semantic checks (oracle_checks.py).

    External/library call names come from Slither's IR (HighLevelCall / LibraryCall), so a call
    like pair.getReserves() or OracleLibrary.consult(...) is recognised regardless of formatting.
    """
    try:
        from slither.slithir.operations import HighLevelCall, LibraryCall
    except Exception:
        HighLevelCall = LibraryCall = ()
    out = []
    for contract in slither.contracts_derived:
        if getattr(contract, "is_interface", False):
            continue
        for f in contract.functions:
            calls, lib_calls = [], []
            try:
                for node in f.nodes:
                    for ir in node.irs:
                        if LibraryCall and isinstance(ir, LibraryCall):
                            lib_calls.append(str(ir.function_name))
                        elif HighLevelCall and isinstance(ir, HighLevelCall):
                            calls.append(str(ir.function_name))
            except Exception:
                pass
            sm = getattr(f, "source_mapping", None)
            text = ""
            try:
                text = sm.content or ""
            except Exception:
                pass
            fname = getattr(getattr(sm, "filename", None), "relative", None) or ""
            out.append({
                "contract": contract.name,
                "declared_in": _name(getattr(f, "contract_declarer", contract)),
                "sig": _sig(f), "name": _name(f), "file": fname,
                "line": (sm.lines[0] if sm and sm.lines else 0),
                "text": text[:20000],
                "high_calls": sorted(set(calls)), "lib_calls": sorted(set(lib_calls)),
                "internal": sorted({_name(c) for c in _internal_calls(f)}),
                "view": bool(getattr(f, "view", False) or getattr(f, "pure", False)),
            })
    return out



# --------------------------------------------------------------------------------------------------------------
# SolScan detector: unprotected-sibling
#   An ungated public/external function that (a) delegatecalls / makes a low-level call to an address the caller
#   supplies, (b) makes the CONTRACT approve a caller-chosen spender (or approves on a caller-chosen token),
#   (c) calls privilege-granting functions, or (d) calls a state-changing function on a caller-chosen address —
#   in a contract where OTHER functions are gated. The gated siblings show the author knew the entry points need
#   protection; the ungated one is then very likely an oversight. HIGH when the contract can move value.
# --------------------------------------------------------------------------------------------------------------
APPROVAL_FNS = {"approve", "safeApprove", "forceApprove", "increaseAllowance", "safeIncreaseAllowance",
                "setApprovalForAll", "increaseApproval"}
PRIVILEGE_FNS_RE = re.compile(r"^(_?grantRole|_?setupRole|_?transferOwnership|setOperator|addMinter|addAdmin|"
                              r"setAuthority|setOwner|setGovernance|setGuardian|setController|addOperator)$")
# transfers of a caller-chosen token are the normal deposit pattern, not a finding by themselves
BENIGN_TOKEN_CALLS = {"transfer", "transferFrom", "safeTransfer", "safeTransferFrom", "balanceOf", "allowance",
                      "decimals", "symbol", "name", "totalSupply", "permit", "supportsInterface", "ownerOf"}
VALUE_FNS = {"transfer", "transferFrom", "safeTransfer", "safeTransferFrom", "approve", "safeApprove",
             "forceApprove", "safeIncreaseAllowance", "increaseAllowance"}


def _param_dependent(var, params, ctx):
    from slither.analyses.data_dependency.data_dependency import is_dependent
    if var is None:
        return False
    for p in params:
        try:
            if is_dependent(var, p, ctx):
                return True
        except Exception:
            continue
    return False


def _validated_params(f, params):
    """Parameters that the function checks against a mapping (allowlist / registry / existing-id check) inside a
    require/assert or an if-revert condition. A caller-supplied address that has to be on an allowlist is not
    "caller-chosen" in the dangerous sense."""
    from slither.core.cfg.node import NodeType
    from slither.slithir.operations import Index
    valid = set()
    for node in getattr(f, "nodes", []) or []:
        if not (node.contains_require_or_assert() or node.type == NodeType.IF):
            continue
        for ir in getattr(node, "irs", []) or []:
            if isinstance(ir, Index):
                for p in params:
                    if _param_dependent(getattr(ir, "variable_right", None), [p], f):
                        valid.add(p)
    return valid


def _is_addr_like(p):
    s = str(getattr(p, "type", ""))
    return s.startswith("address") or s.startswith("bytes") or not s.startswith(("uint", "int", "bool", "string"))


def _contract_moves_value(contract):
    from slither.slithir.operations import HighLevelCall, LibraryCall, LowLevelCall, Send, Transfer
    for f in contract.functions:
        if getattr(f, "payable", False):
            return True
        for node in getattr(f, "nodes", []) or []:
            for ir in getattr(node, "irs", []) or []:
                if isinstance(ir, (Transfer, Send)):
                    return True
                if isinstance(ir, LowLevelCall) and getattr(ir, "call_value", None) is not None:
                    return True
                if isinstance(ir, (HighLevelCall, LibraryCall)) and str(getattr(ir, "function_name", "")) in VALUE_FNS:
                    return True
    return False


def _risky_ops(f, params, ctx, via=""):
    """Risky operations inside function f whose target/spender depends on `params` (parameters of ctx)."""
    from slither.slithir.operations import HighLevelCall, InternalCall, LibraryCall, LowLevelCall
    ops = []
    for node in getattr(f, "nodes", []) or []:
        for ir in getattr(node, "irs", []) or []:
            if isinstance(ir, LowLevelCall):
                fname = str(getattr(ir, "function_name", ""))
                if _param_dependent(getattr(ir, "destination", None), params, ctx):
                    kind = "delegatecall" if fname == "delegatecall" else "low-level-call"
                    ops.append((kind, f"{fname} naar een door de caller opgegeven adres{via}"))
            elif isinstance(ir, LibraryCall):
                fname = str(getattr(ir, "function_name", ""))
                args = list(getattr(ir, "arguments", []) or [])
                if fname in APPROVAL_FNS and len(args) >= 2:
                    if _param_dependent(args[1], params, ctx):
                        ops.append(("approval", f"het contract geeft via {fname} een approval aan een door de caller opgegeven spender{via}"))
                    elif _param_dependent(args[0], params, ctx):
                        ops.append(("approval-token", f"het contract geeft via {fname} een approval aan een vaste spender, op een door de caller gekozen token{via}"))
            elif isinstance(ir, HighLevelCall):
                fname = str(getattr(ir, "function_name", ""))
                dest = getattr(ir, "destination", None)
                args = list(getattr(ir, "arguments", []) or [])
                if fname in APPROVAL_FNS and args and _param_dependent(args[0], params, ctx):
                    ops.append(("approval", f"het contract geeft via {fname} een approval aan een door de caller opgegeven spender{via}"))
                elif fname in APPROVAL_FNS and args and _param_dependent(dest, params, ctx):
                    ops.append(("approval-token", f"het contract geeft via {fname} een approval aan een vaste spender, op een door de caller gekozen token{via}"))
                elif PRIVILEGE_FNS_RE.match(fname) and (_param_dependent(dest, params, ctx) or any(
                        _param_dependent(a, params, ctx) for a in args)):
                    ops.append(("privilege", f"{fname}() wordt aangeroepen met door de caller bepaalde waarden{via}"))
                elif _param_dependent(dest, params, ctx) and fname not in BENIGN_TOKEN_CALLS:
                    callee = getattr(ir, "function", None)
                    if not (getattr(callee, "view", False) or getattr(callee, "pure", False)):
                        ops.append(("callback", f"{fname}() op een door de caller opgegeven adres{via}"))
    return ops


def unprotected_siblings(slither, access):
    findings = []
    for contract in slither.contracts_derived:
        if getattr(contract, "is_interface", False):
            continue
        info = access.get(contract.name) or {}
        gated = [r for r in info.values()
                 if r.get("kind") == "admin" and not r.get("view") and r.get("visibility") in ("public", "external")]
        if not gated:
            continue                                     # no authorization model -> no "sibling" to compare with
        value = _contract_moves_value(contract)
        for f in [f for f in contract.functions if not getattr(f, "is_shadowed", False)]:
            rec = info.get(_sig(f))
            if not rec or rec["kind"] != "external" or rec["view"]:
                continue
            params = list(getattr(f, "parameters", []) or [])
            if not params:
                continue
            validated = _validated_params(f, params)
            free = [p for p in params if p not in validated]       # parameters the caller can still choose freely
            ops = _risky_ops(f, free, f) if free else []
            if any(_is_addr_like(p) for p in free):
                for callee in getattr(f, "internal_calls", []) or []:
                    cf = getattr(callee, "function", callee)
                    if not hasattr(cf, "nodes") or cf is f:
                        continue
                    vnames = {getattr(p, "name", None) for p in validated}
                    cparams = [p for p in (getattr(cf, "parameters", []) or []) if getattr(p, "name", None) not in vnames]
                    if cparams:
                        ops += _risky_ops(cf, cparams, cf, via=f" (via interne functie {_name(cf)})")
            if not ops:
                continue
            kinds = sorted({k for k, _ in ops})
            strong = bool(set(kinds) & {"delegatecall", "low-level-call", "approval", "privilege"})
            high = strong and value
            sm = getattr(f, "source_mapping", None)
            loc = {
                "file": getattr(getattr(sm, "filename", None), "relative", None)
                        or getattr(getattr(sm, "filename", None), "absolute", ""),
                "line": (sm.lines[0] if sm and sm.lines else 0),
            }
            sib = ", ".join(sorted({r["function"] for r in gated})[:4])
            findings.append({
                "check": "solscan-unprotected-sibling",
                "impact": "High" if high else "Medium",
                "confidence": "Medium" if strong else "Low",
                "contract": contract.name,
                "function": _sig(f),
                "patterns": kinds,
                "value_reachable": value,
                "description": (
                    f"{contract.name}.{_sig(f)} is {rec['visibility']} zonder caller-check, terwijl andere functies in "
                    f"dit contract wel gegate zijn ({sib}). De functie: " + "; ".join(sorted({d for _, d in ops})) + ". "
                    + ("Het contract verplaatst waarde, dus dit pad kan bij waarde komen." if value
                       else "Geen waardeverplaatsing gevonden in dit contract.")
                ),
                **loc,
            })
    return findings



def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--solc")
    ap.add_argument("--solc-working-dir")
    ap.add_argument("--solc-args")
    ap.add_argument("--solc-remaps")
    args = ap.parse_args(argv)

    out = {"results": [], "detectors": {}, "access": {}, "custom": [], "functions": [], "errors": []}
    kwargs = {"disable_solc_warnings": True}
    if args.solc:
        kwargs["solc"] = args.solc
    if args.solc_working_dir:
        kwargs["solc_working_dir"] = args.solc_working_dir
    if args.solc_args:
        kwargs["solc_args"] = args.solc_args
    if args.solc_remaps:
        kwargs["solc_remaps"] = args.solc_remaps
    try:
        sl = Slither(args.target, **kwargs)
    except Exception as e:
        out["errors"].append(f"compilatie/parse mislukt: {e}")
        print(json.dumps(out))
        return 2

    for _, cls in inspect.getmembers(all_detectors, inspect.isclass):
        if issubclass(cls, AbstractDetector) and cls is not AbstractDetector:
            sl.register_detector(cls)
            out["detectors"][cls.ARGUMENT] = {
                "title": getattr(cls, "WIKI_TITLE", "") or cls.HELP,
                "recommendation": getattr(cls, "WIKI_RECOMMENDATION", ""),
                "wiki": getattr(cls, "WIKI", ""),
            }
    try:
        for res in sl.run_detectors():
            out["results"].extend(res)
    except Exception as e:
        out["errors"].append(f"detectors: {e}\n{traceback.format_exc(limit=3)}")
    try:
        out["functions"] = export_functions(sl)
    except Exception as e:
        out["errors"].append(f"function-export: {e}")
    try:
        out["access"], out["custom"] = build_access_map(sl)
    except Exception as e:
        out["errors"].append(f"access-map: {e}\n{traceback.format_exc(limit=3)}")
    try:
        out["custom"].extend(unprotected_siblings(sl, out["access"]))
    except Exception as e:
        out["errors"].append(f"unprotected-sibling: {e}\n{traceback.format_exc(limit=3)}")
    print(json.dumps(out, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
