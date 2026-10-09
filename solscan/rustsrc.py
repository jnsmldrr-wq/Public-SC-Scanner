"""
Lightweight structural parser for Rust / Anchor Solana program source.

This is intentionally NOT a full Rust parser. It does brace-matched block
extraction so detectors can reason per-function and per-accounts-struct
instead of blindly scanning the whole file. For production you would swap
this for `syn` (Rust) or Semgrep's Rust mode; the detector interface stays
the same.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass, field


@dataclass
class Block:
    """A brace-delimited region of source (a fn body or struct body)."""
    kind: str                 # "fn" | "accounts_struct" | "state_struct"
    name: str
    header: str               # the signature / declaration line(s)
    body: str                 # text inside the outer braces (exclusive)
    start: int                # char offset of body start
    end: int                  # char offset of body end
    attrs: list[str] = field(default_factory=list)  # attributes above the item


class RustSource:
    def __init__(self, text: str, path: str = "<memory>"):
        self.text = text
        self.path = path
        self._line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                self._line_starts.append(i + 1)

    # -- location helpers ---------------------------------------------------
    def line_of(self, offset: int) -> int:
        return bisect.bisect_right(self._line_starts, offset)

    def snippet(self, offset: int, width: int = 1) -> str:
        ln = self.line_of(offset)
        lines = self.text.splitlines()
        lo = max(0, ln - 1)
        hi = min(len(lines), ln - 1 + width)
        return "\n".join(lines[lo:hi]).strip()

    # -- brace matching -----------------------------------------------------
    def _match_brace(self, open_idx: int) -> int:
        """Given index of a '{', return index just past the matching '}'.
        Skips braces inside strings, chars and // and /* */ comments."""
        depth = 0
        i = open_idx
        n = len(self.text)
        in_line_comment = in_block_comment = in_str = in_char = False
        while i < n:
            c = self.text[i]
            nxt = self.text[i + 1] if i + 1 < n else ""
            if in_line_comment:
                if c == "\n":
                    in_line_comment = False
            elif in_block_comment:
                if c == "*" and nxt == "/":
                    in_block_comment = False
                    i += 1
            elif in_str:
                if c == "\\":
                    i += 1
                elif c == '"':
                    in_str = False
            elif in_char:
                if c == "\\":
                    i += 1
                elif c == "'":
                    in_char = False
            else:
                if c == "/" and nxt == "/":
                    in_line_comment = True
                    i += 1
                elif c == "/" and nxt == "*":
                    in_block_comment = True
                    i += 1
                elif c == '"':
                    in_str = True
                elif c == "'" and re.match(r"'\\?.'", self.text[i:i + 4] or ""):
                    in_char = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return i + 1
            i += 1
        return n

    def _attrs_above(self, decl_start: int) -> list[str]:
        """Collect #[...] attribute lines immediately preceding a declaration."""
        head = self.text[:decl_start].rstrip().splitlines()
        attrs = []
        for line in reversed(head):
            s = line.strip()
            if s.startswith("#[") or s.startswith("//") or s.startswith("///") or s == "":
                if s.startswith("#["):
                    attrs.append(s)
                continue
            break
        return list(reversed(attrs))

    # -- item extraction ----------------------------------------------------
    def functions(self) -> list[Block]:
        out = []
        for m in re.finditer(r"\bfn\s+([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\(", self.text):
            brace = self.text.find("{", m.end())
            if brace == -1:
                continue
            # make sure we didn't jump over a ';' (trait decl without body)
            if ";" in self.text[m.end():brace]:
                continue
            end = self._match_brace(brace)
            out.append(Block(
                kind="fn",
                name=m.group(1),
                header=self.text[m.start():brace].strip(),
                body=self.text[brace + 1:end - 1],
                start=brace + 1,
                end=end - 1,
                attrs=self._attrs_above(m.start()),
            ))
        return out

    def _structs(self) -> list[Block]:
        out = []
        for m in re.finditer(r"\bstruct\s+([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\{", self.text):
            brace = self.text.find("{", m.start())
            end = self._match_brace(brace)
            # look back across visibility modifiers + attribute lines
            line_start = self.text.rfind("\n", 0, m.start()) + 1
            attrs = self._attrs_above(line_start)
            pre = self.text[max(0, m.start() - 300):m.start()]
            is_accounts = "derive" in pre and "Accounts" in pre
            out.append(Block(
                kind="accounts_struct" if is_accounts else "state_struct",
                name=m.group(1),
                header=self.text[m.start():brace].strip(),
                body=self.text[brace + 1:end - 1],
                start=brace + 1,
                end=end - 1,
                attrs=attrs,
            ))
        return out

    def accounts_structs(self) -> list[Block]:
        return [b for b in self._structs() if b.kind == "accounts_struct"]

    def state_structs(self) -> list[Block]:
        return [b for b in self._structs() if b.kind == "state_struct"]
