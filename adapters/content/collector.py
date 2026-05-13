import feedparser
import hashlib
import json
import httpx
from datetime import datetime
from bs4 import BeautifulSoup
from core.domain_config import load_default_sources
from core.database import execute_query
from core.logger import HarnessLogger

DEFAULT_RSS_SOURCES = load_default_sources("physical_ai")

def deep_fetch_content(url: str, logger: HarnessLogger) -> str:
    """기사 URL로부터 본문 전문을 스크래핑한다."""
    try:
        response = httpx.get(url, timeout=20, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "lxml")
        if "arxiv.org" in url:
            abstract = soup.find("blockquote", class_="abstract")
            return abstract.get_text(strip=True) if abstract else ""
        
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 50])
        return content[:15000]
    except Exception as e:
        logger.warning(f"Deep fetch 실패 ({url}): {e}")
        return ""

def save_raw_signal(source: str, entry: dict, content_hash: str, full_content: str = ""):
    query = """
        INSERT INTO raw_signals (source, raw_data, content_hash, full_content, status)
        VALUES (%s, %s, %s, %s, 'pending')
        ON CONFLICT (content_hash) DO NOTHING
    """
    execute_query(query, (source, json.dumps(entry), content_hash, full_content))

def check_liveness(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=10, follow_redirects=True)
        return response.status_code == 200
    except Exception:
        return False

def get_active_sources(logger: HarnessLogger) -> list[dict]:
    rows = execute_query("""
        SELECT source_name, base_url, reliability_score, expected_signal_type, rate_limit_policy
        FROM source_catalog WHERE enabled = TRUE AND source_type = 'rss'
    """, fetch=True)
    if not rows:
        logger.info(f"source_catalog 비어 있음 — 기본 소스 {len(DEFAULT_RSS_SOURCES)}개 사용")
        return DEFAULT_RSS_SOURCES

    sources = []
    for row in rows:
        policy = row.get("rate_limit_policy") or {}
        if isinstance(policy, str):
            try:
                policy = json.loads(policy)
            except json.JSONDecodeError:
                policy = {}
        sources.append({
            "name": row["source_name"],
            "url": row["base_url"],
            "stale_minutes": int(policy.get("stale_minutes", 0) or 0),
            "reliability_score": row.get("reliability_score"),
            "expected_signal_type": row.get("expected_signal_type"),
        })
    logger.info(f"source_catalog에서 활성 RSS 소스 {len(sources)}개 로드")
    return sources

def collect(correlation_id: str = None):
    logger = HarnessLogger(tier=1, correlation_id=correlation_id)
    logger.info("=== Tier 1 수집 시작 (Deep Scraping 활성화) ===")
    total_saved = 0
    sources = get_active_sources(logger)
    for source in sources:
        if not check_liveness(source["url"]): continue
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            title = entry.get("title", "")
            url = entry.get("link", "")
            content_hash = hashlib.sha256(f"{title}{url}".encode()).hexdigest()[:64]
            full_text = deep_fetch_content(url, logger)
            raw_data = {"title": title, "url": url, "summary": entry.get("summary", ""), "source_name": source["name"]}
            save_raw_signal(source["name"], raw_data, content_hash, full_text)
            total_saved += 1
    logger.info(f"=== Tier 1 완료: {total_saved}개 저장 ===")
    return total_saved

if __name__ == "__main__": collect()
