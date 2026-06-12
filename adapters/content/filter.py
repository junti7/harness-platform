import json
import logging
import os
import re
import httpx
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dotenv import load_dotenv
from core.database import execute_query
from core.gemini_sdk import generate_text
from core.lane_router import log_lane_a_escalation, validate_lane_a_json
from core.logger import HarnessLogger
from core.topic_registry import load_active_topics
from core.trading_universe import ensure_trading_schema

load_dotenv()

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
    model_lower = (model or "").lower()
    if provider == "google":
        if model_lower.startswith("claude"):
            provider = "anthropic"
        elif model_lower.startswith("gpt") or model_lower.startswith("o"):
            provider = "openai"
        elif any(model_lower.startswith(prefix) for prefix in ("gemma", "qwen", "llama", "mistral", "deepseek", "nomic-embed")):
            provider = "ollama"
    try:
        try:
            execute_query("""
                INSERT INTO api_cost_log (model, input_tokens, output_tokens, provider)
                VALUES (%s, %s, %s, %s)
            """, (model, input_tokens, output_tokens, provider))
        except Exception:
            execute_query("""
                INSERT INTO api_cost_log (model, input_tokens, output_tokens)
                VALUES (%s, %s, %s)
            """, (model, input_tokens, output_tokens))
    except Exception as exc:
        _logger.warning(f"API 비용 로그 저장 실패 — 응답은 계속 진행: {exc}")


def _gemini_call(model_name: str, text: str) -> dict:
    full_prompt = FACT_EXTRACTION_PROMPT + text[:4000] #
    raw_text, usage = generate_text(
        full_prompt,
        model=model_name,
        timeout_seconds=GEMINI_TIMEOUT_SECONDS,
        max_output_tokens=2048,
    )

    # Log API cost
    log_api_cost(
        model_name,
        usage["prompt_token_count"],
        usage["candidates_token_count"],
    )
    
    raw_content = raw_text.strip().replace("```json", "").replace("```", "").strip()
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


_FACT_REQUIRED_KEYS = ["costs", "performance", "market_size", "key_players"]

# Lane A Sonnet 재실행용 모델 (schema 검증 실패 시)
_LANE_A_ESCALATION_MODEL = os.getenv("LANE_A_ESCALATION_MODEL", "gemini-2.5-pro")


def extract_facts(model_name: str, text: str, logger: HarnessLogger) -> dict:
    if not text or len(text) < 100:
        return {}

    raw_output: str | None = None
    try:
        if TIER2_USE_REMOTE_OLLAMA and probe_ollama_host(OLLAMA_REMOTE_HOST):
            try:
                result = _ollama_call(OLLAMA_REMOTE_HOST, text)
                # Lane A 검증 게이트: Ollama 출력도 schema 검증
                if isinstance(result, dict) and all(k in result for k in _FACT_REQUIRED_KEYS):
                    return result
                log_lane_a_escalation("extract_facts", "ollama_schema_fail")
                logger.warning("Ollama 팩트 schema 검증 실패 — Gemini 재실행")
            except Exception as exc:
                logger.warning(f"MBP Ollama 팩트 추출 실패 — Gemini fallback: {type(exc).__name__}: {exc}")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_gemini_call, model_name, text)
            result = future.result(timeout=GEMINI_TIMEOUT_SECONDS)

        # Lane A 검증 게이트: required_keys 확인
        if isinstance(result, dict) and all(k in result for k in _FACT_REQUIRED_KEYS):
            return result

        # 검증 실패 → 프리미엄 모델로 자동 승급
        log_lane_a_escalation("extract_facts", "gemini_schema_fail")
        logger.warning(f"Gemini 팩트 schema 검증 실패 — {_LANE_A_ESCALATION_MODEL} 재실행")
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_gemini_call, _LANE_A_ESCALATION_MODEL, text)
                return future.result(timeout=GEMINI_TIMEOUT_SECONDS)
        except Exception as exc:
            logger.warning(f"승급 모델 팩트 추출 실패: {type(exc).__name__}: {exc}")
            return {}

    except FuturesTimeoutError:
        logger.warning(f"Gemini timeout ({GEMINI_TIMEOUT_SECONDS}s) — 팩트 추출 건너뜀")
        return {}
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Gemini JSON 파싱 또는 키 오류: {type(e).__name__}")
        return {}
    except Exception as e:
        logger.warning(f"Gemini 호출 실패: {type(e).__name__}: {e}")
        return {}


def compute_relevance_score(title: str, summary: str, full_content: str, source: str = "", domain: str = "physical_ai") -> float:
    high_value_keywords = load_active_topics(domain)
    text = f"{title} {summary} {full_content[:2000]}".lower()

    # 숏폼/소셜 미디어 여부 판단
    source_lower = source.lower()
    is_short_form = any(s in source_lower for s in ["youtube", "instagram", "tiktok", "threads", "x", "twitter"])

    # 숏폼 매체는 광고/스폰서 태그가 일상적이므로 LOW_VALUE_PATTERNS에서 즉각 탈락시키지 않고 패널티만 부여
    penalty = 0.0
    for pattern in LOW_VALUE_PATTERNS:
        if re.search(pattern, text):
            if is_short_form:
                penalty += 0.05
            else:
                return 0.0

    hits = sum(1 for kw in high_value_keywords if kw in text)
    score = hits * 0.08 - penalty

    # 숏폼 미디어는 텍스트 길이가 짧아 키워드가 1개만 등장해도 최소 0.2점을 부여하여 Tier2(LLM) 검증 기회를 줌
    if is_short_form and hits >= 1:
        score = max(score, 0.2)

    # 공공데이터포털은 이미 수집기(Tier 1)에서 타겟 키워드 필터링을 거쳤으므로 강제 패스 (최소 0.2 부여)
    if "공공데이터포털" in source:
        score = max(score, 0.2)

    return max(0.1, score)


def compute_cluster_bonus(raw_data: dict, domain: str = "physical_ai") -> float:
    cluster = str(raw_data.get("topic_cluster") or "").strip().lower()
    source_name = str(raw_data.get("source_name") or "").strip().lower()
    title = str(raw_data.get("title") or "").strip().lower()
    if not cluster:
        return 0.0
    if domain == "edu_consulting":
        if cluster in {"worker_ai", "career_major", "job_seeker_ai", "military_ai", "digital_dependence", "parenting_ai"}:
            return 0.18
        if cluster == "general_ai_education" and any(term in f"{title} {source_name}" for term in ["진로", "전공", "직장인", "부모", "스마트폰", "군대"]):
            return 0.08
        return 0.03
    if cluster in {"power_cooling", "networking_optics", "memory_packaging", "simulation_software", "warehouse_deployment", "edge_realtime", "embodiment_robotics", "compute_models"}:
        return 0.14
    if cluster == "general_physical_ai" and any(term in f"{title} {source_name}" for term in ["hbm", "packaging", "cooling", "digital twin", "warehouse", "logistics"]):
        return 0.07
    return 0.02


def determine_category(text: str) -> str:
    categories = []
    text_lower = text.lower()
    
    if any(k in text_lower for k in ["ai", "인공지능", "agi"]):
        categories.append("AI")
    if any(k in text_lower for k in ["로봇", "robot", "로보틱스", "자율주행", "자율비행", "드론"]):
        categories.append("Robotics")
    if any(k in text_lower for k in ["교육", "에듀테크", "학습", "커리큘럼", "학교", "학생", "교사"]):
        categories.append("Education")
    if any(k in text_lower for k in ["부동산", "경매", "투자", "상권", "주택", "토지", "공매", "재건축", "재개발"]):
        categories.append("RealEstate")
        
    if not categories:
        return "physical_ai" # 기본값
    return ", ".join(categories)


def save_filtered_signal(raw_id, source, title, summary, score, category, content_hash, facts, model_name, domain="physical_ai"):
    execute_query("""
        INSERT INTO filtered_signals
            (raw_signal_id, source, title, summary, score, category, content_hash, tier2_model, extracted_facts, domain)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
    """, (raw_id, source, title, summary, score, category, content_hash, model_name, json.dumps(facts), domain))


def pending_backlog_count() -> int:
    rows = execute_query("SELECT count(*) AS cnt FROM raw_signals WHERE status = 'pending'", fetch=True)
    return int((rows or [{"cnt": 0}])[0]["cnt"])


def filter_signals(correlation_id: str = None, limit: int | None = None, domain: str = "physical_ai"):
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
        "AND COALESCE(domain, raw_data->>'domain', 'physical_ai') = %s "
        "ORDER BY ingested_at ASC LIMIT %s",
        (domain, batch_limit),
        fetch=True,
    )

    if not rows:
        logger.info("처리할 pending signal 없음")
        return 0

    logger.info(f"처리 대상: {len(rows)}개")
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

        score = compute_relevance_score(title, summary, full_content, source, domain=domain)
        score = min(1.0, score + compute_cluster_bonus(raw_data, domain=domain))

        # edu_consulting은 YouTube 제목만 있는 경우가 많아 임계값을 낮게 적용
        score_threshold = 0.10 if domain == "edu_consulting" else 0.15
        if score < score_threshold:
            execute_query("UPDATE raw_signals SET status = 'filtered_fail' WHERE id = %s", (raw_id,))
            failed += 1
            continue

        facts = {}
        if score >= 0.4 and facts_extracted < fact_budget:
            logger.info(f"  [{facts_extracted+1}/{fact_budget}] 팩트 추출 중 (score={score:.2f}): {title[:50]}...")
            facts = extract_facts(TIER2_LLM_MODEL, full_content if full_content else summary, logger)
            facts_extracted += 1
        elif score >= 0.4:
            logger.info(f"  팩트 추출 스킵 (backlog/배치 정책, score={score:.2f}): {title[:50]}...")

        # 카테고리 동적 분류
        category = determine_category(f"{title} {summary} {full_content}")

        save_filtered_signal(raw_id, source, title, summary, score, category, content_hash, facts, TIER2_LLM_MODEL, domain=domain)
        execute_query("UPDATE raw_signals SET status = 'filtered_pass' WHERE id = %s", (raw_id,))
        passed += 1

    logger.info(f"=== Tier 2 완료: pass={passed}, fail={failed}, facts_extracted={facts_extracted} ===")
    return passed


if __name__ == "__main__":
    filter_signals()
