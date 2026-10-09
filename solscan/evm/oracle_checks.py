"""
Defensive oracle-safety checks for the EVM module (SolScan's own layer on top of Slither).

Purpose: point out contracts that read a price without the usual protections, so the
protocol can add them. Every finding states only WHICH protection is missing and HOW to add
it. These are attention points (verify manually), not verdicts.

Input: per-function facts exported by slither_worker.export_functions (external/library call
names from Slither's IR, function source, view status). Fallback: regex over .sol files.

Rules
  EVM-ORACLE-SPOT    price read from a DEX pool without time-averaging (no TWAP in function/contract)
  EVM-ORACLE-FRESH   Chainlink value used without freshness / positivity check
  EVM-ORACLE-SINGLE  exactly one price source, no TWAP, no second source or sanity bound
"""
from __future__ import annotations

import os
import re

from ..report import Finding

# --- what counts as a price source ------------------------------------------------------------
POOL_PRICE_CALLS = {"getReserves", "slot0", "getAmountOut", "getAmountsOut"}
CHAINLINK_CALLS = {"latestRoundData", "latestAnswer"}
TIME_AVERAGE_CALLS = {"observe", "consult", "getTimeWeightedAverageTick", "getQuoteAtTick",
                      "currentCumulativePrices", "price0CumulativeLast", "price1CumulativeLast"}
TIME_AVERAGE_TEXT = re.compile(r"\b(twap|TWAP|timeWeighted|TimeWeighted|cumulative|Cumulative|observe\s*\(|consult\s*\()")
# a function that performs a swap/liquidity action uses pool numbers for that action, not as a valuation
POOL_ACTION_CALLS = re.compile(r"^(swap\w*|exactInput\w*|exactOutput\w*|addLiquidity\w*|removeLiquidity\w*|"
                               r"mint|burn|collect|sync|skim)$")
# a protocol-specific oracle contract: counts for coverage only (its protections live in that contract)
CUSTOM_ORACLE_CALLS = re.compile(r"^(getPrice|getAssetPrice|getUnderlyingPrice|getPriceUSD|getLatestPrice|"
                                 r"fetchPrice|peek|getUnderlyingPriceView|price|assetPrices)$")
SECOND_SOURCE_OR_BOUND = re.compile(
    r"(fallback|secondary|backup|maxDeviation|deviation|minAnswer|maxAnswer|lowerBound|upperBound|"
    r"sanity|priceBound|MAX_PRICE|MIN_PRICE|maxPrice|minPrice|circuitBreaker)", re.I)

FIX_SPOT = ("Gebruik een tijdsgemiddelde prijs (TWAP, bijv. Uniswap V3 `observe`/`OracleLibrary.consult`) "
            "of een robuuste oracle in plaats van een momentane poolprijs.")
FIX_FRESH = ("Controleer `updatedAt` tegen een maximale leeftijd (bijv. `block.timestamp - updatedAt <= MAX_AGE`) "
             "en `answer > 0` voordat je de waarde gebruikt; vervang `latestAnswer()` door `latestRoundData()`.")
FIX_SINGLE = "Voeg een tweede prijsbron of een redelijkheidsgrens (min/max of maximale afwijking) toe."


def _strip_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t or "", flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def _line_of(fn: dict, needle: str) -> int:
    text = fn.get("text") or ""
    i = text.find(needle)
    return fn["line"] + text[:i].count("\n") if i >= 0 else fn["line"]


def _snippet(fn: dict, needle: str) -> str:
    for ln in (fn.get("text") or "").splitlines():
        if needle in ln:
            return ln.strip()[:160]
    return fn.get("sig", "")


def _mk(rule, title, sev, conf, fn, needle, detail, fix):
    f = Finding(rule_id=rule, title=title, severity=sev, confidence=conf, file=fn.get("file", ""),
                line=_line_of(fn, needle), snippet=_snippet(fn, needle), detail=detail,
                recommendation=fix, needs_manual_review=True)
    return f, {"check": rule.lower(), "functions": [(fn["contract"], fn["sig"])], "files": [fn.get("file", "")]}


def _calls(fn: dict) -> set:
    return set(fn.get("high_calls") or []) | set(fn.get("lib_calls") or [])


def _closure_text(fn: dict, by_name: dict) -> str:
    """Function text plus the text of the internal functions it calls (one level), comments removed."""
    parts = [fn.get("text") or ""]
    for name in fn.get("internal") or []:
        for other in by_name.get((fn["contract"], name), []):
            parts.append(other.get("text") or "")
    return _strip_comments("\n".join(parts))


# --- FRESH: is the Chainlink value checked? -----------------------------------------------------
_DESTRUCT = re.compile(
    r"\(\s*(?:uint80\s+)?(\w*)\s*,\s*(?:int256\s+)?(\w*)\s*,\s*(?:uint256\s+)?(\w*)\s*,\s*"
    r"(?:uint256\s+)?(\w*)\s*,\s*(?:uint80\s+)?(\w*)\s*\)\s*=\s*[^;]*latestRoundData\s*\(")


_TRY_RETURNS = re.compile(
    r"latestRoundData\s*\(\s*\)\s*returns\s*\(\s*(?:uint80\s+)?(\w*)\s*,\s*(?:int256\s+)?(\w*)\s*,\s*"
    r"(?:uint256\s+)?(\w*)\s*,\s*(?:uint256\s+)?(\w*)\s*,\s*(?:uint80\s+)?(\w*)\s*\)")
# contract-level evidence, also for values stored in struct fields (e.g. response.timestamp, response.answer)
_CONTRACT_FRESH = re.compile(
    r"block\.timestamp\s*(?:-|\.sub\s*\()\s*[\w.]*(?:updatedAt|[tT]imestamp|updateTime)\b"
    r"|[\w.]*(?:updatedAt|[tT]imestamp|updateTime)\b\s*(?:<|>|<=|>=)\s*[^;]*block\.timestamp"
    r"|block\.timestamp\s*(?:<|>|<=|>=)\s*[\w.]*(?:updatedAt|[tT]imestamp|updateTime)\b")
_CONTRACT_POSITIVE = re.compile(r"[\w.]*(?:answer|[pP]rice)\w*\s*(?:<=|>|==)\s*0\b|\b0\s*(?:<|>=)\s*[\w.]*(?:answer|[pP]rice)")


def _freshness_gaps(text: str, contract_text: str = "") -> list[str]:
    """Which protections are missing around latestRoundData()? (empty = all present)

    First the function (+ its internal helpers); for what is still missing, the whole contract is
    searched (checks often live in a separate validation function called by the caller).
    """
    gaps = []
    m = _DESTRUCT.search(text) or _TRY_RETURNS.search(text)
    answer = m.group(2) if m else ""
    updated = m.group(4) if m else ""
    # freshness = updatedAt compared in the SAME statement as block.timestamp (an interval check
    # relative to the last update alone does not detect a stale feed)
    fresh = bool(updated) and any(
        re.search(rf"\b{re.escape(updated)}\b", st) and "block.timestamp" in st and re.search(r"[<>]", st)
        for st in text.split(";"))
    if not fresh:
        gaps.append("geen controle van `updatedAt` tegen `block.timestamp` (maximale leeftijd)")
    # positivity must exclude zero: > 0, <= 0, == 0 (a check `< 0` lets a zero price through)
    if not answer or not re.search(rf"\b{re.escape(answer)}\b\s*(>|<=|==)\s*0\b|\b0\s*(<|>=)\s*\b{re.escape(answer)}\b", text):
        gaps.append("geen controle `answer > 0` (een prijs van 0 wordt niet geweigerd)")
    if contract_text:
        if gaps and "block.timestamp" in gaps[0] and _CONTRACT_FRESH.search(contract_text):
            gaps = gaps[1:]
        gaps = [g for g in gaps if not ("answer > 0" in g and _CONTRACT_POSITIVE.search(contract_text))]
    return gaps


def check_functions(functions: list[dict]) -> tuple[list, dict]:
    """Run the three checks over the worker's per-function export."""
    findings = []
    by_name = {}
    for fn in functions:
        by_name.setdefault((fn["contract"], fn["name"]), []).append(fn)

    per_contract = {}
    for fn in functions:
        c = per_contract.setdefault(fn["contract"], {"sources": set(), "twap": False, "bound": False, "sites": []})
        text = _strip_comments(fn.get("text") or "")
        calls = _calls(fn)
        if calls & TIME_AVERAGE_CALLS or TIME_AVERAGE_TEXT.search(text):
            c["twap"] = True
        if SECOND_SOURCE_OR_BOUND.search(text):
            c["bound"] = True
        if calls & CHAINLINK_CALLS:
            c["sources"].add("chainlink")
            c["sites"].append((fn, next(iter(calls & CHAINLINK_CALLS))))
        if calls & POOL_PRICE_CALLS and not any(POOL_ACTION_CALLS.match(x) for x in calls):
            c["sources"].add("dex-pool")
            c["sites"].append((fn, next(iter(calls & POOL_PRICE_CALLS))))
        if any(CUSTOM_ORACLE_CALLS.match(x) for x in calls):
            c["custom"] = True

    contract_text = {}
    for fn in functions:
        contract_text[fn["contract"]] = contract_text.get(fn["contract"], "") + "\n" + _strip_comments(fn.get("text") or "")

    seen = set()
    for fn in functions:
        key = (fn.get("file"), fn.get("line"), fn["sig"])
        if key in seen:
            continue  # inherited copies of the same function
        seen.add(key)
        calls = _calls(fn)
        contract = per_contract[fn["contract"]]

        # SPOT: pool price used outside a pool action, and no time-averaging anywhere in the contract
        pool = calls & POOL_PRICE_CALLS
        if pool and not any(POOL_ACTION_CALLS.match(c) for c in calls) and not contract["twap"]:
            call = sorted(pool)[0]
            findings.append(_mk(
                "EVM-ORACLE-SPOT", "Poolprijs gebruikt zonder tijdsmiddeling", "High", "Medium", fn, call,
                f"`{fn['contract']}.{fn['sig']}` leest `{call}()` van een DEX-pool en gebruikt de uitkomst niet "
                f"voor een swap; in de functie en het contract is geen tijdsmiddeling (TWAP) aanwezig. "
                f"Bescherming ontbreekt: tijdsgemiddelde prijs.", FIX_SPOT))

        # FRESH: latestAnswer is always without timestamp; latestRoundData needs the checks
        if "latestAnswer" in calls:
            findings.append(_mk(
                "EVM-ORACLE-FRESH", "Chainlink latestAnswer() zonder versheidsinformatie", "Medium", "Medium",
                fn, "latestAnswer",
                f"`{fn['contract']}.{fn['sig']}` gebruikt `latestAnswer()`; die geeft geen tijdstip terug, dus "
                f"versheid kan niet worden gecontroleerd. Bescherming ontbreekt: versheidscontrole.", FIX_FRESH))
        if "latestRoundData" in calls:
            gaps = _freshness_gaps(_closure_text(fn, by_name), contract_text.get(fn["contract"], ""))
            if gaps:
                findings.append(_mk(
                    "EVM-ORACLE-FRESH", "Chainlink latestRoundData() zonder volledige versheidscontrole",
                    "High" if len(gaps) == 2 else "Medium", "Medium", fn, "latestRoundData",
                    f"`{fn['contract']}.{fn['sig']}` gebruikt `latestRoundData()`; ontbrekend: {'; '.join(gaps)}.",
                    FIX_FRESH))

    # SINGLE: exactly one source kind, no time-averaging, no second source / bound
    for cname, c in per_contract.items():
        if len(c["sources"]) == 1 and not c["twap"] and not c["bound"] and c["sites"]:
            fn, call = c["sites"][0]
            findings.append(_mk(
                "EVM-ORACLE-SINGLE", "Eén prijsbron zonder tweede controle", "Medium", "Low", fn, call,
                f"`{cname}` gebruikt één prijsbron ({next(iter(c['sources']))}, via `{call}()`), zonder "
                f"tijdsmiddeling, tweede bron of redelijkheidsgrens. Bescherming ontbreekt: tweede controle.",
                FIX_SINGLE))

    coverage = {cn: sorted(c["sources"] | ({"eigen oracle-contract"} if c.get("custom") else set()))
                for cn, c in per_contract.items() if c["sources"] or c.get("custom")}
    return findings, coverage


# --- regex fallback (no Slither data) ----------------------------------------------------------
_FALLBACK_CALL = re.compile(r"\.\s*(getReserves|slot0|getAmountsOut|getAmountOut|latestRoundData|latestAnswer)\s*\(")


def check_sources(root: str) -> tuple[list, dict]:
    """Coarse fallback when Slither could not compile: file-level, low confidence."""
    findings, coverage = [], {}
    for d, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".sol"):
                continue
            path = os.path.join(d, name)
            rel = os.path.relpath(path, root)
            text = _strip_comments(open(path, encoding="utf-8", errors="ignore").read())
            calls = set(_FALLBACK_CALL.findall(text))
            if not calls:
                continue
            coverage[rel] = sorted(calls)
            fn = {"contract": rel, "sig": "(bestand)", "name": rel, "file": rel, "line": 1, "text": text,
                  "high_calls": sorted(calls), "lib_calls": [], "internal": []}
            twap = bool(TIME_AVERAGE_TEXT.search(text))
            for f, meta in check_functions([fn])[0]:
                if f.rule_id == "EVM-ORACLE-SPOT" and twap:
                    continue
                f.confidence = "Low"
                f.detail += " (regex-fallback: Slither-data niet beschikbaar)"
                findings.append((f, meta))
    return findings, coverage


def coverage_line(coverage: dict) -> str:
    if not coverage:
        return "Oracle-dekking: nee — geen externe prijsbron gevonden; oracle-checks niet van toepassing."
    kinds = sorted({k for v in coverage.values() for k in v})
    note = (" — de bescherming van een eigen oracle-contract zit in dát contract en is hier niet beoordeeld"
            if "eigen oracle-contract" in kinds else "")
    return f"Oracle-dekking: ja — prijsbron(nen): {', '.join(kinds)} (in {', '.join(sorted(coverage))}){note}"
