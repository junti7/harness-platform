import anthropic
import json
import os
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger

load_dotenv()

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "2.00"))
TIER3_BATCH_LIMIT = int(os.getenv("TIER3_BATCH_LIMIT", "10"))

# Claude Sonnet 4.6 가격
INPUT_COST_PER_1K = 0.003
OUTPUT_COST_PER_1K = 0.015

# Physical AI 한국 실익 분석 프레임워크 — 매 이슈 동일 렌즈 적용
SYSTEM_PROMPT = """당신은 Physical AI / AGI / 반도체 분야 수석 애널리스트입니다.

당신의 분석 렌즈: **"이 신호가 한국의 제조·반도체·서비스·일자리·투자 중 무엇을 어떻게 바꾸는가"**

당신이 만드는 콘텐츠는 한국어 독자가 돈을 내고 읽는 유료 구독 인텔리전스입니다.
단순 요약이 아니라, 독자가 이 정보로 실제 의사결정(투자, 직업 선택, 사업 방향)을 할 수 있어야 합니다.

반드시 JSON 형식으로만 응답하세요. JSON 외 텍스트 금지.

출력 스키마:
{
  "final_title": "한국어 제목 — 구체적이고 긴박감 있게 (20~40자)",
  "hook": "독자를 잡는 첫 문장 — 수치 또는 반전을 포함 (1~2문장)",
  "what_happened": "무슨 일이 있었는가 — who, what, when, where, how를 포함한 팩트 서술 (3~5문장, 출처 포함)",
  "why_it_matters": "왜 중요한가 — 업계 구조 변화, 기술 전환점, 경쟁 역학을 설명 (4~6문장)",
  "quantitative_snapshot": {
    "label": "핵심 수치 테이블 제목",
    "rows": [
      {"metric": "지표명", "value": "수치", "context": "비교 맥락"}
    ]
  },
  "korea_implication": "한국 독자 함의 — 한국 기업·산업·직업·투자 관점에서 구체적으로 무엇을 의미하는가 (4~6문장)",
  "risk_counterargument": "리스크 또는 반론 — 낙관적 해석에 제동을 거는 현실적 우려 (2~3문장)",
  "watchlist": [
    {"item": "추적 대상 (기업/기술/지표/규제)", "reason": "왜 추적해야 하는가", "trigger": "어떤 이벤트가 발생하면 행동해야 하는가"}
  ],
  "decision_block": {
    "what_to_track": "다음 호까지 주목할 핵심 지표 또는 발표 (1~2문장)",
    "who_benefits": "수혜 대상 — 구체적 기업/업종/역할 (1~2문장)",
    "who_is_exposed": "리스크 노출 대상 — 구체적 기업/업종/역할 (1~2문장)"
  },
  "tags": ["태그1", "태그2", "태그3", "태그4"],
  "is_relevant": true
}

수치가 없으면 quantitative_snapshot.rows를 빈 배열로 남기세요. 추측 금지.
관련 없는 기사라면 is_relevant를 false로 설정하고 나머지는 빈 문자열로 반환하세요."""


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000 * INPUT_COST_PER_1K +
            output_tokens / 1000 * OUTPUT_COST_PER_1K)


def get_today_cost(logger=None) -> float:
    try:
        result = execute_query("""
            SELECT SUM(
                (input_tokens::float / 1000 * 0.003) +
                (output_tokens::float / 1000 * 0.015)
            ) as total_cost
            FROM api_cost_log
            WHERE DATE(created_at) = CURRENT_DATE
        """, fetch=True)
        if result and result[0]["total_cost"]:
            return float(result[0]["total_cost"])
    except Exception as e:
        if logger:
            logger.warning(f"비용 조회 실패 — 킬스위치 무력화 위험: {e}")
    return 0.0


def log_api_cost(model: str, input_tokens: int, output_tokens: int):
    execute_query("""
        INSERT INTO api_cost_log (model, input_tokens, output_tokens)
        VALUES (%s, %s, %s)
    """, (model, input_tokens, output_tokens))


def save_to_dlq(row: dict, error: str, logger):
    try:
        execute_query("""
            INSERT INTO dead_letter_queue (tier, item_id, item_type, error_message, raw_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            3, row["id"], "filtered_signal", str(error)[:500],
            json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        ))
    except Exception as dlq_err:
        logger.error(f"DLQ 저장 실패: {dlq_err}")


def save_refined_output(filtered_id, result: dict, tier3_model: str):
    execute_query("""
        INSERT INTO refined_outputs
            (filtered_signal_id, final_title, final_body, tags, tier3_model)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        filtered_id,
        result["final_title"],
        json.dumps(result, ensure_ascii=False),  # 전체 구조화 결과를 final_body에 저장
        json.dumps(result.get("tags", []), ensure_ascii=False),
        tier3_model,
    ))


def build_user_content(row: dict) -> str:
    title = row.get("title") or ""
    summary = row.get("summary") or ""
    source = row.get("source") or ""
    score = row.get("score") or 0
    facts_raw = row.get("extracted_facts")

    facts_str = ""
    if facts_raw:
        try:
            facts = facts_raw if isinstance(facts_raw, dict) else json.loads(facts_raw)
            if any(facts.get(k) for k in ["costs", "performance", "market_size", "key_players"]):
                facts_str = f"\n\nTier 2 추출 수치 데이터:\n{json.dumps(facts, ensure_ascii=False, indent=2)}"
        except Exception:
            pass

    return f"""출처: {source} | Tier2 점수: {score:.2f}

제목: {title}

본문 요약:
{summary[:2000]}
{facts_str}"""


def refine_signal(client: anthropic.Anthropic, row: dict) -> dict:
    user_content = build_user_content(row)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    log_api_cost(
        "claude-sonnet-4-6",
        response.usage.input_tokens,
        response.usage.output_tokens,
    )

    raw = response.content[0].text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)

    required = ["final_title", "is_relevant"]
    for field in required:
        if field not in parsed:
            raise ValueError(f"필수 필드 누락: {field}")

    return parsed


def refine(correlation_id: str = None):
    logger = HarnessLogger(tier=3, correlation_id=correlation_id)
    logger.info("=== Tier 3 정제 시작 (Physical AI 한국 실익 프레임워크) ===")

    rows = execute_query("""
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score,
               fs.extracted_facts
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        WHERE ro.id IS NULL
          AND fs.score >= 0.3
        ORDER BY fs.score DESC
        LIMIT %s
    """, (TIER3_BATCH_LIMIT,), fetch=True)

    if not rows:
        logger.info("처리할 데이터 없음")
        return 0

    logger.info(f"처리 대상: {len(rows)}개 (score >= 0.3 기준)")

    client = anthropic.Anthropic()
    refined = 0
    skipped = 0
    total_cost = 0.0

    for i, row in enumerate(rows):
        today_cost = get_today_cost(logger)
        if today_cost >= DAILY_COST_LIMIT:
            logger.warning(f"일일 비용 한도 도달: ${today_cost:.4f} / ${DAILY_COST_LIMIT}")
            break

        logger.info(f"[{i+1}/{len(rows)}] 처리 중: {row['title'][:50]}... (score={row['score']:.2f})")

        try:
            result = refine_signal(client, dict(row))
        except json.JSONDecodeError as e:
            logger.error(f"  JSON 파싱 실패: {e}")
            save_to_dlq(dict(row), f"json_decode:{e}", logger)
            skipped += 1
            continue
        except Exception as e:
            logger.error(f"  에러: {type(e).__name__}: {e}")
            save_to_dlq(dict(row), f"{type(e).__name__}:{e}", logger)
            skipped += 1
            continue

        if not result.get("is_relevant", True):
            logger.info("  → Claude 판단: 관련 없음, 탈락")
            skipped += 1
            continue

        save_refined_output(row["id"], result, "claude-sonnet-4-6")

        cost = estimate_cost(600, 800)
        total_cost += cost
        logger.info(f"  → 완료: {result['final_title'][:50]}")
        refined += 1

    logger.info("=" * 50)
    logger.info(f"Tier 3 완료: 정제 {refined}개 / 스킵 {skipped}개 / 예상비용 ${total_cost:.4f}")
    logger.info("=" * 50)
    return refined


if __name__ == "__main__":
    refine()
