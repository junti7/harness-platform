import json
import logging
import google.generativeai as genai
import os
import re
import httpx
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger
from core.topic_registry import load_active_topics

load_dotenv()

# --- Gemini Configuration for Tier 2 ---
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

TIER2_LLM_MODEL = os.getenv("TIER2_LLM_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "45"))
TIER2_BATCH_LIMIT = int(os.getenv("TIER2_BATCH_LIMIT", "20"))
TIER2_BATCH_LIMIT_MBP_ACTIVE = int(os.getenv("TIER2_BATCH_LIMIT_MBP_ACTIVE", "80"))
TIER2_BATCH_LIMIT_BACKLOG = int(os.getenv("TIER2_BATCH_LIMIT_BACKLOG", "120"))
MAX_FACT_EXTRACTION_PER_BATCH = 5
TIER2_BACKLOG_DISABLE_FACTS_THRESHOLD = int(os.getenv("TIER2_BACKLOG_DISABLE_FACTS_THRESHOLD", "3000"))
OLLAMA_REMOTE_HOST = os.getenv("OLLAMA_REMOTE_HOST", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
TIER2_FACT_OLLAMA_MODEL = os.getenv("TIER2_FACT_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")).strip()
TIER2_USE_REMOTE_OLLAMA = os.getenv("TIER2_USE_REMOTE_OLLAMA", "true").strip().lower() in {"1", "true", "yes"}

LOW_VALUE_PATTERNS = [
    r"\bjob posting\b", r"\bhiring\b.*\bjob\b", r"\bpress release\b",
    r"\bsponsored\b", r"\badvertisement\b", r"\bcookies?\b.*\bprivacy\b",
]

FACT_EXTRACTION_PROMPT = """너는 기술/경제 전문 분석가이다. 다음 기술 기사의 본문을 읽고, 핵심 수치 데이터를 추출하라.

출력 형식 (반드시 JSON만 응답, 다른 텍스트 금지):
{
  "costs": [{"item": "이름", "value": "수치", "trend": "하락/상승/유지"}],
  "performance": [{"metric": "항목", "value": "수치"}],
  "market_size": [{"segment": "분야", "value": "수치", "year": "연도"}],
  "key_players": ["기업1", "기업2"]
}

없는 항목은 빈 배열로 반환. 추측 금지.

기사 본문:
"""
_logger = logging.getLogger(__name__)


def probe_ollama_host(host: str) -> bool:
    if not host:
        return False
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=2.5)
        return resp.status_code == 200
    except Exception:
        return False

# TODO: 이 비용 로깅 함수들은 refiner.py와 중복됩니다. 향후 core 유틸리티로 리팩토링해야 합니다.
def log_api_cost(model: str, input_tokens: int, output_tokens: int, provider: str = "google"):
    try:
        execute_query("""
            INSERT INTO api_cost_log (model, input_tokens, output_tokens, provider)
            VALUES (%s, %s, %s, %s)
        """, (model, input_tokens, output_tokens, provider))
    except Exception as exc:
        _logger.warning(f"API 비용 로그 저장 실패 — 응답은 계속 진행: {exc}")


def _gemini_call(model: genai.GenerativeModel, text: str) -> dict:
    full_prompt = FACT_EXTRACTION_PROMPT + text[:4000] #
    response = model.generate_content(full_prompt)

    # Log API cost
    log_api_cost(
        model.model_name.split('/')[-1],
        response.usage_metadata.prompt_token_count,
        response.usage_metadata.candidates_token_count,
    )
    
    raw_content = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw_content)


def _ollama_call(host: str, text: str) -> dict:
    prompt = FACT_EXTRACTION_PROMPT + text[:4000]
    resp = httpx.post(
        f"{host}/api/chat",
        json={
            "model": TIER2_FACT_OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
        },
        timeout=20,
    )
    resp.raise_for_status()
    content = (((resp.json() or {}).get("message") or {}).get("content") or "").strip()
    return json.loads(content)


def extract_facts(model: genai.GenerativeModel, text: str, logger: HarnessLogger) -> dict:
    if not text or len(text) < 100:
        return {}

    try:
        if TIER2_USE_REMOTE_OLLAMA and probe_ollama_host(OLLAMA_REMOTE_HOST):
            try:
                return _ollama_call(OLLAMA_REMOTE_HOST, text)
            except Exception as exc:
                logger.warning(f"MBP Ollama 팩트 추출 실패 — Gemini fallback: {type(exc).__name__}: {exc}")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_gemini_call, model, text)
            return future.result(timeout=GEMINI_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        logger.warning(f"Gemini timeout ({GEMINI_TIMEOUT_SECONDS}s) — 팩트 추출 건너뜀")
        return {}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Gemini JSON 파싱 또는 키 오류: {type(e).__name__}")
        return {}
    except Exception as e:
        logger.warning(f"Gemini 호출 실패: {type(e).__name__}: {e}")
        return {}


def compute_relevance_score(title: str, summary: str, full_content: str) -> float:
    high_value_keywords = load_active_topics("physical_ai")
    text = f"{title} {summary} {full_content[:2000]}".lower()

    for pattern in LOW_VALUE_PATTERNS:
        if re.search(pattern, text):
            return 0.0

    hits = sum(1 for kw in high_value_keywords if kw in text)
    score = min(1.0, hits * 0.08)

    return max(0.1, score)


def save_filtered_signal(raw_id, source, title, summary, score, category, content_hash, facts, model_name):
    execute_query("""
        INSERT INTO filtered_signals
            (raw_signal_id, source, title, summary, score, category, content_hash, tier2_model, extracted_facts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
    """, (raw_id, source, title, summary, score, category, content_hash, model_name, json.dumps(facts)))


def pending_backlog_count() -> int:
    rows = execute_query("SELECT count(*) AS cnt FROM raw_signals WHERE status = 'pending'", fetch=True)
    return int((rows or [{"cnt": 0}])[0]["cnt"])


def filter_signals(correlation_id: str = None, limit: int | None = None):
    logger = HarnessLogger(tier=2, correlation_id=correlation_id)
    remote_ollama_active = TIER2_USE_REMOTE_OLLAMA and probe_ollama_host(OLLAMA_REMOTE_HOST)
    backlog_count = pending_backlog_count()
    adaptive_batch_limit = (
        TIER2_BATCH_LIMIT_BACKLOG
        if remote_ollama_active and backlog_count >= TIER2_BACKLOG_DISABLE_FACTS_THRESHOLD
        else (TIER2_BATCH_LIMIT_MBP_ACTIVE if remote_ollama_active else TIER2_BATCH_LIMIT)
    )
    batch_limit = limit or adaptive_batch_limit
    fact_budget = 0 if backlog_count >= TIER2_BACKLOG_DISABLE_FACTS_THRESHOLD else MAX_FACT_EXTRACTION_PER_BATCH
    logger.info(
        f"=== Tier 2 필터링 시작 (batch={batch_limit}, model={TIER2_LLM_MODEL}, "
        f"mbp_ollama={'on' if remote_ollama_active else 'off'}, pending={backlog_count}, fact_budget={fact_budget}) ==="
    )

    rows = execute_query(
        "SELECT id, source, raw_data, content_hash, full_content FROM raw_signals "
        "WHERE status = 'pending' "
        "ORDER BY ingested_at ASC LIMIT %s",
        (batch_limit,),
        fetch=True,
    )

    if not rows:
        logger.info("처리할 pending signal 없음")
        return 0

    logger.info(f"처리 대상: {len(rows)}개")
    model = genai.GenerativeModel(TIER2_LLM_MODEL)
    passed = 0
    failed = 0
    facts_extracted = 0

    for row in rows:
        raw_id = row["id"]
        source = row["source"]
        raw_data = row["raw_data"]
        content_hash = row["content_hash"]
        full_content = row["full_content"] or ""
        title = raw_data.get("title", "")
        summary = raw_data.get("summary", "")

        score = compute_relevance_score(title, summary, full_content)

        if score < 0.15:
            execute_query("UPDATE raw_signals SET status = 'filtered_fail' WHERE id = %s", (raw_id,))
            failed += 1
            continue

        facts = {}
        if score >= 0.4 and facts_extracted < fact_budget:
            logger.info(f"  [{facts_extracted+1}/{fact_budget}] 팩트 추출 중 (score={score:.2f}): {title[:50]}...")
            facts = extract_facts(model, full_content if full_content else summary, logger)
            facts_extracted += 1
        elif score >= 0.4:
            logger.info(f"  팩트 추출 스킵 (backlog/배치 정책, score={score:.2f}): {title[:50]}...")

        save_filtered_signal(raw_id, source, title, summary, score, "physical_ai", content_hash, facts, TIER2_LLM_MODEL)
        execute_query("UPDATE raw_signals SET status = 'filtered_pass' WHERE id = %s", (raw_id,))
        passed += 1

    logger.info(f"=== Tier 2 완료: pass={passed}, fail={failed}, facts_extracted={facts_extracted} ===")
    return passed


if __name__ == "__main__":
    filter_signals()
