"""
QA Agent — qa_clear gate before customer-facing publish.

Checks:
  1. schema_valid   : required JSON fields present and non-empty
  2. completeness   : sections meet minimum length thresholds
  3. investment_risk: flags prohibited investment-advice language (자본시장법)
  4. llm_review     : Claude Haiku checks Korean fluency + factual coherence
                      (skipped if daily cost limit reached)

Target types:
  qa_review / refined_output   : single signal analysis (final_body JSON)
  qa_review / newsletter_issue : assembled weekly issue (all source signals)
"""

import json
import os
import re
from datetime import date, datetime
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from core.approval import validate_approval
from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.refiner import log_api_cost, get_today_cost

load_dotenv()

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "1.00"))

# ─── Rubric constants ─────────────────────────────────────────────────────────

REQUIRED_FIELDS = [
    "final_title", "hook", "deep_analysis",
    "korea_strategic_context", "risk_and_bottlenecks",
    "watchlist", "executive_decision_block", "tags",
]
REQUIRED_DEEP_FIELDS = ["technical_breakdown", "economic_implication"]

MIN_CHARS = {
    "hook": 80,
    "korea_strategic_context": 150,
    "risk_and_bottlenecks": 80,
    "technical_breakdown": 200,
    "economic_implication": 200,
}

INVESTMENT_RISK_PATTERNS = [
    r"(무조건|반드시|확실히)\s*(오릅니다|오를|수익이 납니다)",
    r"(투자|매수|매도)\s*(추천|권유|권고)\s*합니다",
    r"원금\s*보장",
]

LLM_QA_PROMPT = """당신은 한국어 콘텐츠 품질 검사관입니다.
아래 Physical AI 분석 리포트를 읽고 다음 항목을 평가하세요.

1. korean_fluency (true/false): 문장이 자연스러운 한국어인가? 어색하거나 번역투 문장이 없는가?
2. coherence (true/false): 섹션 간 내용이 일관성 있는가? 앞뒤가 맞지 않는 주장이 없는가?
3. factual_risk (true/false): 출처 없는 단정적 수치 또는 투자 권유에 해당하는 표현이 있는가?
4. issues: 발견된 문제점 목록 (없으면 빈 배열)

반드시 JSON으로만 응답:
{"korean_fluency": true, "coherence": true, "factual_risk": false, "issues": []}

리포트:
"""


# ─── Individual checks ────────────────────────────────────────────────────────

def _check_schema(body: dict) -> list[str]:
    findings = []
    for f in REQUIRED_FIELDS:
        if not body.get(f):
            findings.append(f"필수 필드 누락 또는 비어있음: {f}")
    deep = body.get("deep_analysis") or {}
    if isinstance(deep, dict):
        for f in REQUIRED_DEEP_FIELDS:
            if not deep.get(f):
                findings.append(f"deep_analysis 하위 필드 누락: {f}")
    else:
        findings.append("deep_analysis가 dict 형태가 아님")
    return findings


def _check_completeness(body: dict) -> list[str]:
    findings = []
    deep = body.get("deep_analysis") or {}
    if not isinstance(deep, dict):
        deep = {}
    checks = {
        "hook": body.get("hook") or "",
        "korea_strategic_context": body.get("korea_strategic_context") or "",
        "risk_and_bottlenecks": body.get("risk_and_bottlenecks") or "",
        "technical_breakdown": deep.get("technical_breakdown") or "",
        "economic_implication": deep.get("economic_implication") or "",
    }
    for field, text in checks.items():
        min_len = MIN_CHARS[field]
        if len(text) < min_len:
            findings.append(f"{field} 내용 불충분: {len(text)}자 (최소 {min_len}자)")
    return findings


def _check_investment_risk(body: dict) -> list[str]:
    text = json.dumps(body, ensure_ascii=False)
    findings = []
    for pattern in INVESTMENT_RISK_PATTERNS:
        m = re.search(pattern, text)
        if m:
            findings.append(f"투자 권유 위험 표현 감지: '{m.group()}'")
    return findings


def _check_llm(body: dict, logger: HarnessLogger) -> list[str]:
    today_cost = get_today_cost(logger)
    if today_cost >= DAILY_COST_LIMIT * 0.9:
        logger.warning(f"QA LLM 검사 스킵 — 일일 비용 한도 90% 도달 (${today_cost:.3f})")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY 미설정 — LLM QA 스킵")
        return []

    excerpt = json.dumps({
        "final_title": body.get("final_title", ""),
        "hook": (body.get("hook") or "")[:500],
        "korea_strategic_context": (body.get("korea_strategic_context") or "")[:500],
        "risk_and_bottlenecks": (body.get("risk_and_bottlenecks") or "")[:300],
    }, ensure_ascii=False)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": LLM_QA_PROMPT + excerpt}],
        )
        log_api_cost("claude-haiku-4-5", resp.usage.input_tokens, resp.usage.output_tokens)
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"LLM QA 호출 실패 (비치명적): {e}")
        return []

    findings = []
    if not result.get("korean_fluency"):
        findings.append("LLM: 한국어 유창성 문제 감지")
    if not result.get("coherence"):
        findings.append("LLM: 섹션 간 일관성 문제 감지")
    if result.get("factual_risk"):
        findings.append("LLM: 팩트 리스크 또는 투자 권유 의심 표현")
    findings.extend(result.get("issues") or [])
    return findings


# ─── Core runner ─────────────────────────────────────────────────────────────

def _run_checks(body: dict, logger: HarnessLogger) -> tuple[bool, list[str]]:
    findings = []
    findings.extend(_check_schema(body))
    findings.extend(_check_completeness(body))
    findings.extend(_check_investment_risk(body))
    findings.extend(_check_llm(body, logger))
    return len(findings) == 0, findings


def _record_decision(target_id: int, approved: bool, reason: str):
    validate_approval("qa_review", "qa_clear")
    decision = "approved" if approved else "rejected"
    execute_query("""
        INSERT INTO ceo_decisions
            (target_type, target_id, decision, approval_type, reason, decided_by)
        VALUES ('qa_review', %s, %s, 'qa_clear', %s, 'QA_Agent')
        ON CONFLICT (target_type, target_id, decision)
        DO UPDATE SET reason = EXCLUDED.reason, created_at = NOW()
    """, (target_id, decision, reason[:1000]))


def _save_memo(target_id: int, target_label: str, approved: bool,
               findings: list[str], title: str) -> str:
    today = date.today().isoformat()
    memo_dir = Path(__file__).resolve().parents[2] / "docs/reports/qa"
    memo_dir.mkdir(parents=True, exist_ok=True)
    memo_path = memo_dir / f"{target_label.upper()}-{target_id}-{today}.md"

    verdict = "APPROVED" if approved else "REJECTED"
    lines = [
        f"# QA Review — {title}",
        f"",
        f"| 항목 | 값 |",
        f"|---|---|",
        f"| target | {target_label}#{target_id} |",
        f"| date | {today} |",
        f"| verdict | {'✅ ' if approved else '❌ '}{verdict} |",
        f"| reviewer | QA Agent (claude-haiku-4-5) |",
        f"| findings | {len(findings)}건 |",
        f"",
        f"## Findings",
        "",
    ]
    if findings:
        lines += [f"- {f}" for f in findings]
    else:
        lines.append("- 발견된 문제 없음 — 모든 검사 통과")
    lines += [
        "",
        "---",
        f"*Generated by adapters/content/qa_agent.py at {datetime.now().isoformat()}*",
    ]
    memo_path.write_text("\n".join(lines), encoding="utf-8")
    return str(memo_path)


# ─── Public API ──────────────────────────────────────────────────────────────

def qa_check_refined_output(refined_output_id: int,
                             correlation_id: str = None) -> bool:
    """refined_output 1건 QA. 결과를 ceo_decisions에 기록하고 bool 반환."""
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"[QA] refined_output id={refined_output_id} 검사 시작")

    row = execute_query(
        "SELECT id, final_title, final_body FROM refined_outputs WHERE id = %s",
        (refined_output_id,), fetch=True,
    )
    if not row:
        logger.error(f"[QA] refined_output {refined_output_id} 없음")
        return False

    row = dict(row[0])
    title = row.get("final_title") or f"refined_output#{refined_output_id}"
    raw_body = row.get("final_body") or "{}"
    try:
        body = raw_body if isinstance(raw_body, dict) else json.loads(raw_body)
    except json.JSONDecodeError as e:
        _record_decision(refined_output_id, False, f"JSON 파싱 실패: {e}")
        logger.error(f"[QA] final_body JSON 파싱 실패: {e}")
        return False

    approved, findings = _run_checks(body, logger)
    reason = "; ".join(findings) if findings else "모든 검사 통과"
    memo_path = _save_memo(refined_output_id, "refined_output", approved, findings, title)
    _record_decision(refined_output_id, approved, reason)

    verdict = "✅ APPROVED" if approved else f"❌ REJECTED ({len(findings)}건)"
    logger.info(f"[QA] {verdict} — memo={memo_path}")
    return approved


def qa_check_newsletter_issue(issue_id: int,
                               correlation_id: str = None) -> bool:
    """newsletter_issue의 모든 구성 signal에 대해 QA를 실행."""
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"[QA] newsletter_issue id={issue_id} 검사 시작")

    issue = execute_query(
        "SELECT id, title, source_signal_ids FROM newsletter_issues WHERE id = %s",
        (issue_id,), fetch=True,
    )
    if not issue:
        logger.error(f"[QA] newsletter_issue {issue_id} 없음")
        return False

    issue = dict(issue[0])
    raw_ids = issue.get("source_signal_ids") or "[]"
    signal_ids = raw_ids if isinstance(raw_ids, list) else json.loads(raw_ids)

    if not signal_ids:
        reason = "source_signal_ids 비어있음"
        _record_decision(issue_id, False, reason)
        logger.error(f"[QA] {reason}")
        return False

    all_findings = []
    for sid in signal_ids:
        row = execute_query(
            "SELECT final_title, final_body FROM refined_outputs WHERE id = %s",
            (sid,), fetch=True,
        )
        if not row:
            all_findings.append(f"signal id={sid}: refined_output 없음")
            continue
        row = dict(row[0])
        raw_body = row.get("final_body") or "{}"
        try:
            body = raw_body if isinstance(raw_body, dict) else json.loads(raw_body)
        except json.JSONDecodeError:
            all_findings.append(f"signal id={sid}: JSON 파싱 실패")
            continue

        label = (row.get("final_title") or f"signal#{sid}")[:35]
        for f in _check_schema(body) + _check_completeness(body) + _check_investment_risk(body):
            all_findings.append(f"[{label}] {f}")

    # LLM 검사는 첫 번째 signal로 대표 수행 (비용 절감)
    first_row = execute_query(
        "SELECT final_body FROM refined_outputs WHERE id = %s",
        (signal_ids[0],), fetch=True,
    )
    if first_row:
        try:
            first_body = dict(first_row[0]).get("final_body") or "{}"
            first_body = first_body if isinstance(first_body, dict) else json.loads(first_body)
            all_findings.extend(_check_llm(first_body, logger))
        except Exception:
            pass

    approved = len(all_findings) == 0
    reason = "; ".join(all_findings) if all_findings else "모든 검사 통과"
    title = issue.get("title") or f"newsletter_issue#{issue_id}"
    memo_path = _save_memo(issue_id, "newsletter_issue", approved, all_findings, title)
    _record_decision(issue_id, approved, reason)

    verdict = "✅ APPROVED" if approved else f"❌ REJECTED ({len(all_findings)}건)"
    logger.info(f"[QA] {verdict} — memo={memo_path}")
    return approved


def has_qa_clear(target_id: int) -> bool:
    """qa_review 대상에 대한 qa_clear approved 여부 확인."""
    result = execute_query("""
        SELECT decision FROM ceo_decisions
        WHERE target_type = 'qa_review'
          AND target_id = %s
          AND approval_type = 'qa_clear'
        ORDER BY created_at DESC LIMIT 1
    """, (target_id,), fetch=True)
    return bool(result and result[0]["decision"] == "approved")
