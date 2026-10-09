#!/usr/bin/env python3
"""
sourcecheck — does a repo contain the REAL program logic, or only a shell?

A `declare_id!` in `src/lib.rs` does not prove the repo is the deployed program:
some projects publish only state layouts and instruction builders (an SDK),
while the live program is built from private source (lesson from Larix).

Per program crate, three checks (read-only; bytecode via `getAccountInfo`):
  1. entrypoint  — an Anchor `#[program]` module, or a native `entrypoint!(f)`
                   whose `f` actually dispatches (not commented out / only `Ok(())`)
  2. handlers    — real handler logic exists (non-trivial `#[program]` fns, or a
                   processor.rs / processor/ / processors/ with non-trivial bodies)
  3. bytecode    — crate-local source paths (`src/...rs`) embedded in the live ELF
                   (panic locations) must exist in the repo; paths to files that are
                   not in the repo mean the live code was built from private source

Verdicts: "VOLLEDIGE BRON" / "SHELL (geen logica)" / "LIVE = PRIVAAT".
Only "VOLLEDIGE BRON" counts as really scannable.

Usage (normally called by livecheck.py for repo paths):
  python3 sourcecheck.py <repo-path> [--rpc URL] [--no-bytecode]
"""
import argparse
import base64
import os
import re
import sys

FULL, SHELL, PRIVATE = "VOLLEDIGE BRON", "SHELL (geen logica)", "LIVE = PRIVAAT"

SKIP_DIRS = {".git", "target", "node_modules", ".anchor"}
DECLARE_ID_RE = re.compile(r'declare_id!\s*\(\s*"([1-9A-HJ-NP-Za-km-z]{32,44})"\s*\)')
ENTRY_RE = re.compile(r'\b(?:program_)?(?:lazy_)?entrypoint!\s*\(\s*([A-Za-z_]\w*)')
# `#[program]` may be followed by other attributes (e.g. #[allow(...)]) before the mod
PROGRAM_MOD_RE = re.compile(r'#\[program\]\s*(?:#\[[^\]]*\]\s*)*(?:pub\s+)?mod\s+\w+\s*\{')
FN_RE = re.compile(r'\bfn\s+([A-Za-z_]\w*)\s*(?:<[^{;]*?>)?\s*\(')
# crate-local panic paths in the ELF, optionally prefixed by a workspace member dir
ELF_PATH_RE = re.compile(rb'(?:programs/[\w.-]+/)?src/[\w/.-]+?\.rs')
HANDLER_FILE_RE = re.compile(r'(processor|processors|instructions?|handler|entrypoint)', re.I)


def strip_comments(text):
    """Remove // and (nested) /* */ comments, string-literal aware.

    String contents are kept but blanked to spaces, so braces or `//` inside
    strings (URLs, globs, format strings) can't break brace matching or eat code.
    Handles "..." with escapes, raw strings r"..."/r#"..."#, b"..." and char
    literals ('x', '\\n'); lifetimes ('a) are left alone.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":                      # line comment
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif c == "/" and nxt == "*":                    # block comment (nestable)
            depth, i = 1, i + 2
            while i < n and depth:
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            out.append(" ")
        elif c == "r" and re.match(r'r#*"', text[i:i + 8]) and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")):
            hashes = len(re.match(r'r(#*)"', text[i:]).group(1))
            end = text.find('"' + "#" * hashes, i + 2 + hashes)
            end = n if end < 0 else end + 1 + hashes
            out.append('""')
            i = end
        elif c == '"':                                   # normal / byte string
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append('""')
            i = j + 1
        elif c == "'" and re.match(r"'(\\.[^']*|[^\\'])'", text[i:i + 12]):   # char literal
            m = re.match(r"'(\\.[^']*|[^\\'])'", text[i:i + 12])
            out.append("' '")
            i += m.end()
        else:
            out.append(c)
            i += 1
    return "".join(out)


def block_after(text, open_idx):
    """Return the body between the brace at/after open_idx and its matching close."""
    i = text.find("{", open_idx)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
    return text[i + 1:]


def fn_bodies(text):
    """Yield (name, body) for every fn with a body in comment-stripped text."""
    for m in FN_RE.finditer(text):
        # skip trait/extern declarations without a body (`;` before `{`)
        semi, brace = text.find(";", m.end()), text.find("{", m.end())
        if brace < 0 or (0 <= semi < brace):
            continue
        yield m.group(1), block_after(text, m.end())


def trivial(body):
    """True if a body does nothing: empty, or only `Ok(())`."""
    b = re.sub(r'\s+', '', body)
    return b in ("", "Ok(())", "Ok(());", "returnOk(());")


def rust_files(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(".rs"):
                yield os.path.join(d, f)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return strip_comments(fh.read())
    except OSError:
        return ""


def find_crates(repo):
    """Program crates: dirs with Cargo.toml + src/lib.rs containing a declare_id!."""
    crates = {}
    for d, dirs, files in os.walk(repo):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        lib = os.path.join(d, "src", "lib.rs")
        if "Cargo.toml" in files and os.path.isfile(lib):
            # keep string literals here (read() blanks them); only drop // comment lines
            try:
                with open(lib, encoding="utf-8", errors="ignore") as fh:
                    raw = re.sub(r"(?m)^\s*//.*$", "", fh.read())
            except OSError:
                raw = ""
            # all ids (cfg-selected mainnet/devnet/localnet variants map to the same crate)
            for pid in DECLARE_ID_RE.findall(raw):
                crates.setdefault(pid, d)
    return crates


def check_entry_and_handlers(crate):
    """Checks 1 and 2 on the crate's source. Returns (entry_ok, handlers_ok, notes)."""
    sources = {p: read(p) for p in rust_files(os.path.join(crate, "src"))}
    allsrc = "\n".join(sources.values())
    notes = []

    # --- 1. entrypoint -----------------------------------------------------
    anchor = PROGRAM_MOD_RE.search(allsrc)
    entry_ok = False
    if anchor:
        entry_ok = True
        notes.append("entrypoint: Anchor #[program]-module")
    elif re.search(r'\bsolitaire!\s*\{', allsrc):
        entry_ok = True
        notes.append("entrypoint: Solitaire-dispatch (solitaire!-macro)")
    else:
        m = ENTRY_RE.search(allsrc)
        if not m:
            notes.append("entrypoint: GEEN entrypoint!/#[program] gevonden")
        else:
            name = m.group(1)
            body = next((b for n, b in fn_bodies(allsrc) if n == name), None)
            if body is None:
                # entry fn defined elsewhere (e.g. a processor fn passed directly)
                entry_ok = True
                notes.append(f"entrypoint: entrypoint!({name}) → extern gedefinieerd")
            elif trivial(body):
                notes.append(f"entrypoint: entrypoint!({name}) doet niets (alleen Ok(()) / "
                             "dispatch uitgecommentarieerd)")
            else:
                entry_ok = True
                notes.append(f"entrypoint: entrypoint!({name}) schakelt door")

    # --- 2. handler logic --------------------------------------------------
    nontrivial = 0
    if anchor:
        prog_body = block_after(allsrc, anchor.start())
        nontrivial = sum(1 for _, b in fn_bodies(prog_body) if not trivial(b))
        where = "#[program]-handlers"
    else:
        # native programs keep their dispatch anywhere (processor.rs, state.rs, ...):
        # count non-trivial process*/handle* fns across the whole crate
        nontrivial = sum(1 for p in sources for n, b in fn_bodies(sources[p])
                         if not trivial(b) and n.startswith(("process", "handler", "handle")))
        where = "process*/handle*-functies in de crate"
        if nontrivial == 0:
            # frameworks like Solitaire name handlers after the instruction (api/*.rs)
            api = [p for p in sources if re.search(r'[\\/](api|instructions?|processors?)[\\/]', p)]
            nontrivial = sum(1 for p in api for n, b in fn_bodies(sources[p]) if not trivial(b))
            where = "niet-triviale functies in api/instructions-modules"
    handlers_ok = nontrivial > 0
    notes.append(f"handlers: {nontrivial} niet-triviale {where}")
    return entry_ok, handlers_ok, notes


def elf_paths(elf):
    """Crate-local source paths embedded in an ELF (skip absolute/registry paths)."""
    out = set()
    for m in ELF_PATH_RE.finditer(elf):
        before = elf[m.start() - 1:m.start()] if m.start() else b""
        if before == b"/":
            continue  # part of an absolute path, i.e. a dependency or toolchain file
        out.add(m.group(0).decode("ascii", "ignore"))
    return out


def check_bytecode(crate, repo, elf):
    """Check 3. Returns (private: bool|None, missing, present, notes).

    Newer Solana toolchains store dependency paths trimmed to a bare `src/...rs`
    (e.g. solana-program's `src/account_info.rs`), indistinguishable from the
    crate's own files. Only unambiguous evidence counts as "built from private source":
      - workspace-prefixed paths `programs/<this crate>/src/...` missing from the repo;
      - bare `src/<subdir>/...` paths whose <subdir> exists in this crate but whose
        file does not (e.g. src/state/mining.rs next to a real src/state/).
    If the ELF has workspace-prefixed paths for this crate, bare `src/` paths are
    taken to be dependencies. Other missing bare paths are reported as unclear.
    """
    paths = elf_paths(elf)
    if not paths:
        return None, [], [], ["bytecode: geen bronpaden in ELF gevonden — niet te vergelijken"]
    repo_files = {os.path.relpath(p, repo).replace(os.sep, "/") for p in rust_files(repo)}
    crate_rel = os.path.relpath(crate, repo).replace(os.sep, "/")
    crate_name = os.path.basename(os.path.abspath(crate))
    own_prefix = f"programs/{crate_name}/"
    prefixed = {p for p in paths if p.startswith(own_prefix)}
    other_prefixed = {p for p in paths if p.startswith("programs/") and p not in prefixed}
    bare = paths - prefixed - other_prefixed

    def in_repo(p):
        cands = {p, f"{crate_rel}/{p}" if crate_rel != "." else p}
        return bool(cands & repo_files) or any(f.endswith("/" + p) for f in repo_files)

    present = sorted(p for p in paths if in_repo(p))
    missing_own, unclear = [], []
    for p in sorted(paths - set(present)):
        if p in other_prefixed:
            continue  # another workspace member compiled in; not this crate's evidence
        if p in prefixed:
            missing_own.append(p)
        elif prefixed:
            continue  # workspace build: bare src/ paths are dependencies
        else:
            sub = p.split("/")[1] if p.count("/") >= 2 else None
            if sub and os.path.isdir(os.path.join(crate, "src", sub)):
                missing_own.append(p)
            else:
                unclear.append(p)
    private = bool(missing_own)
    notes = [f"bytecode: {len(paths)} bronpaden; {len(present)} in repo; "
             f"{len(missing_own)} eigen bestanden NIET in repo; "
             f"{len(unclear)} onduidelijk (mogelijk dependency)"]
    if missing_own:
        notes.append("  ontbreekt (eigen): " + ", ".join(missing_own[:12])
                     + (" …" if len(missing_own) > 12 else ""))
    if unclear:
        notes.append("  onduidelijk: " + ", ".join(unclear[:8]) + (" …" if len(unclear) > 8 else ""))
    return private, missing_own, present, notes


def assess(crate, repo, elf=None):
    """Full assessment of one program crate. Returns (verdict, notes)."""
    entry_ok, handlers_ok, notes = check_entry_and_handlers(crate)
    private = None
    if elf is not None:
        private, _, _, bnotes = check_bytecode(crate, repo, elf)
        notes += bnotes
    else:
        notes.append("bytecode: niet opgehaald")
    if private:
        return PRIVATE + ("" if entry_ok and handlers_ok else " (repo = schil)"), notes
    if not (entry_ok and handlers_ok):
        return SHELL, notes
    return FULL, notes


def fetch_elf(rpc_call, url, programdata):
    """Download the program bytes from a ProgramData account (read-only)."""
    res = rpc_call(url, "getAccountInfo", [programdata, {"encoding": "base64"}])
    value = res.get("value")
    if not value:
        return None
    return base64.b64decode(value["data"][0])[45:].rstrip(b"\0")


def main(argv=None):
    import livecheck  # reuse its RPC helpers

    ap = argparse.ArgumentParser(description="Check of een repo de echte programmalogica bevat.")
    ap.add_argument("repo")
    ap.add_argument("--rpc", default=livecheck.MAINNET_RPC)
    ap.add_argument("--no-bytecode", action="store_true")
    args = ap.parse_args(argv)

    crates = find_crates(args.repo)
    if not crates:
        print("Geen programma-crates (src/lib.rs met declare_id!) gevonden.")
        return 1
    any_full = False
    for pid, crate in crates.items():
        elf = None
        if not args.no_bytecode:
            info = livecheck.check(args.rpc, pid)
            if info.get("programdata"):
                try:
                    elf = fetch_elf(livecheck.rpc_call, args.rpc, info["programdata"])
                except livecheck.RpcError:
                    elf = None
        verdict, notes = assess(crate, args.repo, elf)
        any_full |= verdict == FULL
        print(f"\n{pid}  ({os.path.relpath(crate, args.repo)})\n  bron: {verdict}")
        for n in notes:
            print(f"    {n}")
    return 0 if any_full else 1


if __name__ == "__main__":
    sys.exit(main())
