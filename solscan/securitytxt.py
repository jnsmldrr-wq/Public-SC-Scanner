"""
Extract the responsible-disclosure contact (Neodyme `security_txt!` macro)
and project-level config smells (Cargo overflow-checks).

The security_txt macro embeds fields like name, contacts, policy,
source_code and preferred_languages directly in the program binary and
source. It is exactly the channel you use to warn an owner for free.
"""
from __future__ import annotations

import os
import re

from .report import Finding
from .rustsrc import RustSource

FIELD_RE = re.compile(r'"([A-Za-z_]+)"\s*,\s*"([^"]*)"')


def parse_security_txt(text: str) -> dict | None:
    m = re.search(r"security_txt!\s*\{(.*?)\}", text, re.S)
    if not m:
        return None
    fields = dict(FIELD_RE.findall(m.group(1)))
    return fields or None


def find_contact_in_tree(root: str) -> dict | None:
    for dirpath, _dirs, files in os.walk(root):
        if "target" in dirpath.split(os.sep):
            continue
        for fn in files:
            if fn.endswith(".rs"):
                p = os.path.join(dirpath, fn)
                try:
                    with open(p, encoding="utf-8", errors="ignore") as fh:
                        c = parse_security_txt(fh.read())
                    if c:
                        c["_source_file"] = os.path.relpath(p, root)
                        return c
                except OSError:
                    continue
    return None


def check_cargo_overflow(root: str) -> list[Finding]:
    """Flag Cargo.toml files that don't force overflow checks in release."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        if "target" in dirpath.split(os.sep):
            continue
        if "Cargo.toml" in files:
            p = os.path.join(dirpath, "Cargo.toml")
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            rel = os.path.relpath(p, root)
            # strip comments so a commented example can't be mistaken for config
            code = "\n".join(ln.split("#", 1)[0] for ln in txt.splitlines())
            if "[workspace]" in code and "[package]" not in code:
                continue
            has = re.search(r"overflow-checks\s*=\s*true", code)
            if not has:
                line = 1
                m = re.search(r"\[profile\.release\]", txt)
                if m:
                    line = txt[:m.start()].count("\n") + 1
                out.append(Finding(
                    rule_id="SOL-CFG-201",
                    title="Release profile does not force overflow checks",
                    severity="High",
                    confidence="High",
                    file=rel,
                    line=line,
                    snippet="[profile.release]  # missing overflow-checks = true",
                    detail="Without `overflow-checks = true`, every unchecked "
                           "arithmetic finding in this program silently wraps in the "
                           "deployed release build instead of aborting.",
                    recommendation="Add `overflow-checks = true` under "
                                   "`[profile.release]` in the workspace Cargo.toml.",
                    needs_manual_review=False,
                ))
    return out
