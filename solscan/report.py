"""Finding model + rendering to console / markdown / JSON."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
SEVERITY_WEIGHT = {"Critical": 40, "High": 20, "Medium": 8, "Low": 3, "Info": 0}


@dataclass
class Finding:
    rule_id: str
    title: str
    severity: str          # Critical | High | Medium | Low | Info
    confidence: str        # High | Medium | Low
    file: str
    line: int
    snippet: str
    detail: str
    recommendation: str
    needs_manual_review: bool = True
    privilege: str = ""    # e.g. "GOUD (extern bereikbaar)" / "LAAG (admin-only: onlyOwner)"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanResult:
    target: str
    program_name: str = ""
    findings: list[Finding] = field(default_factory=list)
    contact: dict | None = None     # from security.txt
    files_scanned: int = 0
    noise_removed: int = 0
    errors: list[str] = field(default_factory=list)
    language: str = "rust"          # code-fence language in markdown ("solidity" for EVM)
    summary_lines: list[str] = field(default_factory=list)  # extra header lines (e.g. oracle coverage)

    def sorted_findings(self) -> list[Finding]:
        # EVM findings carry a privilege label: GOUD first, LAAG last (Solana: no label → unchanged)
        prank = {"GOUD": 0, "GOUD?": 1, "n.v.t.": 2, "LAAG": 3}
        return sorted(
            self.findings,
            key=lambda f: (prank.get(f.privilege.split(" ")[0], 0) if f.privilege else 0,
                           SEVERITY_ORDER.get(f.severity, 9), f.file, f.line),
        )

    def risk_score(self) -> int:
        """Rough 0-100 indicator. Not a guarantee — a prioritisation aid."""
        raw = sum(SEVERITY_WEIGHT.get(f.severity, 0) *
                  (1.0 if f.confidence == "High" else 0.6 if f.confidence == "Medium" else 0.3)
                  for f in self.findings)
        return min(100, round(raw))

    def counts(self) -> dict:
        c = {k: 0 for k in SEVERITY_ORDER}
        for f in self.findings:
            c[f.severity] = c.get(f.severity, 0) + 1
        return c

    # -- renderers ----------------------------------------------------------
    def to_json(self) -> str:
        return json.dumps({
            "target": self.target,
            "program_name": self.program_name,
            "files_scanned": self.files_scanned,
            "risk_score": self.risk_score(),
            "counts": self.counts(),
            "contact": self.contact,
            "findings": [f.to_dict() for f in self.sorted_findings()],
            "errors": self.errors,
        }, indent=2)

    def to_console(self, color: bool = True) -> str:
        def c(code, s):
            return f"\033[{code}m{s}\033[0m" if color else s
        sev_color = {"Critical": "1;31", "High": "31", "Medium": "33",
                     "Low": "36", "Info": "90"}
        lines = []
        lines.append("=" * 70)
        lines.append(f" SolScan report  —  {self.program_name or self.target}")
        lines.append("=" * 70)
        counts = self.counts()
        summary = "  ".join(f"{k}:{counts[k]}" for k in SEVERITY_ORDER)
        lines.append(f" files scanned: {self.files_scanned}   risk score: {self.risk_score()}/100")
        if self.noise_removed:
            lines.append(f" (filtered out {self.noise_removed} test/reference/duplicate findings)")
        lines.append(f" {summary}")
        for sl in self.summary_lines:
            lines.append(f" {sl}")
        if self.contact:
            cs = self.contact.get("contacts") or self.contact.get("contact") or "—"
            lines.append(f" disclosure contact: {cs}")
        lines.append("-" * 70)
        for f in self.sorted_findings():
            tag = c(sev_color.get(f.severity, "0"), f"[{f.severity}]")
            review = " (verify manually)" if f.needs_manual_review else ""
            lines.append(f"{tag} {f.rule_id}  {f.title}")
            lines.append(f"    {f.file}:{f.line}   confidence={f.confidence}{review}")
            if f.privilege:
                lines.append(f"    privilege: {f.privilege}")
            lines.append(f"    > {f.snippet}")
            lines.append(f"    {f.detail}")
            lines.append(f"    fix: {f.recommendation}")
            lines.append("")
        if not self.findings:
            lines.append(" No findings from the current rule set.")
        return "\n".join(lines)

    def to_markdown(self) -> str:
        counts = self.counts()
        md = [f"# SolScan report — {self.program_name or self.target}", ""]
        md.append(f"- Files scanned: **{self.files_scanned}**")
        md.append(f"- Risk score: **{self.risk_score()}/100** (prioritisation aid, not a guarantee)")
        md.append("- Findings: " + ", ".join(f"{k} {counts[k]}" for k in SEVERITY_ORDER))
        for sl in self.summary_lines:
            md.append(f"- {sl}")
        if self.contact:
            md.append(f"- Disclosure contact: `{self.contact.get('contacts', '—')}`")
        md.append("")
        for f in self.sorted_findings():
            md.append(f"## [{f.severity}] {f.rule_id} — {f.title}")
            md.append(f"`{f.file}:{f.line}` · confidence {f.confidence}" +
                      (" · **verify manually**" if f.needs_manual_review else "") +
                      (f" · privilege **{f.privilege}**" if f.privilege else ""))
            md.append("")
            md.append(f"```{self.language}")
            md.append(f.snippet)
            md.append("```")
            md.append(f.detail)
            md.append(f"\n**Aanbevolen fix:** {f.recommendation}\n")
        return "\n".join(md)
