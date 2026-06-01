import json
import logging
import os
import re
from dotenv import load_dotenv
from core.domain_config import load_prompt_text
from core.database import execute_query
from core.gemini_sdk import generate_text
from core.logger import HarnessLogger
from core.cost_alerts import check_and_alert

load_dotenv()

DAILY_COST_LIMIT = float(os.getenv("DAILY_COST_LIMIT_USD", "2.00"))
TIER3_BATCH_LIMIT = int(os.getenv("TIER3_BATCH_LIMIT", "10"))
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Per-1k token estimates used only for internal rough logs/guards.
MODEL_PRICES_PER_1K = {
    "gemini-1.5-pro": (0.0035, 0.0105),
    "gemini-2.5-flash": (0.0003, 0.0025),
    "gemini-2.0-flash": (0.0003, 0.0025),
}
INPUT_COST_PER_1K, OUTPUT_COST_PER_1K = MODEL_PRICES_PER_1K["gemini-2.5-flash"]

SYSTEM_PROMPT = load_prompt_text("physical_ai_analyst")
_logger = logging.getLogger(__name__)


def _price_for_model(model: str) -> tuple[float, float]:
    model_lower = (model or "").lower()
    for key, price in MODEL_PRICES_PER_1K.items():
        if key in model_lower:
            return price
    return MODEL_PRICES_PER_1K["gemini-2.5-flash"]


def estimate_cost(input_tokens: int, output_tokens: int, model: str | None = None) -> float:
    model = model or DEFAULT_GEMINI_MODEL
    input_price, output_price = _price_for_model(model)
    return (input_tokens / 1000 * input_price +
            output_tokens / 1000 * output_price)


def get_today_cost(logger=None) -> float:
    """오늘 사용한 모든 LLM API 비용 합산 (Anthropic + Google + OpenAI)."""
    try:
        result = execute_query("""
            SELECT COALESCE(SUM(
                CASE provider
                    WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                    WHEN 'google'    THEN (input_tokens::float/1000000*0.3) + (output_tokens::float/1000000*2.5)
                    WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                    ELSE 0
                END
            ), 0) as total_cost
            FROM api_cost_log
            WHERE DATE(created_at) = CURRENT_DATE
        """, fetch=True)
        if result and result[0]["total_cost"]:
            return float(result[0]["total_cost"])
    except Exception as e:
        if logger:
            logger.warning(f"비용 조회 실패 — 킬스위치 무력화 위험: {e}")
    return 0.0


def log_api_cost(model: str, input_tokens: int, output_tokens: int, provider: str = "google"):
    try:
        execute_query("""
            INSERT INTO api_cost_log (model, input_tokens, output_tokens, provider)
            VALUES (%s, %s, %s, %s)
        """, (model, input_tokens, output_tokens, provider))
    except Exception as exc:
        _logger.warning(f"API 비용 로그 저장 실패 — 응답은 계속 진행: {exc}")


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


def save_refined_output(filtered_id, result: dict, tier3_model: str) -> int | None:
    rows = execute_query("""
        INSERT INTO refined_outputs
            (filtered_signal_id, final_title, final_body, tags, tier3_model)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        filtered_id,
        result["final_title"],
        json.dumps(result, ensure_ascii=False),  # 전체 구조화 결과를 final_body에 저장
        json.dumps(result.get("tags", []), ensure_ascii=False),
        tier3_model,
    ), fetch=True)
    return rows[0]["id"] if rows else None


def _sanitize_for_prompt(text: str) -> str:
    """LaTeX 수식·특수 이스케이프 제거 — 모델에 전달 전 전처리."""
    if not text:
        return text
    # LaTeX 수식 블록 제거 ($...$, \(...\), \[...\])
    text = re.sub(r'\$\$[^$]*\$\$', '[수식]', text)
    text = re.sub(r'\$[^$\n]{1,80}\$', '[수식]', text)
    text = re.sub(r'\\[\(\[].*?\\[\)\]]', '[수식]', text, flags=re.DOTALL)
    # LaTeX 명령어 (\Delta, \alpha 등) → 제거
    text = re.sub(r'\\[A-Za-z]+\b', '', text)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def build_user_content(row: dict) -> str:
    title = _sanitize_for_prompt(row.get("title") or "")
    summary = _sanitize_for_prompt(row.get("summary") or "")
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


def _extract_json_candidate(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("빈 응답")

    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("JSON 객체 시작점({)을 찾지 못함")

    # brace depth 추적으로 정확한 닫는 } 위치 찾기
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("JSON 닫는 } 쌍이 맞지 않음")


def _fix_invalid_json_escapes(s: str) -> str:
    r"""JSON 문자열 내 무효 이스케이프 시퀀스(예: \D, \e) → \\X 로 치환."""
    valid_esc = set('"\\' + "/" + "bfnrtu")
    result: list[str] = []
    i = 0
    in_string = False
    escape_next = False
    while i < len(s):
        ch = s[i]
        if escape_next:
            if in_string and ch not in valid_esc:
                result.append("\\")  # 추가 백슬래시로 이스케이프
            result.append(ch)
            escape_next = False
            i += 1
            continue
        if ch == "\\" and in_string:
            result.append(ch)
            escape_next = True
            i += 1
            continue
        if ch == '"':
            in_string = not in_string
        result.append(ch)
        i += 1
    return "".join(result)


def _parse_refiner_json(raw_text: str) -> dict:
    candidates: list[str] = []
    try:
        candidates.append(_extract_json_candidate(raw_text))
    except Exception:
        candidates.append((raw_text or "").strip())

    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(candidate)
        # 제어문자 제거
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", candidate)
        if sanitized != candidate:
            expanded.append(sanitized)
        # 무효 JSON 이스케이프 수정
        fixed = _fix_invalid_json_escapes(sanitized)
        if fixed != sanitized:
            expanded.append(fixed)

    last_error: Exception | None = None
    for candidate in expanded:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except Exception as exc:
            last_error = exc
    raise last_error or ValueError("JSON 파싱 실패")


def _fallback_refined_output(row: dict, error: Exception) -> dict | None:
    score = float(row.get("score") or 0.0)
    title = (row.get("title") or "").strip()
    summary = (row.get("summary") or "").strip()
    source = (row.get("source") or "").strip()
    if score < 0.75 or not title or not summary:
        return None

    compact_summary = re.sub(r"\s+", " ", summary)[:600].strip()
    compact_title = re.sub(r"\s+", " ", title)[:120].strip()
    return {
        "final_title": compact_title,
        "is_relevant": True,
        "evidence_posture": {
            "classification": "speculative",
            "why": f"Tier3 fallback used after malformed model JSON: {type(error).__name__}",
        },
        "summary": compact_summary,
        "source": source,
        "tags": ["tier3-fallback", "json-recovery"],
        "fallback_used": True,
    }


def refine_signal(model_name: str, row: dict) -> dict:
    user_content = build_user_content(row)

    # Gemini's system prompt is handled via GenerationConfig or passed differently
    # For simplicity, we prepend it to the user message as per some tutorials.
    full_prompt = SYSTEM_PROMPT + "\n반드시 유효한 JSON 형식으로 응답을 마무리하세요. 중간에 끊기지 않도록 분량을 조절하되 깊이는 유지하세요.\n\n---\n\n" + user_content
    
    # gemini-2.5-flash는 thinking 토큰이 output budget을 소모하므로 8192로 상향
    raw_text, usage = generate_text(
        full_prompt,
        model=model_name,
        timeout_seconds=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60")),
        max_output_tokens=int(os.getenv("TIER3_MAX_OUTPUT_TOKENS", "8192")),
        response_mime_type="application/json",
    )
    input_tokens = usage["prompt_token_count"]
    output_tokens = usage["candidates_token_count"]
    
    log_api_cost(
        model_name,
        input_tokens,
        output_tokens,
    )

    parsed = _parse_refiner_json(raw_text)

    required = ["final_title", "is_relevant", "evidence_posture"]
    for field in required:
        if field not in parsed:
            raise ValueError(f"필수 필드 누락: {field}")

    evidence = parsed.get("evidence_posture") or {}
    if not isinstance(evidence, dict):
        raise ValueError("evidence_posture가 dict 형태가 아님")
    # LLM이 "verified | speculative" 같이 복합값을 반환하는 경우 첫 번째 유효값으로 정규화
    _VALID_CLASS = {"verified", "company-self-report", "speculative"}
    raw_class = str(evidence.get("classification", "")).strip()
    if raw_class not in _VALID_CLASS:
        for candidate in re.split(r"[|,/]", raw_class):
            candidate = candidate.strip()
            if candidate in _VALID_CLASS:
                evidence["classification"] = candidate
                parsed["evidence_posture"] = evidence
                break
        else:
            raise ValueError(f"evidence_posture.classification 값 오류: {raw_class}")
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

    _gemini_model_name = DEFAULT_GEMINI_MODEL
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
            result = refine_signal(_gemini_model_name, dict(row))
            check_and_alert(get_today_cost(logger), DAILY_COST_LIMIT, logger)
        except json.JSONDecodeError as e:
            fallback = _fallback_refined_output(dict(row), e)
            if fallback:
                save_refined_output(row["id"], fallback, f"{_gemini_model_name}:fallback")
                logger.warning("  JSON 파싱 실패 — fallback 정제로 저장")
                refined += 1
                continue
            logger.error(f"  JSON 파싱 실패: {e}")
            save_to_dlq(dict(row), f"json_decode:{e}", logger)
            skipped += 1
            continue
        except Exception as e:
            fallback = _fallback_refined_output(dict(row), e)
            if fallback:
                save_refined_output(row["id"], fallback, f"{_gemini_model_name}:fallback")
                logger.warning(f"  {type(e).__name__} — fallback 정제로 저장")
                refined += 1
                continue
            logger.error(f"  에러: {type(e).__name__}: {e}")
            save_to_dlq(dict(row), f"{type(e).__name__}:{e}", logger)
            skipped += 1
            continue

        if not result.get("is_relevant", True):
            logger.info("  → Gemini 판단: 관련 없음, 탈락")
            skipped += 1
            continue

        refined_output_id = save_refined_output(row["id"], result, _gemini_model_name)

        # cost는 refine_signal 내부에서 이미 로그됨. 여기서는 rough estimate만 사용.
        cost = estimate_cost(1000, 1000, _gemini_model_name)
        total_cost += cost
        logger.info(f"  → 완료: {result['final_title'][:50]}")
        refined += 1

        # Tier 3 완료 즉시 QA Gate 실행 (qa_clear 누적 방지)
        if refined_output_id:
            try:
                from adapters.content.qa_agent import qa_check_refined_output
                qa_ok = qa_check_refined_output(refined_output_id, correlation_id=correlation_id)
                logger.info(f"  → QA: {'✅ APPROVED' if qa_ok else '❌ REJECTED'} (id={refined_output_id})")
            except Exception as qa_err:
                logger.warning(f"  → QA 실행 실패 (비치명적): {qa_err}")

    logger.info("=" * 50)
    logger.info(f"Tier 3 완료: 정제 {refined}개 / 스킵 {skipped}개 / 예상비용 ${total_cost:.4f}")
    logger.info("=" * 50)
    return refined


if __name__ == "__main__":
    refine()
