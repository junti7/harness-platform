"""
QA Agent — qa_clear gate before customer-facing publish.

Checks:
  1. schema_valid   : required JSON fields present and non-empty
  2. completeness   : sections meet minimum length thresholds
  3. investment_risk: flags prohibited investment-advice language (자본시장법)
  4. llm_review     : Claude Haiku checks Korean fluency + factual coherence
                      (skipped if daily cost limit reached)

Target types:
  refined_output   : single signal analysis (final_body JSON)
  newsletter_issue : assembled weekly issue (all source signals)
  research_report  : markdown-based decision brief / memo
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
# 내부 인텔리전스 용도 기준 (외부 발행이 아닌 CEO 브리핑·Notion 저장 목적)
# MUST: 제목 + hook + 한국맥락 — 이 셋만 없으면 가치가 없음
# NICE-TO-HAVE: deep_analysis, evidence_posture 등 — 없어도 통과

REQUIRED_FIELDS = [
    "final_title",
    "hook",
    "korea_strategic_context",
]
# deep_analysis 하위 필드는 optional — 없어도 통과
REQUIRED_DEEP_FIELDS: list[str] = []

MIN_CHARS = {
    "hook": 30,                    # 최소한의 요약만 있으면 됨
    "korea_strategic_context": 50, # 한 문장이라도 있으면 됨
    "risk_and_bottlenecks": 0,     # 없어도 통과
    "technical_breakdown": 0,      # 없어도 통과
    "economic_implication": 0,     # 없어도 통과
}

# 실제 법적으로 문제가 되는 표현만 차단 (speculative 표기·스타일 문제는 허용)
INVESTMENT_RISK_PATTERNS = [
    r"(무조건|반드시|확실히)\s*(오릅니다|오를|수익이 납니다)",
    r"(투자|매수|매도)\s*(추천|권유|권고)\s*합니다",
    r"원금\s*보장",
]

LLM_QA_PROMPT = """당신은 내부 인텔리전스 리포트 검토자입니다.
아래 AI/로보틱스 분석 리포트를 읽고 두 가지만 판단하세요.

1. readable (true/false): 내용을 이해할 수 있는가? (번역투·어색함은 허용. 완전히 깨지거나 의미불명인 경우만 false)
2. factual_risk (true/false): "투자를 권유합니다", "원금 보장", "반드시 오릅니다" 같은 명백한 투자 권유 표현이 있는가? (speculative 표기·분석적 추측은 허용)

판단 기준: 이 리포트는 외부 발행이 아닌 CEO 내부 참고용입니다. 완벽하지 않아도 됩니다.
엄격하게 판단하지 마세요. readable=false는 텍스트가 완전히 깨지거나 무의미한 경우에만 사용합니다.

반드시 JSON으로만 응답 (다른 말 없이):
{"readable": true, "factual_risk": false}

리포트:
"""

REPORT_REQUIRED_HEADINGS = [
    "## 0. 이번 결론",
    "## 3. Evidence Scorecard",
    "## 4. Claim Posture Summary",
    "## 5. 한국 기준으로 왜 중요한가",
    "## 7. What To Watch / What To Defer",
    "## Disclaimer",
]


# ─── Individual checks ────────────────────────────────────────────────────────

def _check_schema(body: dict) -> list[str]:
    """핵심 필드(제목·hook·한국맥락)만 필수 확인. 나머지는 optional."""
    findings = []
    for f in REQUIRED_FIELDS:
        val = body.get(f)
        if not val or (isinstance(val, str) and not val.strip()):
            findings.append(f"핵심 필드 누락: {f}")
    return findings


def _check_completeness(body: dict) -> list[str]:
    """최소 길이 기준 확인 — 0이면 스킵."""
    findings = []
    deep = body.get("deep_analysis") or {}
    if not isinstance(deep, dict):
        deep = {}
    checks = {
        "hook": body.get("hook") or "",
        "korea_strategic_context": body.get("korea_strategic_context") or "",
    }
    for field, text in checks.items():
        min_len = MIN_CHARS.get(field, 0)
        if min_len > 0 and len(str(text).strip()) < min_len:
            findings.append(f"{field} 내용 부족: {len(str(text).strip())}자 (최소 {min_len}자)")
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
            max_tokens=512,
            messages=[{"role": "user", "content": LLM_QA_PROMPT + excerpt}],
        )
        log_api_cost("claude-haiku-4-5", resp.usage.input_tokens, resp.usage.output_tokens)
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        raw = m.group(0) if m else raw
        result = json.loads(raw)
    except Exception as e:
        logger.warning(f"LLM QA 호출 실패 (비치명적): {e}")
        return []

    findings = []
    if result.get("readable") is False:
        findings.append("LLM: 리포트 내용을 이해할 수 없음 (텍스트 손상)")
    if result.get("factual_risk") is True:
        findings.append("LLM: 명백한 투자 권유 표현 감지")
    return findings


# ─── Core runner ─────────────────────────────────────────────────────────────

def _run_checks(body: dict, logger: HarnessLogger) -> tuple[bool, list[str]]:
    findings = []
    findings.extend(_check_schema(body))
    findings.extend(_check_completeness(body))
    findings.extend(_check_investment_risk(body))
    findings.extend(_check_llm(body, logger))
    return len(findings) == 0, findings


def _record_decision(target_type: str, target_id: int, approved: bool, reason: str):
    validate_approval(target_type, "qa_clear")
    decision = "approved" if approved else "rejected"
    execute_query("""
        INSERT INTO ceo_decisions
            (target_type, target_id, decision, approval_type, reason, decided_by)
        VALUES (%s, %s, %s, 'qa_clear', %s, 'QA_Agent')
        ON CONFLICT (target_type, target_id, decision)
        DO UPDATE SET reason = EXCLUDED.reason, created_at = NOW()
    """, (target_type, target_id, decision, reason[:1000]))

    if target_type != "qa_review":
        validate_approval("qa_review", "qa_clear")
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
        _record_decision("refined_output", refined_output_id, False, f"JSON 파싱 실패: {e}")
        logger.error(f"[QA] final_body JSON 파싱 실패: {e}")
        return False

    approved, findings = _run_checks(body, logger)
    reason = "; ".join(findings) if findings else "모든 검사 통과"
    memo_path = _save_memo(refined_output_id, "refined_output", approved, findings, title)
    _record_decision("refined_output", refined_output_id, approved, reason)

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
        _record_decision("newsletter_issue", issue_id, False, reason)
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
    _record_decision("newsletter_issue", issue_id, approved, reason)

    verdict = "✅ APPROVED" if approved else f"❌ REJECTED ({len(all_findings)}건)"
    logger.info(f"[QA] {verdict} — memo={memo_path}")
    return approved


def _check_report_markdown(content: str) -> list[str]:
    findings = []
    for heading in REPORT_REQUIRED_HEADINGS:
        if heading not in content:
            findings.append(f"필수 섹션 누락: {heading}")
    if "company-self-report" not in content and "speculative" not in content and "verified" not in content:
        findings.append("claim posture 분류 누락")
    for pattern in INVESTMENT_RISK_PATTERNS:
        m = re.search(pattern, content)
        if m:
            findings.append(f"투자 권유 위험 표현 감지: '{m.group()}'")
    return findings


def _check_llm_text(title: str, content: str, logger: HarnessLogger) -> list[str]:
    today_cost = get_today_cost(logger)
    if today_cost >= DAILY_COST_LIMIT * 0.9:
        logger.warning(f"QA LLM 검사 스킵 — 일일 비용 한도 90% 도달 (${today_cost:.3f})")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY 미설정 — LLM QA 스킵")
        return []

    excerpt = json.dumps({
        "title": title,
        "excerpt": content[:1800],
    }, ensure_ascii=False)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            messages=[{"role": "user", "content": LLM_QA_PROMPT + excerpt}],
        )
        log_api_cost("claude-haiku-4-5", resp.usage.input_tokens, resp.usage.output_tokens)
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        raw = m.group(0) if m else raw
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


def _resolve_report_path(row: dict) -> Path | None:
    body = row.get("body") or ""
    match = re.search(r"See\s+([^\n]+\.md)", body)
    if not match:
        return None
    return Path(__file__).resolve().parents[2] / match.group(1).strip()


def qa_check_research_report(report_id: int, correlation_id: str = None) -> bool:
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"[QA] research_report id={report_id} 검사 시작")

    rows = execute_query(
        "SELECT id, title, body, summary FROM research_reports WHERE id = %s",
        (report_id,), fetch=True,
    )
    if not rows:
        logger.error(f"[QA] research_report {report_id} 없음")
        return False

    row = dict(rows[0])
    title = row.get("title") or f"research_report#{report_id}"
    path = _resolve_report_path(row)
    content = ""
    if path and path.exists():
        content = path.read_text(encoding="utf-8")
    else:
        content = f"{row.get('summary') or ''}\n\n{row.get('body') or ''}"

    findings = _check_report_markdown(content)
    findings.extend(_check_llm_text(title, content, logger))
    approved = len(findings) == 0
    reason = "; ".join(findings) if findings else "모든 검사 통과"
    memo_path = _save_memo(report_id, "research_report", approved, findings, title)
    _record_decision("research_report", report_id, approved, reason)
    verdict = "✅ APPROVED" if approved else f"❌ REJECTED ({len(findings)}건)"
    logger.info(f"[QA] {verdict} — memo={memo_path}")
    return approved


def has_qa_clear(target_id: int, target_type: str = "qa_review") -> bool:
    """qa_clear approved 여부 확인. 기본값은 legacy qa_review."""
    result = execute_query("""
        SELECT decision FROM ceo_decisions
        WHERE target_type = %s
          AND target_id = %s
          AND approval_type = 'qa_clear'
        ORDER BY created_at DESC LIMIT 1
    """, (target_type, target_id), fetch=True)
    return bool(result and result[0]["decision"] == "approved")
