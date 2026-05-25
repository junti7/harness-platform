"""
교육 컨설팅 DEEP RESEARCH 수집기 — Tier 1

사용법:
  .venv/bin/python scripts/run_edu_deep_research.py
  .venv/bin/python scripts/run_edu_deep_research.py --dry-run
  .venv/bin/python scripts/run_edu_deep_research.py --sources rss
  .venv/bin/python scripts/run_edu_deep_research.py --sources rss,scholar,arxiv,youtube

AR-026 | correlation_id: edu-consulting-20260524
legal_review_approve: 완료 (저위험 채널 — docs/reports/legal/edu_data_collection_legal_review_2026-05-24.md)
red_team_clear: 완료 (AR-029)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import feedparser
import httpx

from core.database import execute_query, get_connection
from core.domain_config import load_default_sources
from core.logger import HarnessLogger

DOMAIN = "edu_consulting"
CORRELATION_ID = "edu-consulting-20260524"

# YouTube 추출 출력 디렉토리
YT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "edu_research" / "yt"
YT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# yt-dlp 실행 경로
# yt-dlp 실행 경로 (Mac Mini: .venv/bin, MBP: /opt/homebrew/bin)
_VENV_YT_DLP = str(Path(__file__).resolve().parent.parent / ".venv" / "bin" / "yt-dlp")
_BREW_YT_DLP = "/opt/homebrew/bin/yt-dlp"
YT_DLP_BIN = _VENV_YT_DLP if Path(_VENV_YT_DLP).exists() else _BREW_YT_DLP


# ---------------------------------------------------------------------------
# 스키마 확인 — raw_signals에 domain 컬럼이 없으면 추가
# ---------------------------------------------------------------------------

def ensure_domain_column(logger: HarnessLogger):
    try:
        execute_query(
            "ALTER TABLE raw_signals ADD COLUMN IF NOT EXISTS domain VARCHAR(64) DEFAULT 'physical_ai'"
        )
        execute_query(
            "CREATE INDEX IF NOT EXISTS idx_raw_signals_domain ON raw_signals(domain)"
        )
        logger.info("raw_signals.domain 컬럼 확인 완료")
    except Exception as e:
        logger.warning(f"domain 컬럼 마이그레이션 실패 (이미 존재하거나 권한 없음): {e}")


# ---------------------------------------------------------------------------
# 공통 저장
# ---------------------------------------------------------------------------

def save_signal(source_name: str, raw_data: dict, domain: str, logger: HarnessLogger) -> bool:
    """중복 제거 후 raw_signals에 저장. 새 항목이면 True 반환."""
    key = f"{raw_data.get('title', '')}{raw_data.get('url', raw_data.get('query', ''))}"
    content_hash = hashlib.sha256(key.encode()).hexdigest()[:64]
    raw_data["domain"] = domain
    raw_data["collected_at"] = datetime.now(timezone.utc).isoformat()

    try:
        execute_query(
            """
            INSERT INTO raw_signals (source, raw_data, content_hash, full_content, status, domain)
            VALUES (%s, %s, %s, %s, 'pending', %s)
            ON CONFLICT (content_hash) DO NOTHING
            """,
            (source_name, json.dumps(raw_data, ensure_ascii=False), content_hash,
             raw_data.get("full_content", ""), domain),
        )
        return True
    except Exception:
        # domain 컬럼 없는 구버전 스키마 fallback
        try:
            execute_query(
                """
                INSERT INTO raw_signals (source, raw_data, content_hash, full_content, status)
                VALUES (%s, %s, %s, %s, 'pending')
                ON CONFLICT (content_hash) DO NOTHING
                """,
                (source_name, json.dumps(raw_data, ensure_ascii=False), content_hash,
                 raw_data.get("full_content", "")),
            )
            return True
        except Exception as e2:
            logger.warning(f"저장 실패 ({source_name}): {e2}")
            return False


# ---------------------------------------------------------------------------
# 포화도(saturation) 트래킹
# ---------------------------------------------------------------------------

class SaturationTracker:
    """연속 3회 신규 비율 < 5% → 해당 소스 포화 선언."""

    def __init__(self):
        self._runs: dict[str, list[float]] = {}

    def record(self, source: str, new_count: int, total_count: int):
        if total_count == 0:
            return
        ratio = new_count / total_count
        self._runs.setdefault(source, []).append(ratio)

    def is_saturated(self, source: str) -> bool:
        runs = self._runs.get(source, [])
        if len(runs) < 3:
            return False
        return all(r < 0.05 for r in runs[-3:])

    def summary(self) -> dict:
        return {src: {"runs": runs, "saturated": self.is_saturated(src)}
                for src, runs in self._runs.items()}


# ---------------------------------------------------------------------------
# RSS 수집
# ---------------------------------------------------------------------------

def collect_rss(sources: list[dict], logger: HarnessLogger,
                tracker: SaturationTracker, dry_run: bool) -> dict:
    rss_sources = [s for s in sources
                   if s.get("type") in ("rss",) and s.get("legal_risk", "low") != "high"]
    stats = {"attempted": len(rss_sources), "new": 0, "duplicate": 0, "error": 0}

    for src in rss_sources:
        name = src["name"]
        url = src["url"]
        logger.info(f"RSS 수집: {name} ({url})")
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                logger.warning(f"  entries 없음 — URL 검증 필요: {url}")
                stats["error"] += 1
                continue

            src_new = 0
            for entry in feed.entries:
                raw = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:2000],
                    "source_name": name,
                    "signal_class": src.get("signal_class", "unknown"),
                    "rq_tags": src.get("rq_tags", []),
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    src_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal(name, raw, DOMAIN, logger)
                    if saved:
                        src_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(name, src_new, len(feed.entries))
            logger.info(f"  완료: {src_new}개 신규 / {len(feed.entries)}개 전체")

        except Exception as e:
            logger.warning(f"  RSS 실패 ({name}): {e}")
            stats["error"] += 1

        time.sleep(1)  # rate limiting

    return stats


# ---------------------------------------------------------------------------
# Semantic Scholar API
# ---------------------------------------------------------------------------

SCHOLAR_QUERIES = [
    # English
    "AI literacy cognitive offloading students",
    "generative AI student learning critical thinking",
    "metacognition AI dependence children education",
    "AI homework help academic achievement",
    "digital literacy parents children",
    "AI replacement anxiety jobs labor",
    "automation anxiety workplace psychological distress",
    "generative AI parental anxiety children",
    "AI educational technology home learning impact",
    "algorithmic replacement white collar jobs anxiety",
    "coping strategies AI workplace disruption",
    "teacher perception generative AI classrooms",
    "critical thinking skills AI age education",
    "AI skill bubble workforce exaggerating skills",
    "student dependence on ChatGPT learning loss",
    "k-12 AI safety guidelines parental concern",
    "job displacement fears artificial intelligence",
    "psychological impact of AI on workers",
    "educational inequality AI access digital divide",
    "AI tutoring systems parent engagement",
    # Spanish
    "ansiedad padres educacion IA",
    "IA reemplazo trabajo ansiedad trabajadores",
    "dependencia cognitiva inteligencia artificial educacion",
    "ansiedad automatizacion laboral psicologia",
    # French
    "anxiete parents education IA",
    "IA remplacement travail anxiete salaries",
    "decharge cognitive dependance intelligence artificielle",
    "anxiete automatisation travail psychologique",
    # German
    "Eltern Angst KI Bildung",
    "KI ersetzt Arbeitsplaetze Angst Mitarbeiter",
    "kognitive Entlastung KI Abhaengigkeit",
    "Angst vor Automatisierung Arbeitsplatz",
    # Japanese
    "AI教育 親の不安",
    "AI仕事代替 労働者の不安",
    "認知的外注 AI依存 教育",
    "雇用代替 不安 人工知能",
    # Chinese
    "AI教育 家长焦虑",
    "人工智能替代工作 员工焦虑",
    "认知外包 AI依赖 教育",
    "自动化焦虑 职场心理",
    # Portuguese
    "ansiedade pais educacao IA",
    "IA substituindo empregos ansiedade trabalhadores",
    "dependencia cognitiva inteligencia artificial",
    "ansiedade automacao trabalho psicologia",
    # Italian
    "ansia genitori educazione IA",
    "IA sostituzione lavoro ansia dipendenti",
    "dipendenza cognitiva intelligenza artificiale",
    # Russian
    "trevoga roditeley II obrazovanie",
    "II zamena raboty trevoga sotrudnikov",
    "kognitivnaya zavisimost iskusstvennyy intellekt",
    # Arabic (UAE & Global)
    "قلق أولياء الأمور التعليم الذكاء الاصطناعي",
    "الذكاء الاصطناعي استبدال الوظائف قلق الموظفين",
    "الذكاء الاصطناعي في التعليم دبي أبوظبي",
    "تأثير الأتمتة على الوظائف في الإمارات",
    "qalaq al-abaa al-talim al-dhakaa al-istinai",
    "al-dhakaa al-istinai istibdal al-wazaif qalaq",
    # Hebrew (Israel)
    "חרדת הורים חינוך בינה מלאכותית",
    "בינה מלאכותית החלפת משרות חרדת עובדים",
    "אוטומציה במקום העבודה חרדה",
    "בינה מלאכותית במערכת החינוך ישראל",
    # Hindi
    "AI shiksha mata-pita ki chinta",
    "AI naukri pratisthapan karmachariyon ki chinta",
    # Indonesian
    "kecemasan orang tua pendidikan AI",
    "AI menggantikan pekerjaan kecemasan karyawan",
    # Turkish
    "yapay zeka egitim veli kaygisi",
    "yapay zeka is kaybi calisan kaygisi",
    # Vietnamese
    "lo lang cha me giao duc AI",
    "AI thay the cong viec lo lang nhan vien",
    # Dutch
    "angst ouders AI onderwijs",
    "AI vervanging banen angst werknemers",
    # Polish
    "lek rodzicow edukacja AI",
    "AI zastepowanie pracy lek pracownikow",
    # Swedish
    "oro foraldrar AI utbildning",
    "AI ersatter jobb oro anstallda",
    # Korean
    "AI 교육 학부모 불안",
    "AI 일자리 대체 직장인 불안",
]

def collect_semantic_scholar(logger: HarnessLogger, tracker: SaturationTracker,
                             dry_run: bool) -> dict:
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "paperId,title,abstract,year,authors,externalIds,url"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    # API key 있으면 사용 (없으면 익명 — rate limit 낮음)
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"User-Agent": "Harness-EduResearch/1.0 (research only; contact junti7@gmail.com)"}
    if api_key:
        headers["x-api-key"] = api_key

    for query in SCHOLAR_QUERIES:
        logger.info(f"Semantic Scholar: {query}")
        # 지수 백오프 재시도 (429 대응)
        resp = None
        for attempt in range(3):
            try:
                resp = httpx.get(
                    endpoint,
                    params={"query": query, "fields": fields, "limit": 20},
                    timeout=20,
                    headers=headers,
                )
                if resp.status_code == 429:
                    wait = 10 * (2 ** attempt)
                    logger.warning(f"  HTTP 429 — {wait}s 대기 후 재시도 (attempt {attempt+1}/3)")
                    time.sleep(wait)
                    continue
                break
            except Exception as e:
                logger.warning(f"  요청 실패 (attempt {attempt+1}): {e}")
                time.sleep(5)

        if resp is None or resp.status_code != 200:
            logger.warning(f"  최종 실패 — HTTP {resp.status_code if resp else 'N/A'} ({query}). SEMANTIC_SCHOLAR_API_KEY 설정 권장.")
            stats["error"] += 1
            time.sleep(5)
            continue

        try:
            data = resp.json()
            papers = data.get("data", [])
            src_new = 0
            for paper in papers:
                raw = {
                    "title": paper.get("title", ""),
                    "url": paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId','')}",
                    "abstract": (paper.get("abstract") or "")[:3000],
                    "year": paper.get("year"),
                    "source_name": "semantic_scholar",
                    "signal_class": "academic",
                    "rq_tags": ["RQ2", "RQ5"],
                    "query": query,
                    "evidence_posture": "academic",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]} ({raw['year']})")
                    src_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("semantic_scholar", raw, DOMAIN, logger)
                    if saved:
                        src_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"scholar_{query[:30]}", src_new, len(papers))
            logger.info(f"  완료: {src_new}개 신규 / {len(papers)}개 전체")

        except Exception as e:
            logger.warning(f"  Semantic Scholar 파싱 실패 ({query}): {e}")
            stats["error"] += 1

        time.sleep(3)  # Scholar API rate limit

    return stats


# ---------------------------------------------------------------------------
# arXiv API
# ---------------------------------------------------------------------------

ARXIV_QUERIES = [
    "ti:AI+literacy+education",
    "ti:generative+AI+learning",
    "abs:cognitive+offloading+artificial+intelligence",
    "abs:AI+dependence+critical+thinking",
    "ti:AI+replacement+anxiety",
    "abs:job+displacement+artificial+intelligence",
    "abs:generative+AI+student+anxiety",
    "ti:workplace+automation+psychological",
    "abs:teacher+perception+generative+AI",
    "abs:parental+perception+AI+education",
]

def collect_arxiv(logger: HarnessLogger, tracker: SaturationTracker,
                  dry_run: bool) -> dict:
    endpoint = "https://export.arxiv.org/api/query"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    for query in ARXIV_QUERIES:
        logger.info(f"arXiv API: {query}")
        try:
            resp = httpx.get(
                endpoint,
                params={"search_query": query, "max_results": 20, "sortBy": "relevance"},
                timeout=30,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                logger.warning(f"  HTTP {resp.status_code}")
                stats["error"] += 1
                time.sleep(2)
                continue

            # arXiv returns Atom XML — parse with feedparser
            feed = feedparser.parse(resp.text)
            src_new = 0
            for entry in feed.entries:
                raw = {
                    "title": entry.get("title", "").replace("\n", " ").strip(),
                    "url": entry.get("link", ""),
                    "abstract": entry.get("summary", "")[:3000],
                    "published": entry.get("published", ""),
                    "source_name": "arxiv_api",
                    "signal_class": "academic",
                    "rq_tags": ["RQ2", "RQ5"],
                    "query": query,
                    "evidence_posture": "academic",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    src_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("arxiv_api", raw, DOMAIN, logger)
                    if saved:
                        src_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"arxiv_{query[:30]}", src_new, len(feed.entries))
            logger.info(f"  완료: {src_new}개 신규 / {len(feed.entries)}개 전체")

        except Exception as e:
            logger.warning(f"  arXiv 실패 ({query}): {e}")
            stats["error"] += 1

        time.sleep(3)

    return stats


# ---------------------------------------------------------------------------
# YouTube yt-dlp 자막 추출
# ---------------------------------------------------------------------------

def collect_youtube(yt_targets: list[dict], logger: HarnessLogger,
                    tracker: SaturationTracker, dry_run: bool) -> dict:
    if not Path(YT_DLP_BIN).exists():
        logger.warning(f"yt-dlp 없음: {YT_DLP_BIN}. YouTube 수집 건너뜀.")
        return {"attempted": 0, "new": 0, "error": 1}

    stats = {"attempted": len(yt_targets), "new": 0, "error": 0}

    for ch in yt_targets:
        name = ch["name"]
        url = ch["url"]
        out_dir = YT_OUTPUT_DIR / name.replace(" ", "_")
        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"YouTube 자막 추출: {name} ({url})")

        if dry_run:
            logger.info(f"  [dry-run] yt-dlp --simulate {url}")
            stats["new"] += 1
            continue

        cmd = [
            YT_DLP_BIN,
            "--skip-download",           # 영상 다운로드 금지 (legal_review_approve 조건)
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "ko,en",
            "--write-info-json",
            "--playlist-end", "10",      # 최근 10개만 (초기 스윕)
            "--quiet",
            "--no-warnings",
            "-o", str(out_dir / "%(id)s.%(ext)s"),
            url,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.warning(f"  yt-dlp 오류 ({name}): {result.stderr[:200]}")
                stats["error"] += 1
                continue

            # 생성된 .info.json 파일들을 raw_signals에 저장
            info_files = list(out_dir.glob("*.info.json"))
            ch_new = 0
            for info_path in info_files:
                try:
                    info = json.loads(info_path.read_text(encoding="utf-8"))
                    raw = {
                        "title": info.get("title", ""),
                        "url": f"https://www.youtube.com/watch?v={info.get('id', '')}",
                        "description": (info.get("description") or "")[:2000],
                        "channel": info.get("channel", name),
                        "upload_date": info.get("upload_date", ""),
                        "view_count": info.get("view_count"),
                        "source_name": f"youtube_{name.replace(' ', '_')}",
                        "signal_class": "youtube",
                        "rq_tags": ch.get("rq_tags", []),
                        "evidence_posture": "media",
                    }
                    # 자막 파일이 있으면 첨부
                    vid_id = info.get("id", "")
                    for sub_ext in ("ko.vtt", "en.vtt", "ko.srv3", "en.srv3"):
                        sub_path = out_dir / f"{vid_id}.{sub_ext}"
                        if sub_path.exists():
                            raw["subtitle_path"] = str(sub_path)
                            raw["full_content"] = sub_path.read_text(encoding="utf-8", errors="ignore")[:10000]
                            break

                    saved = save_signal(f"youtube_{name.replace(' ', '_')}", raw, DOMAIN, logger)
                    if saved:
                        ch_new += 1
                        stats["new"] += 1

                except Exception as e:
                    logger.warning(f"  info.json 파싱 실패 ({info_path.name}): {e}")

            tracker.record(f"youtube_{name[:30]}", ch_new, len(info_files))
            logger.info(f"  완료: {ch_new}개 신규 / {len(info_files)}개 info.json")

        except subprocess.TimeoutExpired:
            logger.warning(f"  yt-dlp 타임아웃 ({name})")
            stats["error"] += 1

        time.sleep(5)  # YouTube rate limit

    return stats


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="교육 컨설팅 DEEP RESEARCH 수집기")
    parser.add_argument(
        "--sources",
        default="rss,scholar,arxiv",
        help="수집 소스 (쉼표 구분): rss,scholar,arxiv,youtube (기본: rss,scholar,arxiv)",
    )
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 수집 예상 항목만 출력")
    parser.add_argument("--domain", default=DOMAIN, help="도메인 태그 (기본: edu_consulting)")
    parser.add_argument("--extra-query", default="", help="추가 연구 주제 쿼리 (scholar + arXiv 앞에 삽입)")
    args = parser.parse_args()

    enabled = {s.strip() for s in args.sources.split(",")}
    domain = args.domain
    dry_run = args.dry_run

    # 추가 쿼리를 각 소스 쿼리 목록 앞에 삽입
    if args.extra_query:
        SCHOLAR_QUERIES.insert(0, args.extra_query)
        arxiv_q = "abs:" + args.extra_query.replace(" ", "+")
        ARXIV_QUERIES.insert(0, arxiv_q)

    logger = HarnessLogger(tier=1, correlation_id=CORRELATION_ID)
    logger.info(f"=== 교육 DEEP RESEARCH 수집 시작 | domain={domain} | sources={args.sources} | dry_run={dry_run} | extra_query={args.extra_query!r} ===")

    if not dry_run:
        ensure_domain_column(logger)

    # 소스 레지스트리 로드
    sources = load_default_sources("edu_consulting")
    yt_config = json.loads(
        (Path(__file__).resolve().parent.parent / "configs" / "sources" / "edu_consulting.json")
        .read_text(encoding="utf-8")
    ).get("youtube_targets", {})
    yt_targets = yt_config.get("channels", [])

    tracker = SaturationTracker()
    total_new = 0
    results = {}

    if "rss" in enabled:
        logger.info("--- [RSS 수집] ---")
        r = collect_rss(sources, logger, tracker, dry_run)
        results["rss"] = r
        total_new += r["new"]

    if "scholar" in enabled:
        logger.info("--- [Semantic Scholar API] ---")
        r = collect_semantic_scholar(logger, tracker, dry_run)
        results["scholar"] = r
        total_new += r["new"]

    if "arxiv" in enabled:
        logger.info("--- [arXiv API] ---")
        r = collect_arxiv(logger, tracker, dry_run)
        results["arxiv"] = r
        total_new += r["new"]

    if "youtube" in enabled:
        logger.info("--- [YouTube yt-dlp] ---")
        r = collect_youtube(yt_targets, logger, tracker, dry_run)
        results["youtube"] = r
        total_new += r["new"]

    # 포화도 리포트
    saturation = tracker.summary()
    saturated = [src for src, info in saturation.items() if info["saturated"]]
    if saturated:
        logger.info(f"포화 소스 (신규율 < 5% × 3회): {saturated}")

    # 최종 요약
    logger.info("=== 수집 완료 ===")
    logger.info(f"총 신규 항목: {total_new}개")
    for src_type, stat in results.items():
        logger.info(f"  {src_type}: {stat}")

    if dry_run:
        logger.info("[dry-run 모드] DB에 저장되지 않았습니다.")

    return total_new


if __name__ == "__main__":
    main()
