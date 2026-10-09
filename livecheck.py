#!/usr/bin/env python3
"""
livecheck — is a Solana program actually live on mainnet?

Run this BEFORE scanning, so no time is spent on forks/dev code that was never
deployed. Read-only: only `getAccountInfo` RPC calls, never a transaction.

Examples
--------
  python3 livecheck.py TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
  python3 livecheck.py targets/reflect-program-library          # pulls declare_id!s
  python3 livecheck.py <id> --devnet                             # also check devnet
  python3 livecheck.py <id> --rpc https://my-rpc.example.com

For a repo path, every own live program also gets a source check (sourcecheck.py):
"VOLLEDIGE BRON" / "SHELL (geen logica)" / "LIVE = PRIVAAT". Disable with --no-source-check.

Exit code: 0 if at least one own program is live on mainnet (and, for repo paths,
has VOLLEDIGE BRON), otherwise 1.
"""
import argparse
import base64
import json
import os
import re
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request

MAINNET_RPC = "https://api.mainnet-beta.solana.com"
DEVNET_RPC = "https://api.devnet.solana.com"

LOADERS = {
    "BPFLoaderUpgradeab1e11111111111111111111111": "BPFLoaderUpgradeable",
    "BPFLoader2111111111111111111111111111111111": "BPFLoader2 (niet upgradebaar)",
    "BPFLoader1111111111111111111111111111111111": "BPFLoader1 (verouderd)",
    "LoaderV411111111111111111111111111111111111": "LoaderV4",
    "NativeLoader1111111111111111111111111111111": "NativeLoader (builtin)",
}

DECLARE_ID_RE = re.compile(r'declare_id!\s*\(\s*"([1-9A-HJ-NP-Za-km-z]{32,44})"\s*\)')
B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
SKIP_DIRS = {".git", "target", "node_modules", ".anchor"}

# Status labels
LIVE, MISSING, NOT_EXEC, UNKNOWN = "LIVE", "BESTAAT NIET", "NIET EXECUTABLE", "ONBEKEND / RPC-FOUT"


class RpcError(Exception):
    pass


def _ssl_context():
    """Verifying TLS context. python.org builds on macOS ship without CA certs, so fall
    back to certifi or the system bundle instead of ever disabling verification."""
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats()["x509_ca"]:
        return ctx
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for path in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return ctx


SSL_CONTEXT = _ssl_context()


def b58encode(raw: bytes) -> str:
    n = int.from_bytes(raw, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58_ALPHABET[r] + out
    pad = len(raw) - len(raw.lstrip(b"\0"))
    return "1" * pad + out


def rpc_call(url, method, params, retries=3, timeout=15):
    """POST a JSON-RPC request. Retries on timeouts, 429 and 5xx. Raises RpcError."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last = "geen antwoord"
    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "solscan-livecheck/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
                payload = json.loads(resp.read().decode())
            if "error" in payload:
                raise RpcError(f"RPC-fout: {payload['error']}")
            if "result" not in payload:
                raise RpcError("RPC-antwoord zonder 'result'")
            return payload["result"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code != 429 and e.code < 500:
                raise RpcError(last)
            wait = float(e.headers.get("Retry-After") or 2 ** attempt)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = f"netwerk/timeout: {getattr(e, 'reason', e)}"
            wait = 2 ** attempt
        except json.JSONDecodeError:
            last = "ongeldige JSON van RPC"
            wait = 2 ** attempt
        if attempt < retries - 1:
            time.sleep(min(wait, 10))
    raise RpcError(last)


def read_programdata(url, address):
    """Return (deploy_slot, upgrade_authority|None) from a ProgramData account.

    Layout (bincode): u32 variant (3 = ProgramData), u64 slot, Option<Pubkey>.
    Only the 45-byte header is fetched, not the whole ELF.
    """
    res = rpc_call(url, "getAccountInfo",
                   [address, {"encoding": "base64", "dataSlice": {"offset": 0, "length": 45}}])
    value = res.get("value")
    if value is None:
        raise RpcError("ProgramData-account niet gevonden")
    raw = base64.b64decode(value["data"][0])
    if len(raw) < 13 or struct.unpack("<I", raw[:4])[0] != 3:
        raise RpcError("onverwacht ProgramData-formaat")
    slot = struct.unpack("<Q", raw[4:12])[0]
    authority = b58encode(raw[13:45]) if raw[12] == 1 and len(raw) >= 45 else None
    return slot, authority


def check(url, program_id):
    """Return a dict describing the program's status on the given cluster. Never guesses."""
    info = {"id": program_id, "status": UNKNOWN}
    try:
        res = rpc_call(url, "getAccountInfo", [program_id, {"encoding": "jsonParsed"}])
    except RpcError as e:
        info["error"] = str(e)
        return info

    value = res.get("value") if isinstance(res, dict) else None
    if isinstance(res, dict) and "value" in res and value is None:
        info["status"] = MISSING
        return info
    if not isinstance(value, dict) or "executable" not in value:
        info["error"] = "onverwacht antwoord van RPC"
        return info

    info["owner"] = value.get("owner")
    info["owner_name"] = LOADERS.get(info["owner"], "onbekende owner")
    if not value["executable"]:
        info["status"] = NOT_EXEC
        return info

    info["status"] = LIVE
    data = value.get("data")
    parsed = data.get("parsed", {}) if isinstance(data, dict) else {}
    pd_addr = (parsed.get("info") or {}).get("programData")
    if pd_addr:
        info["programdata"] = pd_addr
        try:
            info["deploy_slot"], info["upgrade_authority"] = read_programdata(url, pd_addr)
        except RpcError as e:
            info["programdata_error"] = str(e)
    return info


def ids_from_path(path):
    """Map declare_id! -> source file. A program's own id lives in a crate's src/lib.rs;
    ids declared elsewhere are usually vendored copies of external programs (e.g. an
    inlined Metaplex id) and are reported as such."""
    found = {}
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(".rs"):
                continue
            full = os.path.join(root, name)
            try:
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    for m in DECLARE_ID_RE.finditer(fh.read()):
                        found.setdefault(m.group(1), os.path.relpath(full, path))
            except OSError:
                pass
    return found


def describe(info):
    s = info["status"]
    if s == LIVE:
        lines = [f"LIVE (executable), owner: {info['owner_name']}"]
        if "deploy_slot" in info:
            auth = info["upgrade_authority"] or "geen (immutable)"
            lines.append(f"upgrade authority: {auth}")
            lines.append(f"laatste deploy-slot: {info['deploy_slot']}")
        elif "programdata_error" in info:
            lines.append(f"ProgramData: onbekend ({info['programdata_error']})")
        return lines
    if s == NOT_EXEC:
        return [f"account bestaat maar is geen programma (owner: {info['owner']})"]
    if s == MISSING:
        return ["account bestaat niet"]
    return [f"onbekend / RPC-fout: {info.get('error', '?')}"]


def source_check(url, pid, info, repo, crate):
    """Run sourcecheck on a live program's crate and print the details."""
    import sourcecheck
    elf = None
    if info.get("programdata"):
        try:
            elf = sourcecheck.fetch_elf(rpc_call, url, info["programdata"])
        except RpcError as e:
            print(f"  bron:    bytecode niet op te halen ({e})")
    verdict, notes = sourcecheck.assess(crate, repo, elf)
    print(f"  bron:    {verdict}")
    for n in notes:
        print(f"           {n}")
    return verdict.split(" (")[0]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only check of een Solana-programma live op mainnet staat.")
    ap.add_argument("targets", nargs="+", help="program ID(s) of pad naar repo/map")
    ap.add_argument("--rpc", default=MAINNET_RPC, help=f"mainnet RPC-URL (default {MAINNET_RPC})")
    ap.add_argument("--devnet", action="store_true", help="ook tegen devnet checken")
    ap.add_argument("--devnet-rpc", default=DEVNET_RPC)
    ap.add_argument("--no-source-check", action="store_true",
                    help="bij een repo-pad géén echte-code-aanwezig-check doen")
    args = ap.parse_args(argv)

    ids = {}  # id -> source
    external = set()  # ids from vendored modules: checked, but not counted for the exit code
    crates = {}  # id -> (repo root, crate dir), only for ids found in a repo path
    for t in args.targets:
        if os.path.exists(t):
            if os.path.isdir(t) and not args.no_source_check:
                import sourcecheck
                for pid, crate in sourcecheck.find_crates(t).items():
                    crates.setdefault(pid, (t, crate))
            found = ids_from_path(t)
            if not found:
                print(f"[!] geen declare_id! gevonden in {t}")
            for pid, src in found.items():
                ids.setdefault(pid, src)
                if os.path.basename(src) != "lib.rs":
                    external.add(pid)
        elif DECLARE_ID_RE.fullmatch(f'declare_id!("{t}")'):
            ids.setdefault(t, "argument")
        else:
            print(f"[!] '{t}' is geen bestaand pad en geen geldig program ID — overgeslagen")
    if not ids:
        print("Niets te checken.")
        return 1

    any_live = False
    print(f"Mainnet RPC: {args.rpc}" + (f"   Devnet RPC: {args.devnet_rpc}" if args.devnet else ""))
    for pid, src in ids.items():
        tag = "  [extern/vendored — telt niet mee]" if pid in external else ""
        print(f"\n{pid}  ({src}){tag}")
        main_info = check(args.rpc, pid)
        for i, line in enumerate(describe(main_info)):
            print(f"  {'mainnet: ' if i == 0 else '         '}{line}")
        dev_info = None
        if args.devnet:
            dev_info = check(args.devnet_rpc, pid)
            for i, line in enumerate(describe(dev_info)):
                print(f"  {'devnet:  ' if i == 0 else '         '}{line}")

        s = main_info["status"]
        if s == LIVE and pid in external:
            verdict = "ℹ️  live, maar extern programma (niet van dit project) → niet scannen"
        elif s == LIVE and pid in crates:
            source = source_check(args.rpc, pid, main_info, *crates[pid])
            if source == "VOLLEDIGE BRON":
                any_live = True
                verdict = "✅ LIVE OP MAINNET + VOLLEDIGE BRON → waard om te scannen"
            else:
                verdict = f"❌ live, maar bron = {source} → niet scanbaar"
        elif s == LIVE:
            any_live = True
            verdict = "✅ LIVE OP MAINNET → waard om te scannen"
        elif s == UNKNOWN:
            verdict = "⚠️  ONBEKEND (RPC-fout) → opnieuw proberen of andere --rpc"
        else:
            verdict = f"❌ {s.lower()} op mainnet → overslaan"
            if dev_info and dev_info["status"] == LIVE:
                verdict += " (staat alleen op devnet)"
        print(f"  oordeel: {verdict}")

    return 0 if any_live else 1


if __name__ == "__main__":
    sys.exit(main())
