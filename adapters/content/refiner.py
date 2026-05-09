import anthropic
import json
import os
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger

load_dotenv()

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "1.00"))
INPUT_COST_PER_1K = 0.003
OUTPUT_COST_PER_1K = 0.015

SYSTEM_PROMPT = """당신은 기술 트렌드 큐레이터입니다.

주어진 기술 기사를 분석하여 다음 JSON 형식으로만 응답하세요:
{
  "final_title": "한국어 제목 (명확하고 간결하게)",
  "final_body": "한국어 본문 (3~5문장, 핵심 내용과 의미 포함)",
  "tags": ["태그1", "태그2", "태그3"],
  "is_relevant": true
}

관련 없는 기사라면 is_relevant를 false로 설정하세요.
JSON 외 다른 텍스트는 출력하지 마세요."""

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


def save_to_dlq(row: dict, error: str, logger):
    try:
        execute_query("""
            INSERT INTO dead_letter_queue (tier, item_id, item_type, error_message, raw_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            3,
            row["id"],
            "filtered_signal",
            str(error)[:500],
            json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        ))
    except Exception as dlq_err:
        logger.error(f"  → DLQ 저장 실패: {dlq_err}")

def log_api_cost(model: str, input_tokens: int, output_tokens: int):
    execute_query("""
        INSERT INTO api_cost_log (model, input_tokens, output_tokens)
        VALUES (%s, %s, %s)
    """, (model, input_tokens, output_tokens))

def save_refined_output(filtered_id, final_title, final_body, tags, tier3_model):
    execute_query("""
        INSERT INTO refined_outputs
            (filtered_signal_id, final_title, final_body, tags, tier3_model)
        VALUES (%s, %s, %s, %s, %s)
    """, (filtered_id, final_title, final_body,
          json.dumps(tags, ensure_ascii=False), tier3_model))

def refine_signal(client, row: dict):
    title = row["title"]
    summary = row["summary"] or ""
    content = f"제목: {title}\n\n내용: {summary[:1000]}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )

    log_api_cost(
        "claude-sonnet-4-6",
        response.usage.input_tokens,
        response.usage.output_tokens
    )

    raw = response.content[0].text.strip()

    # 🤔 왜 replace? Claude가 JSON을 ```json``` 마크다운으로 감쌀 때가 있음
    raw = raw.replace("```json", "").replace("```", "").strip()

    parsed = json.loads(raw)

    required = ["final_title", "final_body", "tags", "is_relevant"]
    for field in required:
        if field not in parsed:
            raise ValueError(f"필수 필드 누락: {field}")

    return parsed

def refine(correlation_id: str = None):
    logger = HarnessLogger(tier=3, correlation_id=correlation_id)
    logger.info("=== Tier 3 정제 시작 ===")

    rows = execute_query("""
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        WHERE ro.id IS NULL
        ORDER BY fs.score DESC
        LIMIT 20
    """, fetch=True)

    if not rows:
        logger.info("처리할 데이터 없음")
        return 0

    logger.info(f"처리 대상: {len(rows)}개")

    client = anthropic.Anthropic()
    refined = 0
    skipped = 0
    total_cost = 0.0

    for i, row in enumerate(rows):
        today_cost = get_today_cost(logger)
        if today_cost >= DAILY_COST_LIMIT:
            logger.warning(f"일일 비용 한도 도달: ${today_cost:.4f}")
            break

        logger.info(f"[{i+1}/{len(rows)}] 처리 중: {row['title'][:50]}...")

        try:
            result = refine_signal(client, row)
        except json.JSONDecodeError as e:
            logger.error(f"  → JSON 파싱 실패: {e}")
            save_to_dlq(dict(row), f"json_decode:{e}", logger)
            skipped += 1
            continue
        except Exception as e:
            logger.error(f"  → 에러: {type(e).__name__}: {e}")
            save_to_dlq(dict(row), f"{type(e).__name__}:{e}", logger)
            skipped += 1
            continue

        if not result.get("is_relevant", True):
            logger.info(f"  → Claude 판단: 관련 없음, 탈락")
            skipped += 1
            continue

        save_refined_output(
            row["id"],
            result["final_title"],
            result["final_body"],
            result["tags"],
            "claude-sonnet-4-6"
        )

        cost = estimate_cost(500, 200)
        total_cost += cost
        logger.info(f"  → 완료: {result['final_title'][:40]}")
        logger.info(f"  → 태그: {result['tags']}")
        refined += 1

    logger.info("=" * 50)
    logger.info(f"Tier 3 완료: 정제 {refined}개 / 스킵 {skipped}개")
    logger.info(f"예상 비용: ${total_cost:.4f}")
    logger.info("=" * 50)
    return refined

if __name__ == "__main__":
    refine()
