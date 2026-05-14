"""
T-09: 법률 사전 검토 — legal_review_approve gate

CLAUDE.md §5: 외부 발행 / 유료 제안 / 데이터 수집 정책 변경 전 필수.

검토 항목:
  1. 표시광고법    : 허위·과장 광고 표현
  2. 자본시장법    : 투자권유 유사 행위 (disclaimer 없는 종목 추천 등)
  3. 저작권법      : 출처 귀속, 공정이용 범위
  4. 개인정보보호법: PII 노출 여부
  5. 약관규제법    : 구독 조건 불공정 조항

경고: LLM 기반 1차 검토. 외부 변호사 자문을 대체하지 않음.
"""
import json
import os
from datetime import date
from pathlib import Path
from typing import Optional

from core.database import execute_query
from core.llm_orchestrator import LLMOrchestrator
from core.logger import HarnessLogger

_LEGAL_SYSTEM = """당신은 한국 법률 1차 검토 AI입니다.
다음 5개 법률 항목별로 콘텐츠를 검토하고 JSON으로 응답하세요.

검토 항목:
1. 표시광고법: 허위/과장 표현, 소비자 기만 가능성
2. 자본시장법: 투자권유 유사 행위, 종목명 + 매수/매도 권유, disclaimer 없는 수익률 주장
3. 저작권법: 인용된 콘텐츠의 출처 귀속, 공정이용 범위 초과 가능성
4. 개인정보보호법(PIPA): 이름, 이메일, 전화번호 등 개인식별정보 노출
5. 약관규제법: 구독 취소 제한, 불공정 면책조항

출력 JSON 스키마:
{
  "overall_result": "pass" | "block" | "warn",
  "findings": [
    {
      "law": "자본시장법",
      "severity": "block" | "warn" | "ok",
      "excerpt": "문제가 된 원문 발췌",
      "reason": "위반 또는 위험 이유",
      "mitigation": "수정 방향"
    }
  ],
  "disclaimer_required": true | false,
  "disclaimer_text": "이 콘텐츠는 투자 권유가 아닙니다...",
  "summary": "전체 검토 결론 1-2문장"
}

주의: 투자 종목 추천이나 수익 보장 주장이 있으면 반드시 block으로 표시하세요.
보고서 하단에 반드시 명시: "본 검토는 LLM 기반 1차 검토이며 외부 변호사 자문을 대체하지 않습니다."
"""

_GEMINI_CRITIQUE_PROMPT = """당신은 한국 법률 전문 비판적 검토자입니다.
아래 콘텐츠와 1차 법률 검토 결과를 독립적으로 재검토하세요.
1차 검토가 놓친 위험, 과소평가한 항목, 또는 지나치게 엄격한 판단을 지적하세요.

검토 대상 콘텐츠:
{content}

JSON으로만 응답:
{{
  "agreement_level": "agree" | "partial" | "disagree",
  "missed_risks": ["..."],
  "overblocked_items": ["..."],
  "final_recommendation": "pass" | "block" | "warn",
  "notes": "..."
}}
"""

_OUTPUT_DIR = Path("docs/reviews/legal")


def run_legal_review(
    content: str,
    target_type: str,
    target_id: Optional[int] = None,
    logger: Optional[HarnessLogger] = None,
) -> dict:
    """
    콘텐츠 법률 검토 수행.
    Returns: {result, findings, disclaimer_text, memo_path, approved}
    """
    orchestrator = LLMOrchestrator(logger)

    if logger:
        logger.info(f"[legal_review] 시작: target_type={target_type} id={target_id}")

    primary = orchestrator.claude_primary(
        system=_LEGAL_SYSTEM,
        user=f"검토 대상 콘텐츠:\n\n{content[:6000]}",
    )

    raw = primary["output"].replace("```json", "").replace("```", "").strip()
    try:
        primary_result = json.loads(raw)
    except json.JSONDecodeError:
        primary_result = {"overall_result": "warn", "summary": raw[:500], "findings": []}

    critique_prompt = _GEMINI_CRITIQUE_PROMPT.format(content=content[:3000])
    critique = orchestrator.gemini_critique(
        prompt=critique_prompt,
        primary_output=primary["output"],
    )

    critique_result = {}
    if critique.get("output"):
        try:
            c_raw = critique["output"].replace("```json", "").replace("```", "").strip()
            critique_result = json.loads(c_raw)
        except json.JSONDecodeError:
            critique_result = {"agreement_level": "partial", "notes": critique["output"][:200]}

    final_result = _reconcile(primary_result, critique_result)
    memo_path = _write_memo(content, target_type, target_id, primary_result, critique_result, final_result)
    approved = _record_decision(target_type, target_id, final_result, memo_path)

    if logger:
        logger.info(f"[legal_review] 완료: {final_result} memo={memo_path}")

    return {
        "result": final_result,
        "primary": primary_result,
        "critique": critique_result,
        "memo_path": str(memo_path),
        "approved": approved,
    }


def _reconcile(primary: dict, critique: dict) -> str:
    """Primary + Critique 결과 통합."""
    p = primary.get("overall_result", "warn")
    c_rec = critique.get("final_recommendation", "")

    if p == "block" or c_rec == "block":
        return "block"
    if p == "pass" and c_rec in ("pass", ""):
        return "pass"
    return "warn"


def _write_memo(
    content: str,
    target_type: str,
    target_id: Optional[int],
    primary: dict,
    critique: dict,
    final: str,
) -> Path:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    name = f"{target_type.upper()}-{target_id or 'NA'}-{today}.md"
    path = _OUTPUT_DIR / name

    findings_md = ""
    for f in primary.get("findings", []):
        sev = f.get("severity", "").upper()
        law = f.get("law", "")
        reason = f.get("reason", "")
        mitigation = f.get("mitigation", "")
        excerpt = f.get("excerpt", "")
        findings_md += f"\n#### [{sev}] {law}\n- 발췌: `{excerpt}`\n- 이유: {reason}\n- 수정: {mitigation}\n"

    disclaimer = primary.get("disclaimer_text", "")

    path.write_text(
        f"# 법률 사전 검토 메모\n\n"
        f"- **대상**: {target_type} / id={target_id}\n"
        f"- **날짜**: {today}\n"
        f"- **최종 결과**: **{final.upper()}**\n\n"
        f"## 1차 검토 (Claude)\n\n{primary.get('summary', '')}\n"
        f"{findings_md}\n"
        f"## 독립 검토 (Gemini)\n\n"
        f"- 일치도: {critique.get('agreement_level', 'N/A')}\n"
        f"- 놓친 위험: {critique.get('missed_risks', [])}\n"
        f"- 과차단 항목: {critique.get('overblocked_items', [])}\n"
        f"- 비고: {critique.get('notes', '')}\n\n"
        + (f"## Disclaimer 초안\n\n{disclaimer}\n\n" if disclaimer else "")
        + f"---\n> 본 검토는 LLM 기반 1차 검토이며 외부 변호사 자문을 대체하지 않습니다.\n",
        encoding="utf-8",
    )
    return path


def _record_decision(
    target_type: str,
    target_id: Optional[int],
    final_result: str,
    memo_path: Path,
) -> bool:
    approved = final_result in ("pass", "warn")
    approval_type = "legal_review_approve" if approved else "legal_review_block"
    execute_query(
        """INSERT INTO ceo_decisions
               (target_type, target_id, decision, approval_type, reason, decided_by)
           VALUES (%s, %s, %s, %s, %s, 'legal_review_agent')""",
        (
            target_type,
            target_id,
            final_result,
            approval_type,
            f"memo: {memo_path}",
        ),
    )
    return approved
