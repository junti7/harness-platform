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
        "Referer": SUBSTACK_PUBLICATION_URL,
        "Origin": SUBSTACK_PUBLICATION_URL,
    }


def _base_url() -> str:
    return SUBSTACK_PUBLICATION_URL.rstrip("/")


# ─── HTML 포맷터 ───────────────────────────────────────────────────────────────

def _render_table(snapshot: dict) -> str:
    if not snapshot or not snapshot.get("rows"):
        return ""
    label = snapshot.get("label", "핵심 수치")
    rows_html = "".join(
        f"<tr><td><strong>{r.get('metric','')}</strong></td>"
        f"<td>{r.get('value','')}</td>"
        f"<td style='color:#6b7280;font-size:0.9em'>{r.get('context','')}</td></tr>"
        for r in snapshot["rows"]
    )
    return f"""
<div style="margin:24px 0">
  <p style="font-weight:600;color:#4b5563;font-size:0.875rem;text-transform:uppercase;letter-spacing:0.05em">{label}</p>
  <table style="width:100%;border-collapse:collapse;font-size:0.95em">
    <thead>
      <tr style="border-bottom:2px solid #e5e7eb">
        <th style="text-align:left;padding:8px 4px;color:#111827">지표</th>
        <th style="text-align:left;padding:8px 4px;color:#111827">수치</th>
        <th style="text-align:left;padding:8px 4px;color:#111827">맥락</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>"""


def _render_watchlist(watchlist: list) -> str:
    if not watchlist:
        return ""
    items_html = "".join(
        f"<li style='margin-bottom:12px'>"
        f"<strong>📌 {w.get('item','')}</strong><br>"
        f"<span style='color:#4b5563'>{w.get('reason','')}</span><br>"
        f"<span style='color:#2563eb;font-size:0.9em'>트리거: {w.get('trigger','')}</span>"
        f"</li>"
        for w in watchlist
    )
    return f"""
<div style="background:#eff6ff;border-left:4px solid #2563eb;padding:16px;margin:24px 0;border-radius:4px">
  <p style="font-weight:700;color:#1d4ed8;margin:0 0 12px">📡 다음 호까지 추적할 것들</p>
  <ul style="margin:0;padding-left:20px">{items_html}</ul>
</div>"""


def _render_decision_block(block: dict) -> str:
    if not block:
        return ""
    return f"""
<div style="background:#f9fafb;border:1px solid #e5e7eb;padding:16px;margin:24px 0;border-radius:8px">
  <p style="font-weight:700;color:#111827;margin:0 0 12px">⚡ 이번 호 Action Summary</p>
  <p><strong>다음 주 주목:</strong> {block.get('what_to_track','')}</p>
  <p><strong>수혜 대상:</strong> {block.get('who_benefits','')}</p>
  <p><strong>리스크 노출:</strong> {block.get('who_is_exposed','')}</p>
</div>"""


def signal_to_html(signal: dict, issue_number: int = 1) -> str:
    """refined_output 구조화 JSON 1개를 Substack HTML 섹션으로 변환"""
    return f"""
<h2 style="color:#111827;border-bottom:2px solid #2563eb;padding-bottom:8px">{signal.get('final_title','')}</h2>

<p style="font-size:1.05em;color:#374151;font-style:italic;border-left:3px solid #2563eb;padding-left:12px;margin:16px 0">
  {signal.get('hook','')}
</p>

<h3 style="color:#374151">무슨 일이 있었나</h3>
<p>{signal.get('what_happened','')}</p>

<h3 style="color:#374151">왜 중요한가</h3>
<p>{signal.get('why_it_matters','')}</p>

{_render_table(signal.get('quantitative_snapshot'))}

<h3 style="color:#374151">🇰🇷 한국 독자 함의</h3>
<p style="background:#f0fdf4;border-left:4px solid #059669;padding:12px;border-radius:4px">
  {signal.get('korea_implication','')}
</p>

<h3 style="color:#374151">⚠️ 리스크 / 반론</h3>
<p style="color:#6b7280">{signal.get('risk_counterargument','')}</p>

{_render_watchlist(signal.get('watchlist', []))}
{_render_decision_block(signal.get('decision_block'))}

<hr style="border:none;border-top:1px solid #e5e7eb;margin:32px 0">
"""


def build_issue_html(signals: list[dict], issue_number: int, issue_date: str) -> str:
    """여러 signal을 하나의 Weekly Issue HTML로 조립"""
    header = f"""
<div style="text-align:center;padding:24px 0;border-bottom:2px solid #111827;margin-bottom:32px">
  <p style="color:#4b5563;font-size:0.875rem;text-transform:uppercase;letter-spacing:0.1em">
    Physical AI Weekly #{issue_number:03d} · {issue_date}
  </p>
  <p style="color:#6b7280;font-size:0.875rem;margin-top:8px">
    Physical AI / AGI / 반도체 핵심 신호 — 한국 독자를 위한 해석
  </p>
</div>
"""
    signals_html = "".join(
        signal_to_html(s, issue_number) for s in signals
    )
    footer = """
<div style="text-align:center;padding:24px 0;margin-top:32px;border-top:2px solid #e5e7eb;color:#6b7280;font-size:0.875rem">
  <p>📬 이 뉴스레터가 유익했다면 주변에 공유해 주세요.</p>
  <p>피드백·질문은 reply로 보내주세요. 모두 읽습니다.</p>
</div>
"""
    return header + signals_html + footer


# ─── Substack API 호출 ────────────────────────────────────────────────────────

def create_draft(title: str, subtitle: str, body_html: str, logger: HarnessLogger) -> dict:
    """Substack에 draft 생성. draft_id와 draft 정보를 반환."""
    if not SUBSTACK_SESSION_TOKEN:
        raise ValueError("SUBSTACK_SESSION_TOKEN이 설정되지 않았습니다. .env를 확인하세요.")

    payload = {
        "draft_title": title,
        "draft_subtitle": subtitle,
        "draft_body": body_html,
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
            logger.info(f"Substack draft 생성: id={data.get('id')}, title={title[:40]}")
            return data
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"Draft 생성 재시도 {attempt+1}/{MAX_RETRIES}: {e} ({wait}s)")
                time.sleep(wait)
            else:
                raise


def publish_draft(draft_id: int, logger: HarnessLogger, send_email: bool = False) -> dict:
    """Draft를 Substack에 발행. send_email=True면 구독자에게 이메일 발송."""
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
            logger.info(f"Substack 발행 완료: draft_id={draft_id}, url={data.get('canonical_url','')}")
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
    """
    signals 리스트로 Weekly Issue를 생성하고 Substack에 draft(또는 publish) 처리.

    Args:
        signals: refined_output 구조화 JSON 리스트
        issue_number: 발행 번호
        issue_date: 발행일 (YYYY-MM-DD)
        publish: True이면 draft→publish까지 진행, False이면 draft 생성만
        send_email: True이면 구독자 이메일 발송 (publish=True일 때만 적용)

    Returns:
        {"draft_id": ..., "url": ..., "status": "draft"|"published"}
    """
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"=== Substack Weekly Issue #{issue_number:03d} 생성 시작 ===")

    if not signals:
        logger.warning("발행할 signal이 없습니다.")
        return {}

    title = f"Physical AI Weekly #{issue_number:03d} — {issue_date}"
    subtitle = f"이번 주 Physical AI / AGI / 반도체 핵심 신호 {len(signals)}개 분석"
    body_html = build_issue_html(signals, issue_number, issue_date)

    draft = create_draft(title, subtitle, body_html, logger)
    draft_id = draft.get("id")

    if not publish:
        logger.info(f"Draft 생성 완료 (미발행): {_base_url()}/p/{draft.get('slug','')}")
        return {"draft_id": draft_id, "status": "draft", "url": f"{_base_url()}/p/{draft.get('slug','')}"}

    result = publish_draft(draft_id, logger, send_email=send_email)
    url = result.get("canonical_url", "")
    logger.info(f"=== Substack 발행 완료: {url} ===")
    return {"draft_id": draft_id, "status": "published", "url": url}
