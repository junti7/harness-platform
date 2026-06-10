import feedparser
import hashlib
import json
import httpx
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup
from core.domain_config import load_default_sources
from core.database import execute_query
from core.logger import HarnessLogger
from core.source_registry import ACTIVE_COLLECTION_MODES, merge_catalog_rows_with_defaults, parse_rate_limit_policy
from core.topic_registry import merged_sources_with_generated

DEFAULT_RSS_SOURCES = load_default_sources("physical_ai")

_PHYSICAL_AI_CLUSTER_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("power_cooling", ("power", "grid", "cooling", "liquid cooling", "thermal", "datacenter", "data center", "rack scale")),
    ("networking_optics", ("ethernet", "infiniband", "optical", "switch", "networking", "co-packaged optics", "optical interconnect")),
    ("memory_packaging", ("hbm", "hbm3e", "hbm4", "memory", "advanced packaging", "packaging", "chiplet", "interposer", "substrate")),
    ("simulation_software", ("digital twin", "simulation", "world model", "mes", "plm", "scada", "industrial software")),
    ("warehouse_deployment", ("warehouse", "logistics", "fulfillment", "deployment", "fleet")),
    ("edge_realtime", ("edge ai", "on-device", "real-time inference", "realtime inference", "embedded ai")),
    ("embodiment_robotics", ("robot", "robotics", "humanoid", "manipulation", "locomotion", "actuator", "sensor", "factory", "automation")),
    ("compute_models", ("gpu", "semiconductor", "wafer", "foundry", "tsmc", "nvidia", "asic", "accelerator")),
]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "source"


def _substack_feed_urls() -> list[str]:
    configured = os.getenv("SUBSTACK_SOURCE_FEEDS", "").strip()
    urls: list[str] = []
    if configured:
        urls.extend([item.strip() for item in configured.split(",") if item.strip()])
    publication = os.getenv("SUBSTACK_PUBLICATION_URL", "").strip().rstrip("/")
    if publication:
        urls.append(publication)

    normalized: list[str] = []
    seen = set()
    for url in urls:
        candidate = url.rstrip("/")
        if "substack.com" not in candidate:
            continue
        if not candidate.endswith("/feed"):
            candidate = f"{candidate}/feed"
        if candidate not in seen:
            seen.add(candidate)
            normalized.append(candidate)
    return normalized


def _expand_special_sources(source: dict) -> list[dict]:
    channel = str(source.get("channel") or "").strip().lower()
    mode = str(source.get("collection_mode") or "").strip().lower()
    if channel == "substack" and mode == "rss_search":
        expanded = []
        for url in _substack_feed_urls():
            expanded.append(
                {
                    **source,
                    "name": f"substack_feed_{_slugify(url)}",
                    "url": url,
                    "source_type": "rss",
                    "channel": "substack",
                    "collection_mode": "rss_pull",
                    "expected_signal_type": "newsletter_post",
                    "notes": "Substack publication feed",
                }
            )
        return expanded
    return [source]


def infer_physical_ai_topic_cluster(*parts: str) -> str:
    haystack = " ".join(part for part in parts if part).lower()
    source_based_rules = [
        ("memory_packaging", ("google_news_hbm_packaging", "packaging", "hbm")),
        ("networking_optics", ("google_news_ai_networking", "networking", "optical")),
        ("power_cooling", ("google_news_power_cooling", "cooling", "power")),
        ("simulation_software", ("google_news_digital_twin_simulation", "digital_twin", "simulation")),
        ("warehouse_deployment", ("google_news_warehouse_logistics_robotics", "warehouse", "logistics")),
    ]
    for cluster, keywords in source_based_rules:
        if any(keyword in haystack for keyword in keywords):
            return cluster
    for cluster, keywords in _PHYSICAL_AI_CLUSTER_RULES:
        if any(keyword in haystack for keyword in keywords):
            return cluster
    return "general_physical_ai"

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
    title = entry.get("title", "")
    if title:
        import re
        normalized_title = re.sub(r'\s+', '', title).lower()
        # 이미 동일한 제목(공백/대소문자 무시)이 수집되었는지 체크하여 절대 중복 방지
        check_query = """
            SELECT 1 FROM raw_signals 
            WHERE REPLACE(LOWER(raw_data::jsonb->>'title'), ' ', '') = %s
            LIMIT 1
        """
        rows = execute_query(check_query, (normalized_title,), fetch=True)
        if rows:
            return  # 완벽히 동일한 제목의 데이터가 존재하면 중복 수집 안 함

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


def ensure_collection_poll_schema() -> None:
    """source_catalog에 poll 스냅샷 컬럼 추가(멱등). last_ingested_at(=raw_signals 파생)과 달리
    '이번에 실제 점검했는지/결과가 무엇인지'를 운영자가 구분하게 한다. best-effort."""
    for stmt in (
        "ALTER TABLE source_catalog ADD COLUMN IF NOT EXISTS last_polled_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE source_catalog ADD COLUMN IF NOT EXISTS last_poll_status VARCHAR(32)",
        "ALTER TABLE source_catalog ADD COLUMN IF NOT EXISTS last_poll_note TEXT",
    ):
        try:
            execute_query(stmt)
        except Exception:
            pass


def record_poll(source_name: str, status: str, note: str = "") -> None:
    """개별 소스의 '이번 점검 결과' 스냅샷 기록(ok/empty/failed/skipped). best-effort —
    heartbeat 기록 실패가 수집 전체를 죽이면 안 되므로 예외를 삼킨다. failure_count(연속 실패
    누적)는 collection_health_check가 따로 관리 — 역할 분리."""
    if not source_name:
        return
    try:
        execute_query(
            "UPDATE source_catalog SET last_polled_at = NOW(), last_poll_status = %s, last_poll_note = %s "
            "WHERE source_name = %s",
            (str(status)[:32], (note or "")[:500], source_name),
        )
    except Exception:
        pass

def get_active_sources(logger: HarnessLogger) -> list[dict]:
    rows = execute_query("""
        SELECT source_name, base_url, reliability_score, expected_signal_type, rate_limit_policy
             , source_type, enabled
        FROM source_catalog
    """, fetch=True)
    merged_rows = merge_catalog_rows_with_defaults(rows or [], DEFAULT_RSS_SOURCES)
    if not merged_rows:
        logger.info(f"source_catalog 비어 있음 — 기본 소스 {len(DEFAULT_RSS_SOURCES)}개 사용")
        return DEFAULT_RSS_SOURCES

    sources = []
    for row in merged_rows:
        if not bool(row.get("enabled", True)):
            continue
        policy = parse_rate_limit_policy(row.get("rate_limit_policy"))
        if str(policy.get("collection_mode") or "").strip().lower() not in ACTIVE_COLLECTION_MODES:
            continue
        candidate = {
            "name": row["source_name"],
            "url": row["base_url"],
            "stale_minutes": int(policy.get("stale_minutes", 0) or 0),
            "reliability_score": row.get("reliability_score"),
            "expected_signal_type": row.get("expected_signal_type"),
            "source_type": row.get("source_type"),
            "channel": policy.get("channel"),
            "collection_mode": policy.get("collection_mode"),
            "enabled": bool(row.get("enabled", True)),
            "preferred_worker": policy.get("preferred_worker"),
            "activation_policy": policy.get("activation_policy"),
            "requires_login": bool(policy.get("requires_login", False)),
            "notes": policy.get("notes", ""),
        }
        sources.extend(_expand_special_sources(candidate))
    logger.info(f"source_catalog+config에서 활성 수집 소스 {len(sources)}개 로드")
    return sources

def collect(correlation_id: str = None):
    logger = HarnessLogger(tier=1, correlation_id=correlation_id)
    logger.info("=== Tier 1 수집 시작 (Deep Scraping 활성화) ===")
    ensure_collection_poll_schema()
    total_saved = 0
    sources = merged_sources_with_generated("physical_ai", get_active_sources(logger))
    logger.info(f"활성 소스 총 {len(sources)}개 (자동 주제 쿼리 포함)")
    for source in sources:
        _sname = source.get("name")
        if not source.get("url"):
            record_poll(_sname, "skipped", "no url")
            continue
        if not check_liveness(source["url"]):
            record_poll(_sname, "failed", "liveness check failed (non-200/timeout)")
            continue

        if source.get("source_type") == "open_api" and source.get("channel") == "data_go_kr":
            api_key = os.getenv("DATA_GO_KR_API_KEY", "data-portal-test-key")
            headers = {"Authorization": f"Infuser {api_key}"}
            target_keywords = [
                "ai", "인공지능", "로봇", "robot", "로보틱스", "agi", "자율주행", "자율비행",
                "반도체", "gpu", "hbm", "패키징", "네트워킹", "광통신",
                "전력", "냉각", "데이터센터", "디지털트윈", "시뮬레이션",
                "물류", "창고", "자동화", "제조", "factory", "warehouse", "logistics",
                "부동산", "경매", "재건축", "재개발", "공매", "상권", "토지", "주택"
            ]
            low_signal_terms = ["민원", "공원", "관광", "복지"]
            _saved_here = 0
            try:
                base_host = "https://api.odcloud.kr/api/15077093/v1"
                endpoints = ["/dataset", "/open-data-list"]
                
                for ep in endpoints:
                    for page in range(1, 11):
                        url_with_page = f"{base_host}{ep}?page={page}&perPage=100"
                        resp = httpx.get(url_with_page, headers=headers, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            items = data.get("data", [])
                            if not items:
                                break

                            for item in items:
                                if ep == "/open-data-list":
                                    if str(item.get("api_type", "")).upper() != "REST":
                                        continue

                                title = item.get("title", "")
                                desc = item.get("desc", "")
                                
                                text_to_check = f"{title} {desc}".lower()
                                if not any(kw in text_to_check for kw in target_keywords):
                                    continue
                                if any(term in text_to_check for term in low_signal_terms):
                                    continue

                                url = item.get("page_url", "")
                                if not url:
                                    data_id = item.get("list_id") or item.get("id", "")
                                    if ep == "/open-data-list":
                                        url = f"https://www.data.go.kr/data/{data_id}/openapi.do"
                                    else:
                                        url = f"https://www.data.go.kr/data/{data_id}/fileData.do"
                                        
                                content_hash = hashlib.sha256(f"{title}{url}".encode()).hexdigest()[:64]
                                raw_data = {
                                    "title": title,
                                    "url": url,
                                    "summary": desc,
                                    "source_name": source["name"],
                                    "domain": "physical_ai",
                                    "topic_cluster": infer_physical_ai_topic_cluster(title, desc, source["name"], url),
                                }
                                save_raw_signal(source["name"], raw_data, content_hash, desc)
                                total_saved += 1
                                _saved_here += 1
                record_poll(_sname, "ok" if _saved_here > 0 else "empty", f"data.go.kr saved={_saved_here}")
            except Exception as e:
                record_poll(_sname, "failed", f"data_go_kr: {str(e)[:200]}")
                logger.warning(f"data_go_kr API 수집 실패: {e}")
            continue

        # Default RSS fallback
        try:
            feed = feedparser.parse(source["url"])
            _n_entries = len(feed.entries)
            _saved_rss = 0
            for entry in feed.entries:
                title = entry.get("title", "")
                url = entry.get("link", "")
                content_hash = hashlib.sha256(f"{title}{url}".encode()).hexdigest()[:64]
                full_text = deep_fetch_content(url, logger)
                summary = entry.get("summary", "")
                raw_data = {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source_name": source["name"],
                    "domain": "physical_ai",
                    "topic_cluster": infer_physical_ai_topic_cluster(title, summary, source["name"], url),
                }
                save_raw_signal(source["name"], raw_data, content_hash, full_text)
                total_saved += 1
                _saved_rss += 1
            # entries 0 = 피드는 정상 점검됐으나 신규 없음(empty) — '죽음'과 구분되는 핵심 신호
            record_poll(_sname, "empty" if _n_entries == 0 else "ok", f"entries={_n_entries}, saved={_saved_rss}")
        except Exception as e:
            record_poll(_sname, "failed", f"rss: {str(e)[:200]}")
            logger.warning(f"RSS 수집 실패 [{_sname}]: {e}")
    logger.info(f"=== Tier 1 완료: {total_saved}개 저장 ===")
    return total_saved

if __name__ == "__main__": collect()
