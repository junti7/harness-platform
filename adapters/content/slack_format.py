"""Convert LLM markdown into Slack mrkdwn so messages render cleanly.

Slack does not render standard markdown: `**bold**`, `# headers`, and `| tables |`
all show as raw text. This converts:
  - `**bold**` / `__bold__`      -> `*bold*`
  - `# / ## / ### headers`        -> `*bold*`
  - `[text](url)`                 -> `<url|text>`
  - markdown tables               -> monospace code block, column-aligned
                                     (East-Asian width aware, so Korean aligns)

Lists (`- `, `1. `) are left as-is; Slack renders them acceptably. Conversion
skips fenced code blocks (```), leaving their contents untouched.
"""

from __future__ import annotations

import re
import unicodedata

_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def _wlen(s: str) -> int:
    """Display width: East-Asian wide/fullwidth chars count as 2."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _wlen(s))


def _is_table_row(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|") and "|" in line.strip()[1:]


def _is_separator(line: str) -> bool:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{1,}:?", c or "") for c in cells)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _render_table(rows: list[list[str]]) -> str:
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    widths = [max(_wlen(r[c]) for r in rows) for c in range(ncols)]
    lines = []
    for ri, row in enumerate(rows):
        lines.append("| " + " | ".join(_pad(row[c], widths[c]) for c in range(ncols)) + " |")
        if ri == 0:
            lines.append("|-" + "-|-".join("-" * widths[c] for c in range(ncols)) + "-|")
    return "```\n" + "\n".join(lines) + "\n```"


def _convert_inline(line: str) -> str:
    header = _HEADER.match(line)
    if header:
        return f"*{header.group(1)}*"
    line = _BOLD.sub(lambda m: f"*{m.group(1) or m.group(2)}*", line)
    line = _LINK.sub(lambda m: f"<{m.group(2)}|{m.group(1)}>", line)
    return line


def to_slack_mrkdwn(text: str) -> str:
    if not text:
        return text
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    in_fence = False
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue
        # table block: a row followed by a separator row
        if _is_table_row(line) and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            block = [_split_row(line)]
            j = i + 2
            while j < len(lines) and _is_table_row(lines[j]) and not _is_separator(lines[j]):
                block.append(_split_row(lines[j]))
                j += 1
            out.append(_render_table(block))
            i = j
            continue
        out.append(_convert_inline(line))
        i += 1
    return "\n".join(out)
