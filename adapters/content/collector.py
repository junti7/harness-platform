import feedparser
import hashlib
import json
import httpx
from datetime import datetime
from core.database import execute_query
from core.logger import HarnessLogger

RSS_SOURCES = [
    # ── 학술 논문 (arXiv) ─────────────────────────────────────
    {
        "name": "arXiv_robotics",
        "url": "https://rss.arxiv.org/rss/cs.RO",
        "stale_minutes": 7 * 24 * 60,
    },
    {
        "name": "arXiv_AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "stale_minutes": 7 * 24 * 60,
    },
    {
        "name": "arXiv_ML",
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "stale_minutes": 7 * 24 * 60,  # RL 논문 상당수가 cs.LG에 분류됨
    },
    # ── 테크 미디어 ───────────────────────────────────────────
    {
        "name": "IEEE_Spectrum",
        "url": "https://spectrum.ieee.org/feeds/feed.rss",
        "stale_minutes": 3 * 24 * 60,
    },
    {
        "name": "MIT_Tech_Review",
        "url": "https://www.technologyreview.com/feed/",
        "stale_minutes": 2 * 24 * 60,
    },
    {
        "name": "TechCrunch_robotics",
        "url": "https://techcrunch.com/tag/robotics/feed/",
        "stale_minutes": 3 * 24 * 60,
    },
    # ── 기업 블로그 ───────────────────────────────────────────
    {
        "name": "Boston_Dynamics",
        "url": "https://feeds.feedburner.com/BostonDynamics",
        "stale_minutes": 30 * 24 * 60,  # 블로그 포스팅 주기 느림
    },
    # Figure AI, Tesla: 공식 RSS 없음 → 미지원
]

def check_liveness(url: str) -> bool:
    """
    PLATFORM.md 5.1 Liveness Probe.
    🤔 왜 301도 통과? 리다이렉트는 정상 동작.
    원래 코드는 200만 통과시켜서 IEEE가 탈락했음.
    """
    try:
        response = httpx.get(url, timeout=10, follow_redirects=True)
        return response.status_code == 200
    except Exception:
        return False

def make_content_hash(title: str, url: str) -> str:
    """PLATFORM.md 5.4 Idempotency — 중복 수집 방지"""
    raw = f"{title}{url}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:64]

def is_stale(published_date, stale_minutes: int) -> bool:
    """
    PLATFORM.md 5.2 Stale Data Guard.
    🤔 왜 소스별 stale_minutes?
    뉴스(2일)와 학술논문(7일)의 가치 유효기간이 달라요.
    """
    if not published_date:
        return False  # 날짜 없으면 일단 통과
    try:
        from time import mktime
        pub_time = datetime.fromtimestamp(mktime(published_date))
        diff = (datetime.now() - pub_time).total_seconds() / 60
        return diff > stale_minutes
    except Exception:
        return False

def save_raw_signal(source: str, entry: dict, content_hash: str):
    """Tier 1 결과물을 raw_signals에 저장"""
    query = """
        INSERT INTO raw_signals (source, raw_data, content_hash, status)
        VALUES (%s, %s, %s, 'pending')
        ON CONFLICT (content_hash) DO NOTHING
    """
    execute_query(query, (source, json.dumps(entry), content_hash))

def collect(correlation_id: str = None):
    """Tier 1 메인 수집 함수"""
    logger = HarnessLogger(tier=1, correlation_id=correlation_id)
    logger.info("=== Tier 1 수집 시작 ===")

    total_saved = 0
    total_skipped = 0

    for source in RSS_SOURCES:
        logger.info(f"소스 처리 중: {source['name']}")

        if not check_liveness(source["url"]):
            logger.warning(f"Liveness 실패, 스킵: {source['name']}")
            continue

        feed = feedparser.parse(source["url"])
        logger.info(f"{source['name']}: {len(feed.entries)}개 항목 발견")

        for entry in feed.entries:
            title = entry.get("title", "")
            url = entry.get("link", "")
            published = entry.get("published_parsed")

            # 소스별 stale_minutes 적용
            if is_stale(published, source["stale_minutes"]):
                total_skipped += 1
                continue

            content_hash = make_content_hash(title, url)

            raw_data = {
                "title": title,
                "url": url,
                "summary": entry.get("summary", ""),
                "published": str(published),
                "source_name": source["name"]
            }

            save_raw_signal(source["name"], raw_data, content_hash)
            total_saved += 1

    logger.info(f"=== Tier 1 완료: 저장 {total_saved}개, 스킵 {total_skipped}개 ===")
    return total_saved

if __name__ == "__main__":
    collect()
