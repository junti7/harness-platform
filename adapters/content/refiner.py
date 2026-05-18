import anthropic
import json
import os
from dotenv import load_dotenv
from core.domain_config import load_prompt_text
from core.database import execute_query
from core.logger import HarnessLogger
from core.cost_alerts import check_and_alert

load_dotenv()

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "2.00"))
TIER3_BATCH_LIMIT = int(os.getenv("TIER3_BATCH_LIMIT", "10"))

MODEL_PRICES_PER_1K = {
    "haiku": (0.0008, 0.004),
    "sonnet": (0.003, 0.015),
    "opus": (0.015, 0.075),
}
INPUT_COST_PER_1K = MODEL_PRICES_PER_1K["sonnet"][0]
OUTPUT_COST_PER_1K = MODEL_PRICES_PER_1K["sonnet"][1]

SYSTEM_PROMPT = load_prompt_text("physical_ai_analyst")


def _price_for_model(model: str) -> tuple[float, float]:
    model_lower = (model or "").lower()
    for key, price in MODEL_PRICES_PER_1K.items():
        if key in model_lower:
            return price
    return MODEL_PRICES_PER_1K["sonnet"]


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet") -> float:
    input_price, output_price = _price_for_model(model)
    return (input_tokens / 1000 * input_price +
            output_tokens / 1000 * output_price)


def get_today_cost(logger=None) -> float:
    try:
        result = execute_query("""
            SELECT SUM(
                CASE
                    WHEN LOWER(model) LIKE '%haiku%' THEN
                        (input_tokens::float / 1000 * 0.0008) + (output_tokens::float / 1000 * 0.004)
                    WHEN LOWER(model) LIKE '%opus%' THEN
                        (input_tokens::float / 1000 * 0.015) + (output_tokens::float / 1000 * 0.075)
                    ELSE
                        (input_tokens::float / 1000 * 0.003) + (output_tokens::float / 1000 * 0.015)
                END
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


def log_api_cost(model: str, input_tokens: int, output_tokens: int, provider: str = "anthropic"):
    execute_query("""
        INSERT INTO api_cost_log (model, input_tokens, output_tokens, provider)
        VALUES (%s, %s, %s, %s)
    """, (model, input_tokens, output_tokens, provider))


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
        max_tokens=8192,
        system=SYSTEM_PROMPT + "\n반드시 유효한 JSON 형식으로 응답을 마무리하세요. 중간에 끊기지 않도록 분량을 조절하되 깊이는 유지하세요.",
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

    required = ["final_title", "is_relevant", "evidence_posture"]
    for field in required:
        if field not in parsed:
            raise ValueError(f"필수 필드 누락: {field}")

    evidence = parsed.get("evidence_posture") or {}
    if not isinstance(evidence, dict):
        raise ValueError("evidence_posture가 dict 형태가 아님")
    if evidence.get("classification") not in {"verified", "company-self-report", "speculative"}:
        raise ValueError(f"evidence_posture.classification 값 오류: {evidence.get('classification')}")
    if not evidence.get("why"):
        raise ValueError("evidence_posture.why 누락")

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
            check_and_alert(get_today_cost(logger), DAILY_COST_LIMIT, logger)
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
