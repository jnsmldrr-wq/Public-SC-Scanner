#!/usr/bin/env python3
"""
SolScan CLI.

Examples
--------
  python scan.py samples/vulnerable_vault.rs
  python scan.py path/to/anchor/program/
  python scan.py --github https://github.com/org/repo
  python scan.py samples/vulnerable_vault.rs --json report.json --md report.md
  python scan.py samples/vulnerable_vault.rs --draft-outreach
"""
import argparse
import sys

from solscan.scanner import scan_path, clone_and_scan


def draft_outreach(result) -> str:
    """Produce a NEUTRAL, non-coercive disclosure note.

    It describes findings and offers help. It never ties fixing the bug to a
    purchase — that framing ('pay or else') reads as extortion. Report free,
    sell the ongoing monitoring separately.
    """
    counts = result.counts()
    top = [f for f in result.sorted_findings()
           if f.severity in ("Critical", "High")][:3]
    who = (result.contact or {}).get("contacts", "security contact")
    lines = [
        f"To: {who}",
        f"Subject: Security findings in {result.program_name}",
        "",
        "Hi,",
        "",
        f"While reviewing publicly available Solana programs, our static "
        f"analysis flagged {counts['Critical']} critical and {counts['High']} "
        f"high-severity issues in {result.program_name}. Sharing them below so "
        "you can review — no strings attached.",
        "",
    ]
    for f in top:
        lines.append(f"- [{f.severity}] {f.title} ({f.file}:{f.line}) — "
                     f"{f.detail.split('.')[0]}.")
    lines += [
        "",
        "These are automated findings and should be verified by your team; "
        "happy to share full reproduction detail privately.",
        "",
        "Separately, we run a service that monitors deployed programs for this "
        "class of issue continuously. If that's useful I'm glad to show you how "
        "it works — entirely optional and unrelated to the report above.",
        "",
        "Best regards,",
    ]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="SolScan — Solana program vuln scanner")
    ap.add_argument("target", nargs="?", help="path to .rs file or program directory")
    ap.add_argument("--github", help="clone and scan a public GitHub repo URL")
    ap.add_argument("--ref", help="git branch/tag to clone")
    ap.add_argument("--json", help="write JSON report to this path")
    ap.add_argument("--md", help="write markdown report to this path")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--min-severity", default="Info",
                    choices=["Critical", "High", "Medium", "Low", "Info"])
    ap.add_argument("--include-tests", action="store_true",
                    help="do NOT filter out test/reference/duplicate findings")
    ap.add_argument("--draft-outreach", action="store_true",
                    help="print a non-coercive disclosure email draft")
    args = ap.parse_args(argv)

    if args.github:
        result = clone_and_scan(args.github, args.ref, include_tests=args.include_tests)
    elif args.target:
        result = scan_path(args.target, include_tests=args.include_tests)
    else:
        ap.error("provide a target path or --github URL")

    from solscan.report import SEVERITY_ORDER
    cutoff = SEVERITY_ORDER[args.min_severity]
    result.findings = [f for f in result.findings
                       if SEVERITY_ORDER.get(f.severity, 9) <= cutoff]

    print(result.to_console(color=not args.no_color))

    if args.json:
        open(args.json, "w").write(result.to_json())
        print(f"\n[+] JSON written to {args.json}")
    if args.md:
        open(args.md, "w").write(result.to_markdown())
        print(f"[+] Markdown written to {args.md}")
    if args.draft_outreach:
        print("\n" + "=" * 70 + "\n DRAFT OUTREACH (review before sending)\n" + "=" * 70)
        print(draft_outreach(result))

    # exit non-zero if anything Critical/High, for CI usage
    worst = min((SEVERITY_ORDER.get(f.severity, 9) for f in result.findings), default=9)
    return 1 if worst <= 1 else 0


if __name__ == "__main__":
    sys.exit(main())
