import json
import ollama
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dotenv import load_dotenv
from core.domain_config import load_keyword_list
from core.database import execute_query
from core.logger import HarnessLogger

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:latest")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))
TIER2_BATCH_LIMIT = int(os.getenv("TIER2_BATCH_LIMIT", "20"))
MAX_FACT_EXTRACTION_PER_BATCH = 5

HIGH_VALUE_KEYWORDS = load_keyword_list("physical_ai")

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


def compute_relevance_score(title: str, summary: str, full_content: str) -> float:
    text = f"{title} {summary} {full_content[:2000]}".lower()

    # 저품질 패턴 즉시 탈락
    for pattern in LOW_VALUE_PATTERNS:
        if re.search(pattern, text):
            return 0.0

    # 키워드 매칭으로 relevance 계산
    hits = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in text)
    score = min(1.0, hits * 0.08)  # 키워드 1개 = 0.08, 13개 이상이면 1.0

    # 최소값 보장 (Physical AI 도메인 외 일반 tech 뉴스도 최소값 유지)
    return max(0.1, score)


def _ollama_call(text: str) -> dict:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": FACT_EXTRACTION_PROMPT + text[:3000]}],
        options={"temperature": 0.0, "format": "json"},
    )
    return json.loads(response["message"]["content"])


def extract_facts(text: str, logger: HarnessLogger) -> dict:
    if not text or len(text) < 100:
        return {}

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_ollama_call, text)
            return future.result(timeout=OLLAMA_TIMEOUT_SECONDS)
    except FuturesTimeoutError:
        logger.warning(f"Ollama timeout ({OLLAMA_TIMEOUT_SECONDS}s) — 팩트 추출 건너뜀")
        return {}
    except (json.JSONDecodeError, KeyError):
        return {}
    except Exception as e:
        logger.warning(f"Ollama 호출 실패: {type(e).__name__}: {e}")
        return {}


def save_filtered_signal(raw_id, source, title, summary, score, category, content_hash, facts):
    execute_query("""
        INSERT INTO filtered_signals
            (raw_signal_id, source, title, summary, score, category, content_hash, tier2_model, extracted_facts)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
    """, (raw_id, source, title, summary, score, category, content_hash, OLLAMA_MODEL, json.dumps(facts)))


def filter_signals(correlation_id: str = None):
    logger = HarnessLogger(tier=2, correlation_id=correlation_id)
    logger.info(f"=== Tier 2 필터링 시작 (batch={TIER2_BATCH_LIMIT}, model={OLLAMA_MODEL}) ===")

    rows = execute_query(
        "SELECT id, source, raw_data, content_hash, full_content FROM raw_signals WHERE status = 'pending' LIMIT %s",
        (TIER2_BATCH_LIMIT,),
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

        score = compute_relevance_score(title, summary, full_content)

        if score < 0.15:
            execute_query("UPDATE raw_signals SET status = 'filtered_fail' WHERE id = %s", (raw_id,))
            failed += 1
            continue

        # 점수가 0.4 이상인 고가치 신호만 Ollama 팩트 추출 (비용·시간 절감)
        # 배당 최대 추출 개수 제한 (Stuck 방지)
        facts = {}
        if score >= 0.4 and facts_extracted < MAX_FACT_EXTRACTION_PER_BATCH:
            logger.info(f"  [{facts_extracted+1}/{MAX_FACT_EXTRACTION_PER_BATCH}] 팩트 추출 중 (score={score:.2f}): {title[:50]}...")
            facts = extract_facts(full_content if full_content else summary, logger)
            facts_extracted += 1
        elif score >= 0.4:
            logger.info(f"  팩트 추출 스킵 (배치 한도 초과, score={score:.2f}): {title[:50]}...")

        save_filtered_signal(raw_id, source, title, summary, score, "physical_ai", content_hash, facts)
        execute_query("UPDATE raw_signals SET status = 'filtered_pass' WHERE id = %s", (raw_id,))
        passed += 1

    logger.info(f"=== Tier 2 완료: pass={passed}, fail={failed}, facts_extracted={facts_extracted} ===")
    return passed


if __name__ == "__main__":
    filter_signals()
