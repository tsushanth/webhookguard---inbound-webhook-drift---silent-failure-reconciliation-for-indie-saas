"""Render drift findings as a CLI table + summary line."""

from collections import Counter

_KIND_ORDER = ("missing", "duplicate", "late")


def render(findings, provider):
    lines = []
    if not findings:
        lines.append(f"No drift found for provider '{provider}'. Handler matches source-of-truth.")
        return "\n".join(lines)

    header = f"{'KIND':<10} {'EVENT ID':<20} DETAIL"
    lines.append(header)
    lines.append("-" * len(header))
    for finding in findings:
        lines.append(f"{finding.kind.upper():<10} {finding.event_id:<20} {finding.detail}")

    counts = Counter(f.kind for f in findings)
    summary_parts = [f"{counts[k]} {k}" for k in _KIND_ORDER if counts.get(k)]
    lines.append("")
    lines.append(f"{len(findings)} drift findings: " + ", ".join(summary_parts))
    return "\n".join(lines)
