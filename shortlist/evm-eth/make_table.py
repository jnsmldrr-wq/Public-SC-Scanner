#!/usr/bin/env python3
"""Render results.json from inventory.py as a neutral, alphabetical markdown table."""
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_MD = os.path.join(os.path.dirname(os.path.dirname(HERE)), "evm-inventaris-ethereum.md")

rows = json.load(open(os.path.join(HERE, "results.json")))
recs = sorted(rows.values(), key=lambda r: r["protocol"].lower())


def bucket(cls):
    if cls.startswith("EIGEN CODE"):
        return "eigen code"
    if cls.startswith(("FORK", "STANDAARD")):
        return "fork/standaard"
    if cls.startswith("GEEN VERIFIED SOURCE"):
        return "geen verified source"
    if cls.startswith("PROXY"):
        return "proxy, implementation niet bepaald"
    if cls.startswith("ADRES ONBEKEND"):
        return "adres onbekend"
    if cls.startswith("n.v.t."):
        return "n.v.t. (CEX)"
    return "fout"


def esc(s):
    return str(s or "").replace("|", "\\|")


lines = [
    "# EVM-inventaris Ethereum: eigen code of fork/standaard",
    "",
    "Bron: DeFiLlama (`api.llama.fi/protocols`), Ethereum-TVL $1M–$20M, "
    f"{len(recs)} protocollen. Adressen uit de DeFiLlama-TVL-adapters (contracten waar de TVL staat); "
    "verified source en proxy-implementation via Etherscan v2 (read-only: getsourcecode, eth_getStorageAt, "
    "eth_call op beacon, eth_getCode). Classificatie: heuristiek op contractnamen, imports/paden en "
    "kenmerkende code, plus aandeel eigen regels t.o.v. library-code.",
    "",
    "| protocol | verified source? | proxy? | EIGEN CODE / FORK-van-X / STANDAARD-template | compiler | contract (→ implementation) | adres | opmerking |",
    "|---|---|---|---|---|---|---|---|",
]
for r in recs:
    comp = re.sub(r"\+commit\.[0-9a-f]+", "", r.get("compiler") or "")
    lines.append("| " + " | ".join(esc(x) for x in [
        r["protocol"], r.get("verified", ""), r.get("proxy", ""), r.get("class", ""), comp,
        r.get("contract", ""), r.get("address", ""), r.get("note", "")]) + " |")

c = Counter(bucket(r.get("class", "")) for r in recs)
lines += ["", "## Telling", ""]
for k in ["eigen code", "fork/standaard", "geen verified source", "proxy, implementation niet bepaald",
          "adres onbekend", "n.v.t. (CEX)", "fout"]:
    if c.get(k):
        lines.append(f"- {k}: **{c[k]}**")
fam = Counter(re.sub(r"^(FORK/STANDAARD|STANDAARD-template|STANDAARD):\s*", "", r["class"]).split(" (")[0]
              for r in recs if bucket(r.get("class", "")) == "fork/standaard")
if fam:
    lines += ["", "Fork/standaard per familie: " + ", ".join(f"{k} {v}" for k, v in fam.most_common())]
lines += ["", "## Beperkingen", "",
          "- Het 'hoofdcontract' is het eerste geverifieerde, niet-basistoken-contract uit de DeFiLlama-adapter. "
          "Bij protocollen met veel contracten kan een ander contract meer eigen logica bevatten.",
          "- De familie-heuristiek herkent bekende namen en code-kenmerken; een sterk aangepaste fork kan als "
          "EIGEN CODE eindigen, en eigen code die een bekende interface importeert krijgt de notitie 'integreert X'.",
          "- 'ADRES ONBEKEND' betekent: geen contractadres in de adapter (vaak API- of off-chain-gebaseerde TVL), "
          "of alleen een governance-token.",
          ]
open(OUT_MD, "w").write("\n".join(lines) + "\n")
print(OUT_MD)
print(dict(c))
