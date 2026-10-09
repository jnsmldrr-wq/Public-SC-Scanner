"""
Detectors for well-known Solana / Anchor program vulnerability classes.

Each detector is a function (RustSource) -> list[Finding].
They are deliberately explicit and transparent: you can read exactly why
each flag fires. Heuristic detectors carry a realistic confidence level so
the outreach never over-claims.
"""
from __future__ import annotations

import re

from .report import Finding
from .rustsrc import RustSource, Block

# amount-ish identifiers: used to reduce arithmetic false positives
AMOUNT_HINT = re.compile(
    r"\b(amount|amt|balance|lamports|supply|total|fee|fees|reward|rewards|"
    r"share|shares|price|quantity|qty|stake|debt|collateral|liquidity|"
    r"deposit|withdraw|interest|principal|value|weight|allocation)\b", re.I)


def _mut_state_fn(fn: Block) -> bool:
    """Heuristic: does this fn mutate on-chain state / move value?"""
    b = fn.body
    return any(k in b for k in (
        "&mut ctx.accounts", "try_borrow_mut_lamports", "lamports",
        ".balance", "transfer", "mint_to", "burn", "= amount", "-= ", "+= "))


# ---------------------------------------------------------------------------
# 1. Missing signer authorization
# ---------------------------------------------------------------------------
def detect_missing_signer(src: RustSource) -> list[Finding]:
    out = []
    for st in src.accounts_structs():
        body = st.body
        has_signer = ("Signer<" in body or "is_signer" in body or
                      re.search(r"signer\s*[,)]", body) or "#[account(signer" in body)
        # an authority-like AccountInfo with no signer enforcement is the smell
        authority_fields = re.findall(
            r"(?:#\[account\([^\]]*\)\]\s*)?pub\s+(\w*(?:authority|owner|admin|signer|user|payer)\w*)\s*:\s*"
            r"(AccountInfo|UncheckedAccount)\b", body, re.I)
        constrained = ("has_one" in body or "constraint" in body)
        if authority_fields and not has_signer and not constrained:
            name = authority_fields[0][0]
            off = st.start + body.find(name)
            out.append(Finding(
                rule_id="SOL-AUTH-001",
                title="Authority account is not required to sign",
                severity="Critical",
                confidence="Medium",
                file=src.path,
                line=src.line_of(off),
                snippet=src.snippet(off, 2),
                detail=(f"Account `{name}` steers authorization but is typed as a raw "
                        "AccountInfo/UncheckedAccount with no Signer type, `signer` "
                        "constraint or `has_one`. An attacker can pass any pubkey here."),
                recommendation="Use `Signer<'info>` or add `#[account(signer)]` / a "
                               "`has_one = authority` constraint on the owning account.",
            ))
    return out


# ---------------------------------------------------------------------------
# 2. Missing owner / program check on raw accounts
# ---------------------------------------------------------------------------
def detect_missing_owner_check(src: RustSource) -> list[Finding]:
    out = []
    for st in src.accounts_structs():
        for m in re.finditer(
                r"pub\s+(\w+)\s*:\s*(AccountInfo|UncheckedAccount)\b", st.body):
            field = m.group(1)
            # is the owner verified anywhere (constraint or in a fn body)?
            verified = (f"{field}.owner" in src.text or
                        "owner =" in st.body or "owner=" in st.body or
                        "address =" in st.body)
            if verified:
                continue
            off = st.start + m.start()
            out.append(Finding(
                rule_id="SOL-OWNER-002",
                title="Raw account used without owner/address validation",
                severity="High",
                confidence="Low",
                file=src.path,
                line=src.line_of(off),
                snippet=src.snippet(off, 1),
                detail=(f"`{field}` is a raw account with no owner or address check. "
                        "If its data or lamports are trusted later, an attacker can "
                        "substitute a look-alike account they control."),
                recommendation="Prefer a typed `Account<'info, T>` (checks owner + "
                               "discriminator) or add `#[account(owner = <program>)]` / "
                               "`address = <expected>`.",
            ))
    return out


# ---------------------------------------------------------------------------
# 3. Type confusion / manual deserialization without discriminator
# ---------------------------------------------------------------------------
def detect_type_confusion(src: RustSource) -> list[Finding]:
    out = []
    for m in re.finditer(r"(try_from_slice|deserialize|from_bytes)\s*\(", src.text):
        window = src.text[max(0, m.start() - 160):m.start()]
        if "discriminator" in window or "Account<" in window:
            continue
        out.append(Finding(
            rule_id="SOL-TYPE-003",
            title="Manual deserialization without discriminator check",
            severity="High",
            confidence="Low",
            file=src.path,
            line=src.line_of(m.start()),
            snippet=src.snippet(m.start(), 1),
            detail="Data is deserialized manually. Without an 8-byte account "
                   "discriminator check an attacker can pass a different account "
                   "type with a compatible byte layout (type confusion).",
            recommendation="Use Anchor typed accounts, or verify the discriminator "
                           "before `try_from_slice`.",
        ))
    return out


# ---------------------------------------------------------------------------
# 4. Arbitrary / unchecked CPI
# ---------------------------------------------------------------------------
def detect_unchecked_cpi(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        for m in re.finditer(r"\binvoke(?:_signed)?\s*\(", fn.body):
            off = fn.start + m.start()
            # look for a program-id check in the same function
            checks = ("program_id ==" in fn.body or "key() ==" in fn.body or
                      "address =" in fn.body or "::ID" in fn.body or
                      "assert" in fn.body and "program" in fn.body.lower())
            if checks:
                continue
            out.append(Finding(
                rule_id="SOL-CPI-004",
                title="Cross-program invocation without target program validation",
                severity="High",
                confidence="Medium",
                file=src.path,
                line=src.line_of(off),
                snippet=src.snippet(off, 1),
                detail=f"`invoke` in `{fn.name}` is not preceded by a check that the "
                       "called program's id equals the expected program. An attacker "
                       "can route the CPI to a malicious program.",
                recommendation="Compare the target `program_id` against the expected "
                               "program's `::ID`, or use Anchor CPI wrappers with a "
                               "typed `Program<'info, T>` account.",
            ))
    return out


# ---------------------------------------------------------------------------
# 5. PDA bump handling
# ---------------------------------------------------------------------------
def detect_pda_bump(src: RustSource) -> list[Finding]:
    out = []
    for m in re.finditer(r"create_program_address\s*\(", src.text):
        out.append(Finding(
            rule_id="SOL-PDA-005",
            title="Non-canonical PDA derivation (create_program_address)",
            severity="Medium",
            confidence="Medium",
            file=src.path,
            line=src.line_of(m.start()),
            snippet=src.snippet(m.start(), 1),
            detail="`create_program_address` accepts any bump, including "
                   "non-canonical ones. This enables multiple valid PDAs for the "
                   "same seeds and bump-seed manipulation.",
            recommendation="Use `find_program_address` for the canonical bump, store "
                           "it, and in Anchor enforce `bump = stored_bump`.",
        ))
    return out


# ---------------------------------------------------------------------------
# 6. Re-initialization / init_if_needed misuse
# ---------------------------------------------------------------------------
def detect_reinit(src: RustSource) -> list[Finding]:
    out = []
    for m in re.finditer(r"init_if_needed", src.text):
        out.append(Finding(
            rule_id="SOL-INIT-006",
            title="`init_if_needed` used — re-initialization risk",
            severity="Medium",
            confidence="Medium",
            file=src.path,
            line=src.line_of(m.start()),
            snippet=src.snippet(m.start(), 1),
            detail="`init_if_needed` can re-run on an already-initialized account, "
                   "letting an attacker reset state (e.g. ownership or balances) if "
                   "the handler does not guard against re-init.",
            recommendation="Guard with an explicit `is_initialized` flag check, or "
                           "split create and update into separate instructions.",
        ))
    return out


# ---------------------------------------------------------------------------
# 7. remaining_accounts iterated without validation
# ---------------------------------------------------------------------------
def detect_remaining_accounts(src: RustSource) -> list[Finding]:
    out = []
    for m in re.finditer(r"remaining_accounts", src.text):
        window = src.text[m.start():m.start() + 200]
        if ".owner" in window or "key()" in window or "require" in window:
            continue
        out.append(Finding(
            rule_id="SOL-REMACC-007",
            title="`remaining_accounts` used without per-account validation",
            severity="Medium",
            confidence="Low",
            file=src.path,
            line=src.line_of(m.start()),
            snippet=src.snippet(m.start(), 1),
            detail="Accounts from `remaining_accounts` are attacker-ordered and "
                   "attacker-chosen. Using them without validating owner/key/signer "
                   "is a common injection point.",
            recommendation="Validate each remaining account's owner, key and expected "
                           "role before use.",
        ))
    return out


# ---------------------------------------------------------------------------
# 8. Account close without lamport zeroing / realloc of closed account
# ---------------------------------------------------------------------------
def detect_unsafe_close(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        if "try_borrow_mut_lamports" in fn.body and "+=" in fn.body:
            # draining lamports out of an account manually
            if "= 0" not in fn.body and "sub_lamports" not in fn.body:
                off = fn.start + fn.body.find("try_borrow_mut_lamports")
                out.append(Finding(
                    rule_id="SOL-CLOSE-008",
                    title="Manual lamport move without zeroing source",
                    severity="Medium",
                    confidence="Low",
                    file=src.path,
                    line=src.line_of(off),
                    snippet=src.snippet(off, 1),
                    detail="Lamports are moved by hand. If the source account is not "
                           "zeroed and its data wiped, it can be revived/reused within "
                           "the same transaction (closing-account attack).",
                    recommendation="Use Anchor's `#[account(close = recipient)]` or set "
                                   "source lamports to 0 and clear data.",
                ))
    return out


# ---------------------------------------------------------------------------
# 9. unwrap / expect / panic on handler path (DoS / abort)
# ---------------------------------------------------------------------------
def detect_panic(src: RustSource) -> list[Finding]:
    out = []
    for fn in src.functions():
        for m in re.finditer(r"\.(unwrap|expect)\s*\(", fn.body):
            off = fn.start + m.start()
            out.append(Finding(
                rule_id="SOL-PANIC-009",
                title=f"`{m.group(1)}` on instruction path",
                severity="Low",
                confidence="Medium",
                file=src.path,
                line=src.line_of(off),
                snippet=src.snippet(off, 1),
                detail="A panic aborts the transaction. On attacker-controlled input "
                       "this is at least a griefing/DoS vector and can mask logic bugs.",
                recommendation="Return a typed `Err(ErrorCode::...)` instead of "
                               "unwrap/expect.",
                needs_manual_review=False,
            ))
    return out


KNOWN_DETECTORS = [
    detect_missing_signer,
    detect_missing_owner_check,
    detect_type_confusion,
    detect_unchecked_cpi,
    detect_pda_bump,
    detect_reinit,
    detect_remaining_accounts,
    detect_unsafe_close,
    detect_panic,
]
