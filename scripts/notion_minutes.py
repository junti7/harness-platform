"""Save orchestration meeting minutes to Notion.

Requires env:
  NOTION_API_KEY
  NOTION_MINUTES_DATABASE_ID  (별도 회의록 DB; 없으면 NOTION_DATABASE_ID 사용)

Database must have a title property named "제목".
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

# Deterministic .env loading: avoid find_dotenv() edge-cases in non-standard entrypoints.
load_dotenv(dotenv_path=".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_MINUTES_DATABASE_ID = (
    os.getenv("NOTION_MINUTES_DATABASE_ID")
    or os.getenv("NOTION_DATABASE_ID", "")
).split("?")[0]
NOTION_VERSION = "2022-06-28"


def _rich(text: str, *, bold: bool = False, code: bool = False, color: str | None = None) -> dict:
    ann: dict[str, Any] = {"bold": bold, "code": code}
    if color:
        ann["color"] = color
    node: dict[str, Any] = {"type": "text", "text": {"content": (text or "")[:2000]}, "annotations": ann}
    return node


def _rt(*nodes: dict) -> list[dict]:
    return [n for n in nodes if n and isinstance(n, dict)]


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rt(_rich(text))}}


def _heading_2(text: str) -> dict:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _rt(_rich(text, bold=True))}}


def _bul(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _rt(_rich(text))}}


def _todo(text: str, *, checked: bool = False) -> dict:
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {"rich_text": _rt(_rich(text)), "checked": bool(checked)},
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _callout(text: str, *, emoji: str = "📋", color: str = "blue_background") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": _rt(_rich(text)),
            "icon": {"type": "emoji", "emoji": emoji},
            "color": color,
        },
    }


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _blocks_from_markdown(md: str) -> list[dict]:
    blocks: list[dict] = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                            "heading_3": {"rich_text": [_rich(s[4:], bold=True)]}})
        elif s.startswith("## "):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            blocks.append({"object": "block", "type": "heading_2",
                            "heading_2": {"rich_text": [_rich("🔹 " + s[3:], bold=True)]}})
        elif s.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                            "heading_1": {"rich_text": [_rich("🏛️ " + s[2:], bold=True)]}})
        elif s.startswith("- ") or s.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": [_rich(s[2:])]}})
        elif re.match(r"^\d+\. ", s):
            content = re.sub(r"^\d+\. ", "", s)
            blocks.append({"object": "block", "type": "numbered_list_item",
                            "numbered_list_item": {"rich_text": [_rich(content)]}})
        elif s.startswith("|") and s.endswith("|"):
            # 테이블 행 → bullet로 변환 (Notion API 테이블은 구현 복잡)
            cells = [c.strip() for c in s.strip("|").split("|") if c.strip() and c.strip() != "---"]
            if cells:
                blocks.append({"object": "block", "type": "bulleted_list_item",
                                "bulleted_list_item": {"rich_text": [_rich(" | ".join(cells))]}})
        elif s.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [_rich(s)]}})
    return blocks


def save_minutes(
    correlation_id: str,
    order: str,
    personas: list[str],
    minutes_text: str,
    cost_usd: float,
    *,
    minutes_blocks: list[dict] | None = None,
) -> str | None:
    """Create a Notion page with meeting minutes. Returns page URL or None on failure."""
    if not NOTION_API_KEY or not NOTION_MINUTES_DATABASE_ID:
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"[회의록] {date_str} — {correlation_id}"

    meta_blocks: list[dict] = [
        _callout((order or "").strip()[:220] or "(회의 주제 없음)"),
        _paragraph(f"참여 팀: {', '.join(personas)}  |  비용: ${cost_usd:.3f}  |  ID: {correlation_id}"),
        _divider(),
    ]
    content_blocks = minutes_blocks if minutes_blocks is not None else _blocks_from_markdown(minutes_text)
    all_blocks = (meta_blocks + content_blocks)[:100]  # Notion API child blocks limit is low; keep it safe.

    headers = _notion_headers()
    payload = {
        "parent": {"database_id": NOTION_MINUTES_DATABASE_ID},
        "properties": {"제목": {"title": [{"text": {"content": title}}]}},
        "children": all_blocks,
    }
    try:
        r = httpx.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30.0)
        r.raise_for_status()
        return r.json().get("url")
    except Exception as exc:
        print(f"[notion_minutes] 저장 실패: {exc}")
        return None


def query_minutes_pages_by_correlation_id(correlation_id: str, *, page_size: int = 10) -> list[dict[str, Any]]:
    """Find minutes pages whose title contains the correlation_id.

    Note: Notion "delete" is archive; this helper returns raw pages so callers can archive selectively.
    """
    if not NOTION_API_KEY or not NOTION_MINUTES_DATABASE_ID:
        return []
    cid = (correlation_id or "").strip()
    if not cid:
        return []
    headers = _notion_headers()
    payload = {
        "page_size": int(page_size),
        "filter": {"property": "제목", "title": {"contains": cid}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
    }
    try:
        r = httpx.post(
            f"https://api.notion.com/v1/databases/{NOTION_MINUTES_DATABASE_ID}/query",
            headers=headers,
            json=payload,
            timeout=20.0,
        )
        r.raise_for_status()
        return list(r.json().get("results", []) or [])
    except Exception as exc:
        print(f"[notion_minutes] query 실패: {exc}")
        return []


def archive_page(page_id: str) -> bool:
    """Archive (soft-delete) a Notion page."""
    if not NOTION_API_KEY:
        return False
    pid = (page_id or "").strip()
    if not pid:
        return False
    headers = _notion_headers()
    try:
        r = httpx.patch(
            f"https://api.notion.com/v1/pages/{pid}",
            headers=headers,
            json={"archived": True},
            timeout=20.0,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        print(f"[notion_minutes] archive 실패: {exc}")
        return False


def build_minutes_blocks_from_decision_card(
    decision_md: str,
    *,
    ts: str | None = None,
    correlation_id: str | None = None,
    limit: int = 90,
) -> list[dict]:
    """Render a decision-card markdown into clean Notion blocks (executive-friendly, bullet-first)."""

    def parse_sections(text: str) -> dict[str, str]:
        text = (text or "").strip()
        if not text:
            return {}
        sections: dict[str, list[str]] = {"body": []}
        current = "body"
        for line in text.splitlines():
            m = re.match(r"^\s*##\s+(.+?)\s*$", line)
            if m:
                current = m.group(1).strip()
                sections.setdefault(current, [])
                continue
            sections[current].append(line.rstrip())
        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def normalize_heading(text: str) -> str:
        return re.sub(r"[\s()·—\-_/]+", "", (text or "").lower())

    def find_section(sections_map: dict[str, str], *needles: str) -> str:
        normalized_needles = [normalize_heading(needle) for needle in needles if needle]
        for key, value in sections_map.items():
            key_norm = normalize_heading(key)
            if any(needle in key_norm for needle in normalized_needles):
                return value
        return ""

    def bullets(section_text: str, lim: int) -> list[str]:
        out: list[str] = []
        for raw in (section_text or "").splitlines():
            s = raw.strip()
            if not s:
                continue
            if s.startswith(("-", "*")) and len(s) > 2:
                x = s[2:].strip().replace("**", "").replace("*", "")
                out.append(re.sub(r"\s+", " ", x)[:320])
        return out[:lim]

    def numbered(section_text: str, lim: int) -> list[str]:
        lines = (section_text or "").splitlines()
        items: list[str] = []
        buf: list[str] = []
        for raw in lines:
            s = raw.strip()
            if not s:
                continue
            m = re.match(r"^\d+\.\s+(.*)$", s)
            if m:
                if buf:
                    items.append(" ".join(buf).strip())
                    buf = []
                buf = [m.group(1).strip()]
                continue
            if buf and not re.match(r"^[-*]\s+", s):
                buf.append(s)
        if buf:
            items.append(" ".join(buf).strip())
        cleaned = []
        for it in items[:lim]:
            x = re.sub(r"\s+", " ", it).strip().replace("**", "").replace("*", "")
            cleaned.append(x[:300])
        return cleaned

    def table_rows(section_text: str, lim: int, *, skip_headers: tuple[str, ...] = ()) -> list[str]:
        rows: list[str] = []
        normalized_headers = {header.lower() for header in skip_headers}
        for raw in (section_text or "").splitlines():
            s = raw.strip()
            if not (s.startswith("|") and s.endswith("|")):
                continue
            if re.search(r"\|\s*-+\s*\|", s):
                continue
            cells = [c.strip().replace("**", "").replace("*", "") for c in s.strip("|").split("|")]
            cells = [re.sub(r"\s+", " ", cell).strip() for cell in cells if cell.strip()]
            if len(cells) < 2:
                continue
            if cells[0].lower() in normalized_headers:
                continue
            row = f"{cells[0]} — {cells[1]}"
            if len(cells) >= 3:
                row += f": {cells[2]}"
            rows.append(row[:360])
        return rows[:lim]

    def hybrid_items(section_text: str, lim: int, *, skip_headers: tuple[str, ...] = ()) -> list[str]:
        extracted = bullets(section_text, lim)
        if extracted:
            return extracted
        extracted = numbered(section_text, lim)
        if extracted:
            return extracted
        extracted = table_rows(section_text, lim, skip_headers=skip_headers)
        if extracted:
            return extracted
        fallback: list[str] = []
        for raw in (section_text or "").splitlines():
            s = raw.strip()
            if not s or s.startswith(("## ", "### ", "---")):
                continue
            cleaned = re.sub(r"\s+", " ", s.replace("**", "").replace("*", "")).strip()
            if cleaned:
                fallback.append(cleaned[:320])
            if len(fallback) >= lim:
                break
        return fallback

    def gate_rows(section_text: str, lim: int) -> list[str]:
        rows: list[str] = []
        for raw in (section_text or "").splitlines():
            s = raw.strip()
            if not (s.startswith("|") and s.endswith("|")):
                continue
            if re.search(r"\|\s*-+\s*\|", s):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 2:
                continue
            gate = cells[0]
            status = cells[1] if len(cells) > 1 else ""
            note = cells[2] if len(cells) > 2 else ""
            if gate.lower() in {"게이트", "gate"}:
                continue
            x = f"{gate} — {status}"
            if note:
                x += f": {note}"
            x = re.sub(r"\s+", " ", x.replace("**", "").replace("*", "")).strip()
            rows.append(x[:360])
        return rows[:lim]

    sections = parse_sections(decision_md)
    one_liner = find_section(sections, "한 줄 요약", "요약")
    consensus = hybrid_items(find_section(sections, "합의된 점", "consensus"), 10, skip_headers=("항목",))
    dissent = hybrid_items(find_section(sections, "미합의", "이견", "dissent"), 10, skip_headers=("항목",))
    actions = hybrid_items(find_section(sections, "권고 액션", "recommended actions", "즉시 수행 지시"), 10, skip_headers=("AR", "#"))
    gates = gate_rows(find_section(sections, "막힌 게이트", "blocked gates", "gates blocking"), 12)
    decision_requests = hybrid_items(
        find_section(sections, "ceo 결정 요청 사항", "대표님 결재 요청 사항", "결정 요청 사항", "결재 요청 사항"),
        8,
        skip_headers=("항목",),
    )

    blocks: list[dict] = []
    if one_liner:
        summary = re.sub(r"\s+", " ", one_liner).strip()
        blocks.append(_callout(f"핵심 요약: {summary[:350]}", emoji="🧭", color="blue_background"))

    blocks.append(_heading_2("합의된 핵심"))
    if consensus:
        blocks.extend([_bul(c) for c in consensus])
    else:
        blocks.append(_bul("합의된 핵심 항목이 추출되지 않았습니다."))

    blocks.append(_heading_2("미합의 / 이견"))
    if dissent:
        blocks.extend([_bul(d) for d in dissent])
    else:
        blocks.append(_bul("미합의 또는 반대 의견이 명시되지 않았습니다."))

    blocks.append(_heading_2("Action Items (미완료)"))
    if actions:
        blocks.extend([_todo(a, checked=False) for a in actions])
    else:
        blocks.append(_bul("권고 액션이 추출되지 않았습니다 (decision card 포맷 확인 필요)."))

    if decision_requests:
        blocks.append(_heading_2("대표 확인 필요 사항"))
        blocks.extend([_todo(item, checked=False) for item in decision_requests])

    blocks.append(_heading_2("Blocked Gates"))
    if gates:
        blocks.extend([_bul(g) for g in gates])
    else:
        blocks.append(_bul("막힌 게이트 항목이 없습니다(또는 추출 실패)."))

    if ts or correlation_id:
        blocks.append(_divider())
        meta_parts: list[str] = []
        if ts:
            meta_parts.append(f"기록 시각: {ts}")
        if correlation_id:
            meta_parts.append(f"correlation_id: {correlation_id}")
        blocks.append(_paragraph(" | ".join(meta_parts)))

    return blocks[: int(limit)]
