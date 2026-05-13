"""
Substack 뉴스레터 발행 모듈

인증: SUBSTACK_SESSION_TOKEN 환경변수 (브라우저 쿠키 substack.sid 값)
     Chrome → DevTools → Application → Cookies → substack.com → substack.sid
"""
import json
import os
import time
from pathlib import Path
import httpx
from dotenv import load_dotenv
from core.logger import HarnessLogger

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
MAX_RETRIES = 3


def _publication_url() -> str:
    return os.getenv("SUBSTACK_PUBLICATION_URL", "https://junti7.substack.com").rstrip("/")


def _session_token() -> str:
    return os.getenv("SUBSTACK_SESSION_TOKEN", "")


def _headers() -> dict:
    return {
        "Cookie": f"substack.sid={_session_token()}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"{_publication_url()}/publish/posts",
        "Origin": _publication_url(),
    }


def _base_url() -> str:
    return _publication_url()


def _draft_api_url(draft_id: int | str) -> str:
    return f"{_base_url()}/api/v1/drafts/{draft_id}"


def get_author_id(logger: HarnessLogger) -> int:
    """publication subscription 정보에서 user_id 반환"""
    r = httpx.get(f"{_base_url()}/api/v1/subscription", headers=_headers(), timeout=10)
    r.raise_for_status()
    user_id = r.json().get("user_id")
    if not user_id:
        raise ValueError("user_id를 가져올 수 없습니다. 세션 토큰을 확인하세요.")
    logger.info(f"Substack user_id: {user_id}")
    return user_id


def _pm_node_to_text(node: dict) -> str:
    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")

    content = node.get("content") or []
    child_text = "".join(_pm_node_to_text(child) for child in content)

    if node_type in {"paragraph", "heading", "blockquote"}:
        return child_text + "\n"
    if node_type == "horizontal_rule":
        return "\n---\n"
    if node_type == "bullet_list":
        lines: list[str] = []
        for item in content:
            item_text = _pm_node_to_text(item).strip()
            if item_text:
                lines.append(f"- {item_text}")
        return "\n".join(lines) + "\n"
    if node_type == "list_item":
        return child_text.strip()
    return child_text


def _draft_body_to_text(draft_body: str | dict) -> str:
    if isinstance(draft_body, str):
        try:
            draft_body = json.loads(draft_body)
        except json.JSONDecodeError:
            return draft_body

    if not isinstance(draft_body, dict):
        return str(draft_body)

    content = draft_body.get("content") or []
    text = "".join(_pm_node_to_text(node) for node in content)
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip())


def fetch_draft(draft_id: int | str, logger: HarnessLogger | None = None) -> dict:
    resp = httpx.get(_draft_api_url(draft_id), headers=_headers(), timeout=15.0)
    resp.raise_for_status()
    data = resp.json()
    if logger:
        logger.info(f"Substack draft 조회: id={draft_id}")
    return data


def fetch_draft_as_text(draft_id: int | str, logger: HarnessLogger | None = None) -> dict:
    data = fetch_draft(draft_id, logger=logger)
    title = data.get("draft_title") or data.get("search_engine_title") or "Untitled draft"
    subtitle = data.get("draft_subtitle") or data.get("description") or ""
    body_text = _draft_body_to_text(data.get("draft_body") or "")
    return {
        "draft_id": int(draft_id),
        "title": title,
        "subtitle": subtitle,
        "body_text": body_text,
        "status": data.get("type") or "draft",
        "slug": data.get("slug"),
        "audience": data.get("audience"),
    }


# ─── ProseMirror Doc 빌더 ─────────────────────────────────────────────────────

def _text(content: str, bold: bool = False) -> dict:
    node = {"type": "text", "text": content}
    if bold:
        node["marks"] = [{"type": "bold"}]
    return node


def _para(*texts) -> dict:
    return {"type": "paragraph", "content": list(texts)}


def _heading(text: str, level: int = 2) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(text)]}


def _hr() -> dict:
    return {"type": "horizontal_rule"}


def _bullet_list(items: list[str]) -> dict:
    return {
        "type": "bullet_list",
        "content": [
            {"type": "list_item", "content": [_para(_text(item))]}
            for item in items
        ],
    }


def _callout(text: str) -> dict:
    return {
        "type": "blockquote",
        "content": [_para(_text(text))],
    }


def _build_table(snapshot: dict) -> list[dict]:
    if not snapshot or not snapshot.get("rows"):
        return []
    nodes = [_heading(snapshot.get("label", "핵심 수치"), level=3)]
    for row in snapshot["rows"]:
        line = f"• {row.get('metric', '')}: {row.get('value', '')}  ({row.get('context', '')})"
        nodes.append(_para(_text(line)))
    return nodes


def _build_watchlist(watchlist: list) -> list[dict]:
    if not watchlist:
        return []
    nodes = [_heading("📡 다음 호까지 추적할 것들", level=3)]
    for w in watchlist:
        nodes.append(_para(
            _text(f"📌 {w.get('item', '')}", bold=True),
        ))
        nodes.append(_para(_text(f"이유: {w.get('reason', '')}")))
        nodes.append(_para(_text(f"트리거: {w.get('trigger', '')}")))
    return nodes


def _build_decision_block(block: dict) -> list[dict]:
    if not block:
        return []
    return [
        _heading("⚡ Action Summary", level=3),
        _para(_text("다음 주 주목: ", bold=True), _text(block.get("what_to_track", ""))),
        _para(_text("수혜 대상: ", bold=True), _text(block.get("who_benefits", ""))),
        _para(_text("리스크 노출: ", bold=True), _text(block.get("who_is_exposed", ""))),
    ]


def _build_deep_analysis(deep: dict) -> list[dict]:
    if not deep or not isinstance(deep, dict):
        return []
    nodes = []
    if deep.get("technical_breakdown"):
        nodes.append(_heading("🔬 기술 분석", level=3))
        nodes.append(_para(_text(deep["technical_breakdown"])))
    if deep.get("economic_implication"):
        nodes.append(_heading("💰 경제적 함의", level=3))
        nodes.append(_para(_text(deep["economic_implication"])))
    if deep.get("supply_chain_dynamics"):
        nodes.append(_heading("🏭 공급망 역학", level=3))
        nodes.append(_para(_text(deep["supply_chain_dynamics"])))
    return nodes


def _build_executive_decision(block: dict) -> list[dict]:
    if not block or not isinstance(block, dict):
        return []
    nodes = [_heading("⚡ Executive Decision", level=3)]
    if block.get("buy_signal"):
        nodes.append(_para(_text("매수 신호: ", bold=True), _text(block["buy_signal"])))
    if block.get("sell_signal"):
        nodes.append(_para(_text("매도 신호: ", bold=True), _text(block["sell_signal"])))
    if block.get("ceo_priority"):
        nodes.append(_para(_text("CEO 오늘 체크: ", bold=True), _text(block["ceo_priority"])))
    return nodes


def _build_watchlist_v2(watchlist: list) -> list[dict]:
    if not watchlist:
        return []
    nodes = [_heading("📡 추적 대상", level=3)]
    for w in watchlist:
        entity = w.get("entity") or w.get("item", "")
        relevance = w.get("relevance") or w.get("reason", "")
        signal = w.get("monitoring_signal") or w.get("trigger", "")
        nodes.append(_para(_text(f"📌 {entity}", bold=True)))
        if relevance:
            nodes.append(_para(_text(f"관련성: {relevance}")))
        if signal:
            nodes.append(_para(_text(f"트리거: {signal}")))
    return nodes


def signal_to_doc_nodes(signal: dict) -> list[dict]:
    """refined_output 1개를 ProseMirror 노드 리스트로 변환 (v10.0 + legacy 스키마 지원)"""
    nodes = []

    nodes.append(_heading(signal.get("final_title", ""), level=2))

    if signal.get("hook"):
        nodes.append(_callout(signal["hook"]))

    deep = signal.get("deep_analysis")
    if deep:
        nodes.extend(_build_deep_analysis(deep))
    else:
        if signal.get("what_happened"):
            nodes.append(_heading("무슨 일이 있었나", level=3))
            nodes.append(_para(_text(signal["what_happened"])))
        if signal.get("why_it_matters"):
            nodes.append(_heading("왜 중요한가", level=3))
            nodes.append(_para(_text(signal["why_it_matters"])))

    nodes.extend(_build_table(signal.get("quantitative_snapshot")))

    korea = signal.get("korea_strategic_context") or signal.get("korea_implication")
    if korea:
        nodes.append(_heading("🇰🇷 한국 전략적 맥락", level=3))
        nodes.append(_para(_text(korea)))

    risk = signal.get("risk_and_bottlenecks") or signal.get("risk_counterargument")
    if risk:
        nodes.append(_heading("⚠️ 리스크 및 병목", level=3))
        nodes.append(_para(_text(risk)))

    nodes.extend(_build_watchlist_v2(signal.get("watchlist", [])))

    exec_block = signal.get("executive_decision_block") or signal.get("decision_block")
    if exec_block and isinstance(exec_block, dict):
        if "buy_signal" in exec_block:
            nodes.extend(_build_executive_decision(exec_block))
        else:
            nodes.extend(_build_decision_block(exec_block))

    nodes.append(_hr())

    return nodes


def build_issue_doc(signals: list[dict], issue_number: int, issue_date: str) -> str:
    """여러 signal을 하나의 Substack doc JSON 문자열로 조립"""
    content = []

    # 헤더
    content.append(_para(
        _text(f"Physical AI Weekly #{issue_number:03d}  ·  {issue_date}", bold=True),
    ))
    content.append(_para(_text(
        f"Physical AI / AGI / 반도체 핵심 신호 {len(signals)}개 — 한국 독자를 위한 해석"
    )))
    content.append(_hr())

    # Signal 본문
    for s in signals:
        content.extend(signal_to_doc_nodes(s))

    # 푸터
    content.append(_para(_text("📬 이 뉴스레터가 유익했다면 주변에 공유해 주세요.")))
    content.append(_para(_text("피드백·질문은 reply로 보내주세요. 모두 읽습니다.")))

    doc = {
        "type": "doc",
        "attrs": {"schemaVersion": "v1"},
        "content": content,
    }
    return json.dumps(doc, ensure_ascii=False)


# ─── Substack API 호출 ────────────────────────────────────────────────────────

def create_draft(
    title: str,
    subtitle: str,
    body_doc: str,
    author_id: int,
    logger: HarnessLogger,
) -> dict:
    payload = {
        "draft_title": title,
        "draft_subtitle": subtitle,
        "draft_body": body_doc,
        "draft_bylines": [{"id": author_id, "is_lead_author": True, "guest_author_name": None}],
        "type": "newsletter",
        "draft_section_id": None,
        "section_chosen": False,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(
                f"{_base_url()}/api/v1/drafts",
                headers=_headers(),
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Substack draft 생성: id={data.get('id')}")
            return data
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"Draft 생성 재시도 {attempt+1}/{MAX_RETRIES}: {e} ({wait}s)")
                time.sleep(wait)
            else:
                raise


def publish_draft(draft_id: int, logger: HarnessLogger, send_email: bool = False) -> dict:
    payload = {
        "send_email": send_email,
        "for_free_trial_preview": False,
        "audience": "everyone",
    }
    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(
                f"{_base_url()}/api/v1/drafts/{draft_id}/publish",
                headers=_headers(),
                json=payload,
                timeout=15.0,
            )
            resp.raise_for_status()
            data = resp.json()
            url = data.get("canonical_url", "")
            logger.info(f"Substack 발행 완료: {url}")
            return data
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"Draft 발행 재시도 {attempt+1}/{MAX_RETRIES}: {e} ({wait}s)")
                time.sleep(wait)
            else:
                raise


def publish_weekly_issue(
    signals: list[dict],
    issue_number: int,
    issue_date: str,
    publish: bool = False,
    send_email: bool = False,
    correlation_id: str = None,
) -> dict:
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"=== Substack Weekly Issue #{issue_number:03d} 생성 시작 ===")

    if not _session_token():
        raise ValueError("SUBSTACK_SESSION_TOKEN 미설정")

    if not signals:
        logger.warning("발행할 signal이 없습니다.")
        return {}

    author_id = get_author_id(logger)

    title = f"Physical AI Weekly #{issue_number:03d} — {issue_date}"
    subtitle = f"이번 주 Physical AI / AGI / 반도체 핵심 신호 {len(signals)}개 분석"
    body_doc = build_issue_doc(signals, issue_number, issue_date)

    draft = create_draft(title, subtitle, body_doc, author_id, logger)
    draft_id = draft.get("id")
    draft_url = f"{_base_url()}/p/{draft.get('slug', '')}" if draft.get("slug") else f"{_base_url()}/publish/post/{draft_id}"

    if not publish:
        logger.info(f"Draft 생성 완료 (미발행): {draft_url}")
        return {"draft_id": draft_id, "status": "draft", "url": draft_url}

    result = publish_draft(draft_id, logger, send_email=send_email)
    url = result.get("canonical_url", draft_url)
    logger.info(f"=== Substack 발행 완료: {url} ===")
    return {"draft_id": draft_id, "status": "published", "url": url}
