"""
T-10: Pre-Mortem 자동화

CLAUDE.md §5: high-impact 의사결정 전 Pre-Mortem 필수.
docs/governance/PRE_MORTEM_PROTOCOL.md 템플릿 준수.

대상: paid_offer, capital_action, language_launch, external_publish
"""
import json
from datetime import date
from pathlib import Path
from typing import Optional

from core.database import execute_query
from core.llm_orchestrator import LLMOrchestrator
from core.logger import HarnessLogger

_SYSTEM = """당신은 사업 위험 분석가입니다.
주어진 의사결정에 대해 Pre-Mortem 분석을 작성하세요.
"이 결정이 완전히 실패했다"고 가정하고, 왜 실패했는지를 역방향으로 분석합니다.

반드시 JSON으로만 응답하세요:
{
  "decision_target": "...",
  "decision_date": "YYYY-MM-DD",
  "scenarios": [
    {
      "scenario": "실패 시나리오 제목",
      "probability": 0.0~1.0,
      "max_loss_krw": 숫자,
      "recoverability": "reversible" | "hard_to_reverse" | "catastrophic",
      "mitigation": "구체적 대응 행동",
      "detection_trigger": "이 시나리오가 현실화되고 있다는 조기 신호"
    }
  ],
  "overall_risk": "low" | "medium" | "high" | "critical",
  "go_no_go_recommendation": "go" | "no_go" | "conditional_go",
  "conditions_if_conditional": "진행 조건",
  "executive_summary": "결론 2-3문장"
}

요구사항:
- 최소 3개 시나리오 (낙관 실패, 기술 실패, 시장 실패)
- probability는 각자 독립적 (합산이 1일 필요 없음)
- max_loss_krw는 최악 직접 비용 (매출 기회비용 제외)
"""

_OUTPUT_DIR = Path("docs/governance/pre_mortem")

HIGH_IMPACT_TYPES = {
    "paid_offer", "capital_action", "language_launch",
    "external_publish", "investment_thesis", "monetization_experiment",
}


def run_pre_mortem(
    decision_target: str,
    decision_type: str,
    context: str = "",
    target_id: Optional[int] = None,
    logger: Optional[HarnessLogger] = None,
) -> dict:
    """
    Pre-Mortem 분석 수행 및 ceo_decisions 기록.
    Returns: {scenarios, overall_risk, memo_path, approved}
    """
    orchestrator = LLMOrchestrator(logger)

    user_prompt = (
        f"의사결정 유형: {decision_type}\n"
        f"결정 내용: {decision_target}\n"
    )
    if context:
        user_prompt += f"\n추가 맥락:\n{context[:2000]}"

    result = orchestrator.claude_primary(
        system=_SYSTEM,
        user=user_prompt,
        model="claude-sonnet-4-6",
        max_tokens=4096,
    )

    raw = result["output"].replace("```json", "").replace("```", "").strip()
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        analysis = {
            "decision_target": decision_target,
            "scenarios": [],
            "overall_risk": "high",
            "go_no_go_recommendation": "conditional_go",
            "executive_summary": raw[:500],
        }

    memo_path = _write_memo(decision_target, decision_type, target_id, analysis)
    approved = _record_decision(decision_type, target_id, analysis, memo_path)

    if logger:
        logger.info(
            f"[pre_mortem] 완료: {analysis.get('overall_risk')} / "
            f"{analysis.get('go_no_go_recommendation')} memo={memo_path}"
        )

    return {
        "analysis": analysis,
        "memo_path": str(memo_path),
        "approved": approved,
    }


def _write_memo(
    decision_target: str,
    decision_type: str,
    target_id: Optional[int],
    analysis: dict,
) -> Path:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    safe_name = decision_type.upper().replace(" ", "_")
    name = f"{safe_name}-{target_id or 'NA'}-{today}.md"
    path = _OUTPUT_DIR / name

    scenarios_md = ""
    for i, s in enumerate(analysis.get("scenarios", []), 1):
        rec = s.get("recoverability", "")
        prob = s.get("probability", 0)
        loss = s.get("max_loss_krw", 0)
        scenarios_md += (
            f"\n### 시나리오 {i}: {s.get('scenario', '')}\n"
            f"- 확률: {prob:.0%} | 최대 손실: {loss:,}원 | 복구: {rec}\n"
            f"- 대응: {s.get('mitigation', '')}\n"
            f"- 조기 신호: {s.get('detection_trigger', '')}\n"
        )

    path.write_text(
        f"# Pre-Mortem 분석\n\n"
        f"- **결정**: {decision_target}\n"
        f"- **유형**: {decision_type}\n"
        f"- **날짜**: {today}\n"
        f"- **전체 위험**: **{analysis.get('overall_risk', 'N/A').upper()}**\n"
        f"- **권고**: **{analysis.get('go_no_go_recommendation', 'N/A')}**\n\n"
        f"## 결론\n\n{analysis.get('executive_summary', '')}\n\n"
        + (f"**조건부 진행 조건**: {analysis.get('conditions_if_conditional', '')}\n\n"
           if analysis.get("conditions_if_conditional") else "")
        + f"## 실패 시나리오\n{scenarios_md}\n"
        f"---\n> Pre-Mortem은 의사결정 전 최악 시나리오 사전 점검용이며, 진행 여부는 대표가 결정합니다.\n",
        encoding="utf-8",
    )
    return path


def _record_decision(
    decision_type: str,
    target_id: Optional[int],
    analysis: dict,
    memo_path: Path,
) -> bool:
    risk = analysis.get("overall_risk", "high")
    rec = analysis.get("go_no_go_recommendation", "conditional_go")

    approved = rec in ("go", "conditional_go") and risk != "critical"
    approval_type = "pre_mortem_approve" if approved else "pre_mortem_block"

    if target_id is not None:
        execute_query(
            """INSERT INTO ceo_decisions
                   (target_type, target_id, decision, approval_type, reason, decided_by)
               VALUES (%s, %s, %s, %s, %s, 'pre_mortem_agent')""",
            (
                decision_type,
                target_id,
                rec,
                approval_type,
                f"risk={risk} memo={memo_path}",
            ),
        )
    return approved
