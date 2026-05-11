"""
Substack 뉴스레터 발행 모듈

인증: SUBSTACK_SESSION_TOKEN 환경변수 (브라우저 쿠키 substack.sid 값)
     Chrome → DevTools → Application → Cookies → substack.com → substack.sid
"""
import json
import os
import time
import httpx
from dotenv import load_dotenv
from core.logger import HarnessLogger

load_dotenv()

SUBSTACK_PUBLICATION_URL = os.getenv("SUBSTACK_PUBLICATION_URL", "https://junti7.substack.com")
SUBSTACK_SESSION_TOKEN = os.getenv("SUBSTACK_SESSION_TOKEN", "")
MAX_RETRIES = 3


def _headers() -> dict:
    return {
        "Cookie": f"substack.sid={SUBSTACK_SESSION_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": f"{SUBSTACK_PUBLICATION_URL.rstrip('/')}/publish/posts",
        "Origin": SUBSTACK_PUBLICATION_URL.rstrip("/"),
    }


def _base_url() -> str:
    return SUBSTACK_PUBLICATION_URL.rstrip("/")


def get_author_id(logger: HarnessLogger) -> int:
    """publication subscription 정보에서 user_id 반환"""
    r = httpx.get(f"{_base_url()}/api/v1/subscription", headers=_headers(), timeout=10)
    r.raise_for_status()
    user_id = r.json().get("user_id")
    if not user_id:
        raise ValueError("user_id를 가져올 수 없습니다. 세션 토큰을 확인하세요.")
    logger.info(f"Substack user_id: {user_id}")
    return user_id


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


def signal_to_doc_nodes(signal: dict) -> list[dict]:
    """refined_output 1개를 ProseMirror 노드 리스트로 변환"""
    nodes = []

    nodes.append(_heading(signal.get("final_title", ""), level=2))

    if signal.get("hook"):
        nodes.append(_callout(signal["hook"]))

    if signal.get("what_happened"):
        nodes.append(_heading("무슨 일이 있었나", level=3))
        nodes.append(_para(_text(signal["what_happened"])))

    if signal.get("why_it_matters"):
        nodes.append(_heading("왜 중요한가", level=3))
        nodes.append(_para(_text(signal["why_it_matters"])))

    nodes.extend(_build_table(signal.get("quantitative_snapshot")))

    if signal.get("korea_implication"):
        nodes.append(_heading("🇰🇷 한국 독자 함의", level=3))
        nodes.append(_para(_text(signal["korea_implication"])))

    if signal.get("risk_counterargument"):
        nodes.append(_heading("⚠️ 리스크 / 반론", level=3))
        nodes.append(_para(_text(signal["risk_counterargument"])))

    nodes.extend(_build_watchlist(signal.get("watchlist", [])))
    nodes.extend(_build_decision_block(signal.get("decision_block")))
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

    if not SUBSTACK_SESSION_TOKEN:
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
