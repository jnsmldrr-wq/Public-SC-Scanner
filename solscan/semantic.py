"""
Type B — semantic / context-sensitive detectors.

These target bug classes that the arithmetic and known-class detectors miss:
oracle freshness, reading account state that a CPI may have changed, and
rounding that systematically favours the user over the protocol.

Honest caveat: these are harder to pin down with static rules than a raw
`+` without `checked_`. They need flow context ("is this value read after a
CPI?"), which regex approximates. So every finding here is Medium/Low
confidence and flagged for manual review — they point your attention, they
do not deliver a verdict. Claude Code (or you) still judges each one.
"""
from __future__ import annotations

import re

from .report import Finding
from .rustsrc import RustSource, Block


def _line_at(fn: Block, needle_off: int, src: RustSource) -> str:
    ln = src.line_of(fn.start + needle_off)
    lines = src.text.splitlines()
    return lines[ln - 1].strip() if 0 < ln <= len(lines) else ""


# ---------------------------------------------------------------------------
# B1. Oracle price read without a freshness / confidence check
# ---------------------------------------------------------------------------
# A price pulled from Pyth / Switchboard must be checked for staleness
# (publish time vs now) and often for confidence interval. Using the price
# without those checks is a classic "oracle returns stale/zero price" exploit.
PRICE_READ = re.compile(
    r"\b(get_price(_unchecked|_no_older_than)?|get_price_unchecked|"
    r"price_feed|load_price|latest_round|get_result|aggregator|"
    r"\.price\b|price_message|oracle)\b", re.I)
FRESH_HINT = re.compile(
    r"(publish_time|publish_slot|no_older_than|staleness|stale|max_age|"
    r"last_updated|valid_slot|slots_since|current_timestamp|clock|"
    r"unix_timestamp|confidence|conf\b|std_dev|max_confidence)", re.I)


def _strip_line_comments(text: str) -> str:
    return "\n".join(ln.split("//", 1)[0] for ln in text.split("\n"))


def detect_oracle_staleness(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        body = _strip_line_comments(fn.body)  # comments must not satisfy checks
        if not PRICE_READ.search(body):
            continue
        # if the function references publish time / confidence / clock at all,
        # assume the author is handling freshness and don't flag.
        if FRESH_HINT.search(body):
            continue
        # must look like it actually uses the price for value math
        if not re.search(r"(price|value|amount|collateral|debt|ltv|"
                         r"liquidat|borrow|repay)", body, re.I):
            continue
        m = PRICE_READ.search(body)
        off = fn.start + m.start()
        out.append(Finding(
            rule_id="SOL-ORACLE-301",
            title="Oracle price used without a freshness/confidence check",
            severity="High",
            confidence="Low",
            file=src.path,
            line=src.line_of(off),
            snippet=_line_at(fn, m.start(), src),
            detail=f"`{fn.name}` reads an oracle price but the function shows no "
                   "staleness check (publish time vs current slot/clock) or "
                   "confidence-interval check. A stale, zero or wide-confidence "
                   "price lets an attacker borrow/liquidate at the wrong value.",
            recommendation="Use `get_price_no_older_than` / compare the publish "
                           "slot to the clock, and reject prices whose confidence "
                           "interval is too wide before using the value.",
        ))
    return out


# ---------------------------------------------------------------------------
# B2. Reading account state after a CPI without reloading (stale read)
# ---------------------------------------------------------------------------
# After invoke()/CPI (e.g. a token transfer), an account's data/balance may
# have changed. Reading a cached field or `.amount` afterwards without
# `reload()` means computing on stale data — a reentrancy-flavoured bug.
CPI_CALL = re.compile(r"\b(invoke(_signed)?|transfer|transfer_checked|"
                      r"mint_to|burn|CpiContext|::cpi::)\b")
RELOAD = re.compile(r"\.reload\s*\(")
POST_READ = re.compile(r"\.(amount|balance|lamports|supply|owner|delegate)\b")


def detect_stale_read_after_cpi(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        body = fn.body
        mcpi = CPI_CALL.search(body)
        if not mcpi:
            continue
        after = body[mcpi.end():]
        # does it read a balance-ish field after the CPI, without reloading?
        mread = POST_READ.search(after)
        if not mread:
            continue
        if RELOAD.search(after[:mread.start()]):
            continue  # reloaded before the read — fine
        off = fn.start + mcpi.end() + mread.start()
        out.append(Finding(
            rule_id="SOL-CPI-302",
            title="Account field read after CPI without reload (stale data)",
            severity="Medium",
            confidence="Low",
            file=src.path,
            line=src.line_of(off),
            snippet=_line_at(fn, mcpi.end() + mread.start(), src),
            detail=f"In `{fn.name}` a balance/amount field is read after a CPI "
                   "without calling `.reload()`. The CPI may have changed that "
                   "account, so the later read can use stale data — a source of "
                   "accounting drift and reentrancy-style bugs.",
            recommendation="Call `account.reload()?` after the CPI before reading "
                           "its `.amount`/balance, or capture the value before the "
                           "CPI if that is what you intend.",
        ))
    return out


# ---------------------------------------------------------------------------
# B3. Rounding direction that favours the user (value leakage)
# ---------------------------------------------------------------------------
# Integer division rounds toward zero. On a value the *protocol pays out*,
# that should round DOWN (protocol-favourable). On a value the protocol
# *collects* (fee, debt, shares minted to the depositor), rounding down
# favours the user and leaks value over time. We flag division assigned to a
# collect-side variable that doesn't use an explicit ceil/round-up helper.
COLLECT_SIDE = re.compile(
    r"\b(\w*(?:fee|debt|owed|borrow|repay|shares_to_mint|mint_amount|"
    r"deposit_shares|collateral_required|required|charge|premium)\w*)\s*=",
    re.I)
CEIL_HINT = re.compile(r"(ceil|round_up|div_ceil|checked_ceil|\+\s*1\b|"
                       r"DIV_UP|round_half_up)", re.I)


def detect_rounding_favours_user(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        base = fn.start
        off = 0
        for raw in fn.body.split("\n"):
            s = raw.strip()
            if (not s.startswith("//") and "/" in s and COLLECT_SIDE.search(s)
                    and "assert" not in s and not CEIL_HINT.search(s)):
                # only when it's really a division (not a path or comment)
                if re.search(r"[\w\)\]]\s*/\s*[\w\(]", s):
                    out.append(Finding(
                        rule_id="SOL-ROUND-303",
                        title="Collect-side value rounds down (favours user)",
                        severity="Medium",
                        confidence="Low",
                        file=src.path,
                        line=src.line_of(base + off),
                        snippet=s,
                        detail="A value the protocol collects (fee/debt/shares) is "
                               "computed with integer division, which rounds toward "
                               "zero. Rounding a collected amount DOWN favours the "
                               "user and leaks value from the protocol on every "
                               "call.",
                        recommendation="Round collect-side amounts UP (ceil/div_ceil) "
                                       "so rounding always favours the protocol; keep "
                                       "payout-side amounts rounding down.",
                    ))
            off += len(raw) + 1
    return out


SEMANTIC_DETECTORS = [
    detect_oracle_staleness,
    detect_stale_read_after_cpi,
    detect_rounding_favours_user,
]
