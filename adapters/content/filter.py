import json
import ollama
import os
import signal
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:latest")
TIMEOUT_SECONDS = 20

# ============================================
# Tier 2a: 키워드 기반 화이트/블랙리스트
# 🤔 왜 제목만 체크?
# 요약/본문엔 키워드가 맥락 없이 언급될 수 있음.
# 제목에 있어야 그 논문의 핵심 주제임.
# ============================================

WHITELIST = [
    # 로보틱스
    "robot", "humanoid", "robot hand", "dexterous", "manipulation",
    "robotic", "robotics", "autonomous robot", "drone", "UAV", "quadrotor",
    "reinforcement learning",
    # AI / 모델
    "world model", "foundation model", "vision-language",
    "large language model", "LLM", "autonomous",
    # 반도체
    "GPU", "chip", "semiconductor", "NVIDIA", "AMD", "TSMC", "wafer",
    # 항공우주
    "satellite", "spacecraft", "rocket", "aerospace",
    # 기업 키워드
    "Tesla", "Optimus", "Figure AI", "Boston Dynamics", "OpenAI", "DeepMind",
]

BLACKLIST = [
    "education", "teacher", "student", "pedagog",
    "music", "audio", "speech",
    "medical", "clinical", "patient", "disease", "glaucoma",
    "legal", "law", "court",
    "social bias", "fairness",
    "agriculture", "crop", "farm",
    "weather", "climate",
    "jailbreak",
    "e-commerce", "ecommerce", "retail", "stock market", "financial market",
    "ocean corpus", "marine biology",
]

def keyword_filter(title: str, summary: str) -> tuple[bool, str]:
    """
    제목에서만 키워드 체크.
    블랙리스트가 화이트리스트보다 우선.
    """
    title_lower = title.lower()

    # 블랙리스트 먼저 체크
    for kw in BLACKLIST:
        if kw.lower() in title_lower:
            return False, f"blacklist:{kw}"

    # 화이트리스트 체크
    for kw in WHITELIST:
        if kw.lower() in title_lower:
            return True, f"whitelist:{kw}"

    return False, "no_keyword"

# ============================================
# Tier 2b: LLM 한국어 요약 (단순 작업만)
# 🤔 LLM에게 판단/분류는 안 시킴.
# 요약만 시켜서 불안정성 제거.
# ============================================

SUMMARY_PROMPT = """다음 영문 기술 기사 제목과 요약을 한국어로 2문장 이내로 요약하세요.
다른 말 없이 요약문만 출력하세요."""

def truncate_text(text: str, max_chars: int = 300) -> str:
    return text[:max_chars] if len(text) > max_chars else text

def generate_summary(title: str, summary: str) -> str:
    content = f"Title: {truncate_text(title, 150)}\n\n{truncate_text(summary, 300)}"

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": content}
            ],
            options={
                "temperature": 0.3,
                "num_predict": 200,
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"[요약 실패: {str(e)[:30]}]"

# ============================================
# DB 저장
# ============================================

def save_filtered_signal(raw_id, source, title, summary,
                          score, category, content_hash):
    query = """
        INSERT INTO filtered_signals
            (raw_signal_id, source, title, summary, score,
             category, content_hash, tier2_model)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
    """
    execute_query(query, (
        raw_id, source, title, summary,
        score, category, content_hash, OLLAMA_MODEL
    ))

# ============================================
# 메인 루프
# ============================================

def filter_signals():
    logger = HarnessLogger(tier=2)
    logger.info("=== Tier 2 필터링 시작 ===")
    logger.info("2a: 키워드 필터 (제목 기준) / 2b: LLM 한국어 요약")

    # 🤔 status='pending'만 처리 → 중단 후 재시작해도 이어서 처리 가능
    rows = execute_query(
        "SELECT id, source, raw_data, content_hash FROM raw_signals WHERE status = 'pending'",
        fetch=True
    )

    if not rows:
        logger.info("처리할 데이터 없음")
        return 0

    logger.info(f"처리 대상: {len(rows)}개")

    keyword_pass = 0
    keyword_fail = 0
    summary_fail = 0

    for i, row in enumerate(rows):
        raw_id = row["id"]
        raw_data = row["raw_data"]
        content_hash = row["content_hash"]
        source = row["source"]

        title = raw_data.get("title", "")
        summary = raw_data.get("summary", "")

        # === Tier 2a: 키워드 필터 ===
        passed, reason = keyword_filter(title, summary)

        if not passed:
            # 🤔 즉시 status 업데이트 → 중단돼도 재처리 안 함
            execute_query(
                "UPDATE raw_signals SET status = 'filtered_fail' WHERE id = %s",
                (raw_id,)
            )
            keyword_fail += 1
            if (i + 1) % 20 == 0:
                logger.info(f"[{i+1}/{len(rows)}] 진행 중... 키워드 통과 {keyword_pass}개")
            continue

        logger.info(f"[{i+1}/{len(rows)}] 키워드 통과 ({reason}): {title[:50]}")

        # === Tier 2b: LLM 한국어 요약 ===
        def timeout_handler(signum, frame):
            raise TimeoutError("LLM 응답 초과")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT_SECONDS)

        try:
            korean_summary = generate_summary(title, summary)
        except TimeoutError:
            logger.warning(f"  → 요약 타임아웃, 원문 사용")
            korean_summary = f"[요약 실패] {summary[:200]}"
            summary_fail += 1
        finally:
            signal.alarm(0)

        logger.info(f"  → 요약: {korean_summary[:60]}...")

        # DB 저장
        save_filtered_signal(
            raw_id, source, title, korean_summary,
            0.7, "keyword_pass", content_hash
        )
        execute_query(
            "UPDATE raw_signals SET status = 'filtered_pass' WHERE id = %s",
            (raw_id,)
        )
        keyword_pass += 1

    # 최종 리포트
    total = keyword_pass + keyword_fail
    logger.info("=" * 50)
    logger.info(f"Tier 2 완료: 통과 {keyword_pass}개 / 탈락 {keyword_fail}개")
    if summary_fail > 0:
        logger.info(f"요약 실패: {summary_fail}개 (원문으로 대체)")
    if total > 0:
        logger.info(f"탈락률: {keyword_fail/total*100:.1f}%")
    logger.info("=" * 50)

    return keyword_pass

if __name__ == "__main__":
    filter_signals()
