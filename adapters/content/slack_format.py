"""Convert LLM markdown into Slack mrkdwn so messages render cleanly.

Slack does not render standard markdown: `**bold**`, `# headers`, and `| tables |`
all show as raw text. This converts:
  - `**bold**` / `__bold__`      -> `*bold*`
  - `# / ## / ### headers`        -> `*bold*`
  - `[text](url)`                 -> `<url|text>`
  - markdown tables               -> wrapped monospace code block, column-aligned
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


def _strip_markup(s: str) -> str:
    s = _BOLD.sub(lambda m: m.group(1) or m.group(2), s)
    s = _LINK.sub(lambda m: m.group(1), s)
    return s


def _inline_fmt(s: str) -> str:
    s = _BOLD.sub(lambda m: f"*{m.group(1) or m.group(2)}*", s)
    s = _LINK.sub(lambda m: f"<{m.group(2)}|{m.group(1)}>", s)
    return s


_TABLE_WIDTH_LIMIT = 108
_MIN_COL_WIDTH = 4


def _take_width(s: str, width: int) -> tuple[str, str]:
    taken: list[str] = []
    used = 0
    for idx, char in enumerate(s):
        char_width = _wlen(char)
        if used and used + char_width > width:
            return "".join(taken).rstrip(), s[idx:].lstrip()
        if not used and char_width > width:
            return char, s[idx + 1:].lstrip()
        taken.append(char)
        used += char_width
    return "".join(taken).rstrip(), ""


def _wrap_cell(text: str, width: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for word in text.split(" "):
        candidate = word if not current else f"{current} {word}"
        if _wlen(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        remainder = word
        while _wlen(remainder) > width:
            chunk, remainder = _take_width(remainder, width)
            lines.append(chunk)
        current = remainder
    if current:
        lines.append(current)
    return lines or [""]


def _fit_widths(natural: list[int]) -> list[int]:
    ncols = len(natural)
    overhead = 3 * ncols + 1
    available = max(ncols * _MIN_COL_WIDTH, _TABLE_WIDTH_LIMIT - overhead)
    widths = [max(_MIN_COL_WIDTH, min(width, max(_MIN_COL_WIDTH, available // ncols))) for width in natural]
    while sum(widths) > available:
        idx = max(range(ncols), key=lambda i: widths[i])
        if widths[idx] <= _MIN_COL_WIDTH:
            break
        widths[idx] -= 1
    idx = 0
    while sum(widths) < available and any(widths[i] < natural[i] for i in range(ncols)):
        if widths[idx] < natural[idx]:
            widths[idx] += 1
        idx = (idx + 1) % ncols
    return widths


def _format_row(cells: list[str], widths: list[int]) -> list[str]:
    wrapped = [_wrap_cell(cells[i], widths[i]) for i in range(len(widths))]
    height = max(len(cell_lines) for cell_lines in wrapped)
    lines = []
    for line_idx in range(height):
        parts = []
        for col_idx, cell_lines in enumerate(wrapped):
            cell = cell_lines[line_idx] if line_idx < len(cell_lines) else ""
            parts.append(_pad(cell, widths[col_idx]))
        lines.append("| " + " | ".join(parts) + " |")
    return lines


def _render_table(rows: list[list[str]]) -> str:
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    # 폭은 서식 제거(plain) 기준으로 계산 (코드블록 안은 서식이 적용 안 됨).
    plain = [[_strip_markup(c).strip() for c in row] for row in rows]
    natural = [max(_wlen(plain[r][c]) for r in range(len(plain))) for c in range(ncols)]
    widths = _fit_widths(natural)
    lines: list[str] = []
    for ri, row in enumerate(plain):
        lines.extend(_format_row(row, widths))
        if ri == 0:
            lines.append("|-" + "-|-".join("-" * width for width in widths) + "-|")
    return "```\n" + "\n".join(lines) + "\n```"


def _convert_inline(line: str) -> str:
    header = _HEADER.match(line)
    if header:
        return f"*{header.group(1)}*"
    return _inline_fmt(line)


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
