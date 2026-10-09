"""
Arithmetic, rounding and precision detectors.

This is the module the business leans on: "we find the maths mistakes an
audit skimmed over". These are the most automatable class of real bugs
because they are local and value-flow shaped, but they still need manual
confirmation — so every finding carries a concrete reason and a verify flag.
"""
from __future__ import annotations

import re

from .report import Finding
from .rustsrc import RustSource, Block
from .detectors import AMOUNT_HINT

CHECKED = ("checked_", "saturating_", "wrapping_", "overflowing_")


def _amountish(line: str) -> bool:
    return bool(AMOUNT_HINT.search(line))


def _is_checked(line: str) -> bool:
    return any(k in line for k in CHECKED)


def _iter_code_lines(fn: Block, src: RustSource):
    """Yield (abs_offset, stripped_line) for non-comment lines in a fn body."""
    base = fn.start
    off = 0
    for raw in fn.body.split("\n"):
        s = raw.strip()
        if s and not s.startswith("//"):
            yield base + off, s
        off += len(raw) + 1


# ---------------------------------------------------------------------------
# A1. Raw +,-,*,/ on amount-ish values without checked_/saturating_
# ---------------------------------------------------------------------------
def detect_unchecked_arithmetic(src: RustSource) -> list[Finding]:
    out = []
    op_re = re.compile(r"[A-Za-z0-9_\)\]]\s*([*/+\-])\s*[A-Za-z0-9_\(]")
    for fn in src.functions():
        for off, line in _iter_code_lines(fn, src):
            if _is_checked(line) or not _amountish(line):
                continue
            # ignore obvious non-arithmetic uses
            if line.startswith(("//", "msg!", "require", "emit!")):
                continue
            ops = op_re.findall(line)
            # strip out generic / path tokens like ::<T> and &mut
            if not ops:
                continue
            # subtraction gets its own, higher-severity rule below
            ops = [o for o in ops if o != "-"]
            if not ops:
                continue
            out.append(Finding(
                rule_id="SOL-ARITH-101",
                title="Unchecked arithmetic on value-bearing field",
                severity="High",
                confidence="Medium",
                file=src.path,
                line=src.line_of(off),
                snippet=line,
                detail="Arithmetic on an amount/balance/fee without "
                       "`checked_*`/`saturating_*`. In Solana release builds integer "
                       "overflow wraps silently unless `overflow-checks = true`, so "
                       "this can mint value or corrupt accounting.",
                recommendation="Use `checked_add/sub/mul/div` and propagate the error, "
                               "or `saturating_*` where saturation is the intended "
                               "behaviour.",
            ))
    return out


# ---------------------------------------------------------------------------
# A2. Subtraction that can underflow
# ---------------------------------------------------------------------------
def detect_underflow_sub(src: RustSource) -> list[Finding]:
    out = []
    sub_re = re.compile(r"([A-Za-z0-9_\.\)\]]+)\s*-\s*([A-Za-z0-9_\.\(]+)")
    for fn in src.functions():
        for off, line in _iter_code_lines(fn, src):
            if _is_checked(line) or "->" in line or "=>" in line:
                continue
            if not _amountish(line):
                continue
            m = sub_re.search(line)
            if not m:
                continue
            # skip negative literals / decrement-of-index patterns
            if m.group(2).strip().isdigit() and m.group(1).strip().isdigit():
                continue
            out.append(Finding(
                rule_id="SOL-ARITH-102",
                title="Subtraction can underflow",
                severity="High",
                confidence="Medium",
                file=src.path,
                line=src.line_of(off),
                snippet=line,
                detail=f"`{m.group(1)} - {m.group(2)}` on unsigned values. If the "
                       "right side exceeds the left, release builds wrap to a huge "
                       "number — a classic balance/underflow exploit.",
                recommendation="Use `checked_sub` and return an error on `None`, after "
                               "explicitly checking the invariant (e.g. balance >= "
                               "amount).",
            ))
    return out


# ---------------------------------------------------------------------------
# A3. Division before multiplication -> precision loss
# ---------------------------------------------------------------------------
def detect_div_before_mul(src: RustSource) -> list[Finding]:
    out = []
    # a / b ... * c   (division appearing before a multiplication on the line)
    pat = re.compile(r"/\s*[A-Za-z0-9_\.\(\)]+\s*\*")
    pat2 = re.compile(r"\.checked_div\([^)]*\)\s*\.?\s*checked_mul")
    for fn in src.functions():
        for off, line in _iter_code_lines(fn, src):
            if pat.search(line) or pat2.search(line):
                out.append(Finding(
                    rule_id="SOL-ARITH-103",
                    title="Division before multiplication (precision loss)",
                    severity="Medium",
                    confidence="Medium",
                    file=src.path,
                    line=src.line_of(off),
                    snippet=line,
                    detail="Integer division truncates, so dividing before multiplying "
                           "throws away precision. In fee/share/reward maths this "
                           "systematically mis-allocates value and can round a payout "
                           "to zero.",
                    recommendation="Reorder to multiply first then divide, or compute in "
                                   "u128 with a scaling factor (e.g. 1e9) and divide "
                                   "last.",
                ))
    return out


# ---------------------------------------------------------------------------
# A4. Truncating numeric casts
# ---------------------------------------------------------------------------
def detect_truncating_cast(src: RustSource) -> list[Finding]:
    out = []
    cast_re = re.compile(r"\bas\s+(u8|u16|u32|u64|i8|i16|i32|i64)\b")
    for fn in src.functions():
        wide_ctx = "u128" in fn.body or "i128" in fn.body or "u64" in fn.body
        for off, line in _iter_code_lines(fn, src):
            for m in cast_re.finditer(line):
                target = m.group(1)
                # downcast is only risky to a narrower type than the context
                narrow = target in ("u8", "u16", "u32", "i8", "i16", "i32")
                from_wide = ("u128" in line or "i128" in line or
                             (target == "u64" and "u128" in fn.body))
                if not (narrow or from_wide):
                    continue
                if not (_amountish(line) or wide_ctx):
                    continue
                out.append(Finding(
                    rule_id="SOL-ARITH-104",
                    title=f"Potentially truncating cast `as {target}`",
                    severity="Medium",
                    confidence="Low",
                    file=src.path,
                    line=src.line_of(off),
                    snippet=line,
                    detail=f"Casting to `{target}` silently truncates if the value "
                           "exceeds its range. On amount maths this can wrap a large "
                           "balance down to a small one.",
                    recommendation="Use `u64::try_from(x)?` / `try_into()` so an "
                                   "out-of-range value errors instead of truncating.",
                ))
    return out


# ---------------------------------------------------------------------------
# A5. Integer division producing a payout/share -> rounding direction
# ---------------------------------------------------------------------------
def detect_rounding_payout(src: RustSource) -> list[Finding]:
    out = []
    pay_re = re.compile(
        r"\b(\w*(?:fee|reward|share|payout|amount|interest|yield)\w*)\s*=\s*[^=].*/",
        re.I)
    for fn in src.functions():
        for off, line in _iter_code_lines(fn, src):
            if pay_re.search(line) and "/" in line:
                if "ceil" in line or "round" in line:
                    continue
                out.append(Finding(
                    rule_id="SOL-ARITH-105",
                    title="Rounding direction on a payout/share not explicit",
                    severity="Low",
                    confidence="Low",
                    file=src.path,
                    line=src.line_of(off),
                    snippet=line,
                    detail="Integer division always rounds toward zero. For a value "
                           "the protocol pays out, rounding should favour the "
                           "protocol; for a value it collects, it should favour the "
                           "user. Implicit rounding is a frequent source of slow "
                           "value leakage.",
                    recommendation="Decide and document the rounding direction; use an "
                                   "explicit ceil/floor helper on the side that "
                                   "protects the protocol.",
                    needs_manual_review=True,
                ))
    return out


ARITHMETIC_DETECTORS = [
    detect_unchecked_arithmetic,
    detect_underflow_sub,
    detect_div_before_mul,
    detect_truncating_cast,
    detect_rounding_payout,
]
