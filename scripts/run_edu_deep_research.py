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
import re
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
                tracker: SaturationTracker, dry_run: bool,
                max_rss_items: int = 50) -> dict:
    rss_sources = [s for s in sources
                   if s.get("type") in ("rss",)
                   and s.get("legal_risk", "low") != "high"
                   and s.get("active", True)]
    stats = {"attempted": len(rss_sources), "new": 0, "duplicate": 0, "error": 0}

    for src in rss_sources:
        name = src["name"]
        url = src["url"]
        cap = src.get("max_items", max_rss_items)
        logger.info(f"RSS 수집: {name} ({url}) [최대 {cap}개]")
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                logger.warning(f"  entries 없음 — URL 검증 필요: {url}")
                stats["error"] += 1
                continue

            entries = feed.entries[:cap]
            src_new = 0
            for entry in entries:
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

            total = len(feed.entries)
            tracker.record(name, src_new, len(entries))
            logger.info(f"  완료: {src_new}개 신규 / {len(entries)}개 처리 (전체 {total}개)")

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

# en_only 모드: 영어 핵심 쿼리만 (~20개, 빠름)
SCHOLAR_QUERIES_EN_ONLY = [
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
]


def collect_semantic_scholar(logger: HarnessLogger, tracker: SaturationTracker,
                             dry_run: bool, scholar_mode: str = "en_only") -> dict:
    endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "paperId,title,abstract,year,authors,externalIds,url"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    # API key 있으면 사용 (없으면 익명 — rate limit 낮음)
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    headers = {"User-Agent": "Harness-EduResearch/1.0 (research only; contact junti7@gmail.com)"}
    if api_key:
        headers["x-api-key"] = api_key

    queries = SCHOLAR_QUERIES_EN_ONLY if scholar_mode == "en_only" else SCHOLAR_QUERIES
    logger.info(f"Scholar 모드: {scholar_mode} ({len(queries)}개 쿼리)")
    for query in queries:
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


MULTILINGUAL_QUERIES: list[str] = [
    # 한국어
    "AI 교육 학부모 불안",
    "AI 의존 자녀 학습 능력",
    "인공지능 교육 부모 고민",
    # English
    "AI education parenting anxiety children",
    "generative AI K-12 learning dependence",
    "AI literacy children parents school",
    # 日本語
    "AI 教育 保護者 不安",
    "生成AI 子供 学習 依存",
    # 中文
    "人工智能 教育 家长 焦虑",
    "AI 依赖 学习 孩子",
    # Español
    "inteligencia artificial educacion padres ansiedad",
    # Français
    "intelligence artificielle education parents anxiete",
    # Deutsch
    "Künstliche Intelligenz Bildung Eltern Angst",
    # Português
    "inteligencia artificial educacao pais ansiedade",
    # Bahasa Indonesia
    "kecemasan orang tua pendidikan AI",
    # Türkçe
    "yapay zeka egitim ebeveyn kaygisi",
    # Tiếng Việt
    "lo lang cha me giao duc tri tue nhan tao",
    # Русский
    "iskusstvennyy intellekt obrazovanie roditel trevoga",
    # العربية
    "الذكاء الاصطناعي التعليم القلق الوالدين",
    # हिन्दी
    "AI shiksha mata-pita chinta",
]

ACADEMIC_EN_QUERIES: list[str] = [
    "AI literacy cognitive offloading K-12 education",
    "generative AI student learning outcomes critical thinking",
    "parental anxiety AI children education",
    "AI homework automation academic achievement",
    "metacognition artificial intelligence education",
    "job displacement AI anxiety workplace",
    "digital divide AI education equity",
    "teacher perception generative AI classroom",
]

HN_QUERIES: list[str] = [
    "AI education children",
    "generative AI K-12 schools",
    "AI parenting homework",
    "ChatGPT students learning",
    "AI job replacement anxiety",
]

REDDIT_SUBREDDITS: list[tuple[str, str]] = [
    ("Parenting", "AI ChatGPT children homework"),
    ("teachers", "AI ChatGPT classroom"),
    ("ChatGPT", "education children learning"),
    ("Korea", "AI 교육"),
    ("EdTech", "AI learning students"),
    ("asianparents", "AI education"),
    ("jobs", "AI replacement anxiety"),
    ("labor", "AI automation workers"),
]

NAVER_QUERIES: list[str] = [
    "AI 교육 학부모",
    "인공지능 자녀 교육",
    "챗GPT 아이 숙제",
    "AI 의존 학습 능력 저하",
    "AI 시대 자녀 교육법",
    "인공지능 직장인 불안",
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

    stats = {"attempted": len(yt_targets), "new": 0, "duplicate": 0, "error": 0}

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
            "--cookies-from-browser", "chrome",  # 브라우저 인증 쿠키로 429 우회
            "--skip-download",           # 영상 다운로드 금지 (legal_review_approve 조건)
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",          # ko 제거 — 자막 요청 수 절반으로 감소
            "--write-info-json",
            "--playlist-end", "5",       # 최근 5개만
            "--sleep-requests", "3.0",
            "--sleep-interval", "5.0",
            "--max-sleep-interval", "15.0",
            "--ignore-errors",
            "--quiet",
            "--no-warnings",
            "-o", str(out_dir / "%(id)s.%(ext)s"),
            url,
        ]

        success = False
        for attempt in range(1, 3):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    err_msg = result.stderr or ""
                    if "429" in err_msg or "Too Many Requests" in err_msg:
                        backoff = 60 * attempt
                        logger.warning(f"  [Attempt {attempt}/2] HTTP 429 감지 — {backoff}초 대기...")
                        time.sleep(backoff)
                        continue
                    else:
                        logger.warning(f"  yt-dlp 오류 ({name}): {err_msg[:200]}")
                        stats["error"] += 1
                        break
                else:
                    success = True
                    break
            except subprocess.TimeoutExpired:
                logger.warning(f"  yt-dlp 타임아웃 ({name})")
                stats["error"] += 1
                break

        if not success:
            time.sleep(5)
            continue

        # 생성된 .info.json 파일들을 raw_signals에 저장 (success=True일 때만 도달)
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
                vid_id = info.get("id", "")
                for sub_ext in ("en.vtt", "ko.vtt", "en.srv3"):
                    sub_path = out_dir / f"{vid_id}.{sub_ext}"
                    if sub_path.exists():
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
        time.sleep(10)  # YouTube rate limit 방지

    return stats


# ---------------------------------------------------------------------------
# YouTube Data API v3 수집 (공식 API — 429 없음, 1만 유닛/일 무료)
# ---------------------------------------------------------------------------

_YT_API_BASE = "https://www.googleapis.com/youtube/v3"


def _yt_api_get(path: str, params: dict, logger: HarnessLogger) -> dict | None:
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    try:
        resp = httpx.get(
            f"{_YT_API_BASE}/{path}",
            params={**params, "key": api_key},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"  YouTube API {path} HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()
    except Exception as e:
        logger.warning(f"  YouTube API {path} 오류: {e}")
        return None


def collect_youtube_via_api(yt_targets: list[dict], search_queries: list[str],
                            extra_query: str, logger: HarnessLogger,
                            tracker: SaturationTracker, dry_run: bool) -> dict | None:
    """YouTube Data API v3로 채널 영상 메타데이터 수집.
    YOUTUBE_API_KEY 미설정 시 None 반환 → yt-dlp fallback."""
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key:
        return None

    stats = {"attempted": len(yt_targets), "new": 0, "duplicate": 0, "error": 0}

    for ch in yt_targets:
        name = ch["name"]
        url = ch["url"]

        handle_match = re.search(r'@([^/]+)', url)
        if not handle_match:
            logger.warning(f"  채널 핸들 추출 실패: {url}")
            stats["error"] += 1
            continue
        handle = handle_match.group(1)
        logger.info(f"YouTube API: {name} (@{handle})")

        if dry_run:
            logger.info(f"  [dry-run] channels?forHandle=@{handle} + search")
            stats["new"] += 3
            continue

        # 채널 ID 조회 (100 유닛)
        data = _yt_api_get("channels", {"part": "id", "forHandle": f"@{handle}"}, logger)
        if not data or not data.get("items"):
            logger.warning(f"  채널 없음: @{handle} (삭제/URL 변경 확인 필요)")
            stats["error"] += 1
            continue
        channel_id = data["items"][0]["id"]
        time.sleep(1)

        # 최근 영상 목록 (100 유닛/검색)
        data = _yt_api_get("search", {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 5,
            "order": "date",
            "type": "video",
        }, logger)
        if not data:
            stats["error"] += 1
            continue

        videos = data.get("items", [])
        ch_new = 0
        for video in videos:
            snippet = video.get("snippet", {})
            video_id = (video.get("id") or {}).get("videoId", "")
            if not video_id:
                continue
            raw = {
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": (snippet.get("description") or "")[:2000],
                "channel": snippet.get("channelTitle", name),
                "published_at": snippet.get("publishedAt", ""),
                "source_name": f"youtube_{name.replace(' ', '_')}",
                "signal_class": "youtube",
                "rq_tags": ch.get("rq_tags", []),
                "evidence_posture": "media",
            }
            saved = save_signal(f"youtube_{name.replace(' ', '_')}", raw, DOMAIN, logger)
            if saved:
                ch_new += 1
                stats["new"] += 1

        tracker.record(f"youtube_{name[:30]}", ch_new, len(videos))
        logger.info(f"  완료: {ch_new}개 신규 / {len(videos)}개 영상")
        time.sleep(1)

    # Part 2: keyword discovery across multilingual parent/education queries.
    ordered_queries = []
    if extra_query:
        ordered_queries.append(extra_query)
    ordered_queries.extend(search_queries)

    for query in ordered_queries:
        logger.info(f"YouTube API 검색: {query}")
        if dry_run:
            logger.info(f"  [dry-run] search?q={query}")
            stats["new"] += 5
            time.sleep(1)
            continue

        data = _yt_api_get("search", {
            "part": "snippet",
            "q": query,
            "maxResults": 5,
            "type": "video",
            "order": "relevance",
        }, logger)
        if not data:
            stats["error"] += 1
            time.sleep(1)
            continue

        items = data.get("items", [])
        query_new = 0
        for item in items:
            snippet = item.get("snippet", {})
            video_id = (item.get("id") or {}).get("videoId", "")
            if not video_id:
                continue
            raw = {
                "title": snippet.get("title", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "description": (snippet.get("description") or "")[:2000],
                "channel": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "source_name": "youtube_search",
                "signal_class": "youtube",
                "rq_tags": ["RQ1", "RQ3", "RQ4"],
                "query": query,
                "evidence_posture": "media",
            }
            saved = save_signal("youtube_search", raw, DOMAIN, logger)
            if saved:
                query_new += 1
                stats["new"] += 1
            else:
                stats["duplicate"] = stats.get("duplicate", 0) + 1

        tracker.record(f"youtube_search_{query[:30]}", query_new, len(items))
        logger.info(f"  검색 완료: {query_new}개 신규 / {len(items)}개 영상")
        time.sleep(1)

    return stats


# ---------------------------------------------------------------------------
# Additional academic/community APIs
# ---------------------------------------------------------------------------

def _openalex_abstract(abstract_index: dict | None) -> str:
    if not abstract_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in abstract_index.items():
        for index in indexes:
            positions[index] = word
    return " ".join(positions[index] for index in sorted(positions))


def collect_openalex(queries: list[str], logger: HarnessLogger,
                     tracker: SaturationTracker, dry_run: bool) -> dict:
    endpoint = "https://api.openalex.org/works"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    for query in queries:
        logger.info(f"OpenAlex: {query}")
        try:
            resp = httpx.get(
                endpoint,
                params={
                    "search": query,
                    "filter": "open_access.is_oa:true",
                    "per-page": 15,
                    "mailto": "junti7@gmail.com",
                },
                timeout=25,
            )
            if resp.status_code != 200:
                logger.warning(f"  OpenAlex HTTP {resp.status_code}: {resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            works = resp.json().get("results", [])
            query_new = 0
            for work in works:
                raw = {
                    "title": work.get("title", ""),
                    "url": work.get("doi") or work.get("id", ""),
                    "abstract": _openalex_abstract(work.get("abstract_inverted_index"))[:3000],
                    "published_year": work.get("publication_year"),
                    "source_name": "openalex",
                    "signal_class": "academic",
                    "rq_tags": ["RQ2", "RQ5"],
                    "query": query,
                    "evidence_posture": "academic",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    query_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("openalex", raw, DOMAIN, logger)
                    if saved:
                        query_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"openalex_{query[:30]}", query_new, len(works))
            logger.info(f"  완료: {query_new}개 신규 / {len(works)}개 전체")
        except Exception as e:
            logger.warning(f"  OpenAlex 실패 ({query}): {e}")
            stats["error"] += 1
        time.sleep(1)

    return stats


def collect_eric(queries: list[str], logger: HarnessLogger,
                 tracker: SaturationTracker, dry_run: bool) -> dict:
    endpoint = "https://api.ies.ed.gov/eric/"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    for query in queries:
        logger.info(f"ERIC: {query}")
        try:
            resp = httpx.get(
                endpoint,
                params={"search": query, "format": "json", "rows": 15},
                timeout=25,
            )
            if resp.status_code != 200:
                logger.warning(f"  ERIC HTTP {resp.status_code}: {resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            data = resp.json()
            records = data.get("response", {}).get("docs") or data.get("records") or data.get("docs") or []
            query_new = 0
            for record in records:
                title = record.get("title") or record.get("title_s") or ""
                url = record.get("url") or record.get("eric_url") or record.get("id") or ""
                raw = {
                    "title": title,
                    "url": url,
                    "abstract": (record.get("description") or record.get("abstract") or "")[:3000],
                    "year": record.get("publicationdateyear") or record.get("year"),
                    "source_name": "eric",
                    "signal_class": "academic",
                    "rq_tags": ["RQ2", "RQ5"],
                    "query": query,
                    "evidence_posture": "academic",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    query_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("eric", raw, DOMAIN, logger)
                    if saved:
                        query_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"eric_{query[:30]}", query_new, len(records))
            logger.info(f"  완료: {query_new}개 신규 / {len(records)}개 전체")
        except Exception as e:
            logger.warning(f"  ERIC 실패 ({query}): {e}")
            stats["error"] += 1
        time.sleep(1)

    return stats


def collect_pubmed(queries: list[str], logger: HarnessLogger,
                   tracker: SaturationTracker, dry_run: bool) -> dict:
    search_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    for query in queries:
        logger.info(f"PubMed: {query}")
        try:
            search_resp = httpx.get(
                search_endpoint,
                params={"db": "pubmed", "term": query, "retmax": 15, "retmode": "json"},
                timeout=25,
            )
            if search_resp.status_code != 200:
                logger.warning(f"  PubMed esearch HTTP {search_resp.status_code}: {search_resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                tracker.record(f"pubmed_{query[:30]}", 0, 0)
                logger.info("  완료: 0개 신규 / 0개 전체")
                time.sleep(1)
                continue

            summary_resp = httpx.get(
                summary_endpoint,
                params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
                timeout=25,
            )
            if summary_resp.status_code != 200:
                logger.warning(f"  PubMed esummary HTTP {summary_resp.status_code}: {summary_resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            result = summary_resp.json().get("result", {})
            query_new = 0
            for pmid in result.get("uids", []):
                item = result.get(pmid, {})
                raw = {
                    "title": item.get("title", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "summary": item.get("source", ""),
                    "published": item.get("pubdate", ""),
                    "source_name": "pubmed",
                    "signal_class": "academic",
                    "rq_tags": ["RQ2", "RQ5"],
                    "query": query,
                    "evidence_posture": "academic",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    query_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("pubmed", raw, DOMAIN, logger)
                    if saved:
                        query_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"pubmed_{query[:30]}", query_new, len(ids))
            logger.info(f"  완료: {query_new}개 신규 / {len(ids)}개 전체")
        except Exception as e:
            logger.warning(f"  PubMed 실패 ({query}): {e}")
            stats["error"] += 1
        time.sleep(1)

    return stats


def collect_hackernews(queries: list[str], logger: HarnessLogger,
                       tracker: SaturationTracker, dry_run: bool) -> dict:
    endpoint = "https://hn.algolia.com/api/v1/search"
    stats = {"new": 0, "duplicate": 0, "error": 0}

    for query in queries:
        logger.info(f"Hacker News: {query}")
        try:
            resp = httpx.get(
                endpoint,
                params={"query": query, "tags": "story", "hitsPerPage": 10},
                timeout=20,
            )
            if resp.status_code != 200:
                logger.warning(f"  Hacker News HTTP {resp.status_code}: {resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            hits = resp.json().get("hits", [])
            query_new = 0
            for hit in hits:
                object_id = hit.get("objectID", "")
                raw = {
                    "title": hit.get("title") or hit.get("story_title") or "",
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}",
                    "summary": (hit.get("story_text") or hit.get("comment_text") or "")[:2000],
                    "points": hit.get("points"),
                    "num_comments": hit.get("num_comments"),
                    "source_name": "hackernews",
                    "signal_class": "community",
                    "rq_tags": ["RQ2", "RQ3"],
                    "query": query,
                    "evidence_posture": "community",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    query_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("hackernews", raw, DOMAIN, logger)
                    if saved:
                        query_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"hackernews_{query[:30]}", query_new, len(hits))
            logger.info(f"  완료: {query_new}개 신규 / {len(hits)}개 전체")
        except Exception as e:
            logger.warning(f"  Hacker News 실패 ({query}): {e}")
            stats["error"] += 1
        time.sleep(1)

    return stats


def collect_reddit(subreddits: list[tuple[str, str]], logger: HarnessLogger,
                   tracker: SaturationTracker, dry_run: bool) -> dict:
    stats = {"new": 0, "duplicate": 0, "error": 0}
    client_id = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.info("Reddit API credentials missing; skipping reddit collector.")
        return {**stats, "skipped": True}

    headers = {"User-Agent": "Harness-EduResearch/1.0 by junti7"}
    try:
        token_resp = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers=headers,
            timeout=20,
        )
        if token_resp.status_code != 200:
            logger.warning(f"  Reddit token HTTP {token_resp.status_code}: {token_resp.text[:200]}")
            stats["error"] += 1
            return stats
        token = token_resp.json().get("access_token", "")
    except Exception as e:
        logger.warning(f"  Reddit token 실패: {e}")
        stats["error"] += 1
        return stats

    auth_headers = {**headers, "Authorization": f"Bearer {token}"}
    for subreddit, query in subreddits:
        logger.info(f"Reddit: r/{subreddit} {query}")
        try:
            resp = httpx.get(
                f"https://oauth.reddit.com/r/{subreddit}/search.json",
                params={"q": query, "restrict_sr": 1, "sort": "relevance", "limit": 10},
                headers=auth_headers,
                timeout=20,
            )
            if resp.status_code != 200:
                logger.warning(f"  Reddit HTTP {resp.status_code}: {resp.text[:200]}")
                stats["error"] += 1
                time.sleep(1)
                continue

            children = resp.json().get("data", {}).get("children", [])
            query_new = 0
            for child in children:
                item = child.get("data", {})
                raw = {
                    "title": item.get("title", ""),
                    "url": f"https://www.reddit.com{item.get('permalink', '')}",
                    "summary": (item.get("selftext") or "")[:2000],
                    "score": item.get("score"),
                    "num_comments": item.get("num_comments"),
                    "subreddit": subreddit,
                    "source_name": "reddit",
                    "signal_class": "community",
                    "rq_tags": ["RQ1", "RQ4"],
                    "query": query,
                    "evidence_posture": "community",
                }
                if dry_run:
                    logger.info(f"  [dry-run] {raw['title'][:80]}")
                    query_new += 1
                    stats["new"] += 1
                else:
                    saved = save_signal("reddit", raw, DOMAIN, logger)
                    if saved:
                        query_new += 1
                        stats["new"] += 1
                    else:
                        stats["duplicate"] += 1

            tracker.record(f"reddit_{subreddit}_{query[:20]}", query_new, len(children))
            logger.info(f"  완료: {query_new}개 신규 / {len(children)}개 전체")
        except Exception as e:
            logger.warning(f"  Reddit 실패 (r/{subreddit} {query}): {e}")
            stats["error"] += 1
        time.sleep(1)

    return stats


def collect_naver(queries: list[str], logger: HarnessLogger,
                  tracker: SaturationTracker, dry_run: bool) -> dict:
    stats = {"new": 0, "duplicate": 0, "error": 0}
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.info("Naver Search API credentials missing; skipping naver collector.")
        return {**stats, "skipped": True}

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    for query in queries:
        for search_type in ("blog", "news"):
            logger.info(f"Naver {search_type}: {query}")
            try:
                resp = httpx.get(
                    f"https://openapi.naver.com/v1/search/{search_type}.json",
                    params={"query": query, "display": 10, "sort": "date"},
                    headers=headers,
                    timeout=20,
                )
                if resp.status_code != 200:
                    logger.warning(f"  Naver {search_type} HTTP {resp.status_code}: {resp.text[:200]}")
                    stats["error"] += 1
                    time.sleep(1)
                    continue

                items = resp.json().get("items", [])
                query_new = 0
                for item in items:
                    title = re.sub(r"<[^>]+>", "", item.get("title", ""))
                    description = re.sub(r"<[^>]+>", "", item.get("description", ""))
                    raw = {
                        "title": title,
                        "url": item.get("link") or item.get("originallink") or "",
                        "summary": description[:2000],
                        "published": item.get("postdate") or item.get("pubDate") or "",
                        "source_name": f"naver_{search_type}",
                        "signal_class": "community" if search_type == "blog" else "news",
                        "rq_tags": ["RQ1", "RQ4"],
                        "query": query,
                        "evidence_posture": "community" if search_type == "blog" else "media",
                    }
                    if dry_run:
                        logger.info(f"  [dry-run] {raw['title'][:80]}")
                        query_new += 1
                        stats["new"] += 1
                    else:
                        saved = save_signal(f"naver_{search_type}", raw, DOMAIN, logger)
                        if saved:
                            query_new += 1
                            stats["new"] += 1
                        else:
                            stats["duplicate"] += 1

                tracker.record(f"naver_{search_type}_{query[:30]}", query_new, len(items))
                logger.info(f"  완료: {query_new}개 신규 / {len(items)}개 전체")
            except Exception as e:
                logger.warning(f"  Naver {search_type} 실패 ({query}): {e}")
                stats["error"] += 1
            time.sleep(1)

    return stats


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="교육 컨설팅 DEEP RESEARCH 수집기")
    parser.add_argument(
        "--sources",
        default="rss,scholar,arxiv",
        help=("수집 소스 (쉼표 구분): "
              "rss,scholar,arxiv,youtube,openalex,eric,pubmed,hackernews,reddit,naver,all "
              "(기본: rss,scholar,arxiv)"),
    )
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 수집 예상 항목만 출력")
    parser.add_argument("--domain", default=DOMAIN, help="도메인 태그 (기본: edu_consulting)")
    parser.add_argument("--extra-query", default="", help="추가 연구 주제 쿼리 (scholar + arXiv 앞에 삽입)")
    parser.add_argument("--max-rss-items", type=int, default=50,
                        help="RSS 소스당 최대 수집 항목 수 (기본: 50)")
    parser.add_argument("--scholar-mode", default="en_only",
                        choices=["en_only", "multilingual"],
                        help="Scholar 쿼리 모드: en_only(영어 20개, 빠름) / multilingual(60개+, 느림)")
    args = parser.parse_args()

    enabled = {s.strip() for s in args.sources.split(",")}
    domain = args.domain
    dry_run = args.dry_run

    # 추가 쿼리를 각 소스 쿼리 목록 앞에 삽입
    if args.extra_query:
        SCHOLAR_QUERIES.insert(0, args.extra_query)
        arxiv_q = "abs:" + args.extra_query.replace(" ", "+")
        ARXIV_QUERIES.insert(0, arxiv_q)
        ACADEMIC_EN_QUERIES.insert(0, args.extra_query)
        HN_QUERIES.insert(0, args.extra_query)
        NAVER_QUERIES.insert(0, args.extra_query)

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
    yt_search_queries = yt_config.get("multilingual_search_queries", [])

    tracker = SaturationTracker()
    total_new = 0
    results = {}

    if "rss" in enabled or "all" in enabled:
        logger.info("--- [RSS 수집] ---")
        r = collect_rss(sources, logger, tracker, dry_run, max_rss_items=args.max_rss_items)
        results["rss"] = r
        total_new += r["new"]

    if "scholar" in enabled or "all" in enabled:
        logger.info("--- [Semantic Scholar API] ---")
        r = collect_semantic_scholar(logger, tracker, dry_run, scholar_mode=args.scholar_mode)
        results["scholar"] = r
        total_new += r["new"]

    if "arxiv" in enabled or "all" in enabled:
        logger.info("--- [arXiv API] ---")
        r = collect_arxiv(logger, tracker, dry_run)
        results["arxiv"] = r
        total_new += r["new"]

    if "openalex" in enabled or "all" in enabled:
        logger.info("--- [OpenAlex API] ---")
        r = collect_openalex(ACADEMIC_EN_QUERIES, logger, tracker, dry_run)
        results["openalex"] = r
        total_new += r["new"]

    if "eric" in enabled or "all" in enabled:
        logger.info("--- [ERIC API] ---")
        r = collect_eric(ACADEMIC_EN_QUERIES, logger, tracker, dry_run)
        results["eric"] = r
        total_new += r["new"]

    if "pubmed" in enabled or "all" in enabled:
        logger.info("--- [PubMed API] ---")
        r = collect_pubmed(ACADEMIC_EN_QUERIES, logger, tracker, dry_run)
        results["pubmed"] = r
        total_new += r["new"]

    if "hackernews" in enabled or "all" in enabled:
        logger.info("--- [Hacker News Algolia API] ---")
        r = collect_hackernews(HN_QUERIES, logger, tracker, dry_run)
        results["hackernews"] = r
        total_new += r["new"]

    if "reddit" in enabled or "all" in enabled:
        logger.info("--- [Reddit API] ---")
        r = collect_reddit(REDDIT_SUBREDDITS, logger, tracker, dry_run)
        results["reddit"] = r
        total_new += r["new"]

    if "naver" in enabled or "all" in enabled:
        logger.info("--- [Naver Search API] ---")
        r = collect_naver(NAVER_QUERIES, logger, tracker, dry_run)
        results["naver"] = r
        total_new += r["new"]

    if "youtube" in enabled or "all" in enabled:
        api_result = collect_youtube_via_api(
            yt_targets, yt_search_queries, args.extra_query, logger, tracker, dry_run
        )
        if api_result is not None:
            logger.info("--- [YouTube Data API v3] ---")
            results["youtube"] = api_result
            total_new += api_result["new"]
        else:
            logger.info("--- [YouTube yt-dlp (YOUTUBE_API_KEY 미설정 → browser-cookies fallback)] ---")
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
