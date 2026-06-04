"""
네이버 커뮤니티 수집 — 공식 Naver 검색 API (ToS 준수)

수집 대상 (공개 게시글만, 로그인/크롤링 없음):
  - 카페글  (cafearticle)  — 맘카페 등 공개 글
  - 지식iN  (kin)          — 학부모·직장인 AI 고민 Q&A
  - 블로그  (blog)         — 후기·경험담

직접 크롤링(Playwright)은 ToS 리스크로 사용하지 않는다. 공식 API만 사용.

필요 자격증명 (.env):
  NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
  → https://developers.naver.com/apps 에서 무료 발급 (검색 API 사용 설정)

사용:
  python scripts/collect_naver_community.py
  python scripts/collect_naver_community.py --segment worker
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402

CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

API = "https://openapi.naver.com/v1/search"

# 세그먼트별 검색어 (부모 = 학부모 AI 불안·의존 / 직장인 = 커리어 AI 압박)
# 맘카페 담론을 넓게 긁기 위해 키워드를 대폭 확장. 노이즈는 Tier2 필터가 제거.
QUERIES = {
    "parent": [
        # AI 의존·숙제
        "아이 AI 의존 걱정", "챗GPT 숙제 베끼기", "아이 챗GPT 숙제", "숙제 AI 그대로",
        "아이 AI 너무 많이", "아이 스스로 생각 안해", "AI 베껴쓰기 아이",
        # 학년별
        "초등 AI 교육 고민", "초등학생 챗GPT", "중학생 챗GPT 사용", "고등학생 AI 공부",
        "유아 AI 교육", "초등 코딩 학원 고민",
        # 부모 불안·태도
        "AI 시대 자녀 교육 불안", "AI 시대 아이 키우기", "우리 아이 미래 직업 AI",
        "AI 시대 공부 의미", "아이 AI 어떻게 가르쳐", "엄마표 AI 교육",
        "챗GPT 아이에게 도움", "AI 교육 어떻게 시작",
        # 디지털·스크린
        "아이 유튜브 중독", "아이 스마트폰 게임 공부 안해", "아이 영상만 봐 걱정",
        # 학습·진로
        "AI 시대 독서 중요", "아이 문해력 걱정", "AI 시대 사고력 교육",
        "코딩 교육 필요할까", "AI 진로 자녀",
    ],
    "worker": [
        "직장인 AI 불안", "회사 AI 못쓰면 도태", "AI 때문에 이직 고민",
        "AI 공부 어디서 시작", "AI 못따라가 불안", "직장 생성형 AI 압박",
        "30대 AI 공부", "챗GPT 업무 활용", "AI 자기계발 직장인",
        "AI 시대 커리어 불안", "프롬프트 공부", "사무직 AI 대체 불안",
    ],
}

TARGETS = [
    ("cafearticle", "카페글"),
    ("kin", "지식iN"),
    ("blog", "블로그"),
]


def _clean(text: str) -> str:
    """네이버 응답의 <b> 태그·HTML 엔티티 제거."""
    text = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(text).strip()


# 네이버 검색 API: display 최대 100, start 최대 1000 (start+display ≤ 1000).
# 일 25,000 요청 한도 — 페이지를 늘려도 여유 충분.
DISPLAY = 100        # 요청당 100건
PAGES = 3            # 쿼리당 페이지 수 (start=1,101,201 → 최대 300건/쿼리/소스)


def _search(endpoint: str, query: str, display: int = DISPLAY, start: int = 1) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "start": start, "sort": "sim"}
    resp = httpx.get(f"{API}/{endpoint}.json", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def collect(segment: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for endpoint, label in TARGETS:
        for q in QUERIES[segment]:
            items: list[dict] = []
            for page in range(PAGES):
                start = 1 + page * DISPLAY
                if start > 1000:
                    break
                try:
                    batch = _search(endpoint, q, start=start)
                except httpx.HTTPStatusError as e:
                    print(f"  [WARN] {label}/{q} p{page}: HTTP {e.response.status_code} {e.response.text[:100]}")
                    break
                except Exception as e:
                    print(f"  [WARN] {label}/{q} p{page}: {type(e).__name__}: {e}")
                    break
                if not batch:
                    break
                items.extend(batch)
                time.sleep(0.25)  # rate limit 예의
                if len(batch) < DISPLAY:
                    break  # 마지막 페이지
            for it in items:
                title = _clean(it.get("title", ""))
                desc = _clean(it.get("description", ""))
                link = it.get("link", "")
                if not title or link in seen:
                    continue
                seen.add(link)
                out.append({
                    "source": f"Naver_{label}",
                    "segment": segment,
                    "query": q,
                    "title": title,
                    "description": desc,
                    "link": link,
                    "cafe_or_blog": _clean(it.get("cafename") or it.get("bloggername") or ""),
                    "postdate": it.get("postdate", ""),
                })
            print(f"  [OK] {label} / '{q}' → 누적 {len(out)}건")
            time.sleep(0.3)  # rate limit 예의
    return out


def ingest_raw_signals(items: list[dict]) -> int:
    """수집 항목을 raw_signals(domain=edu_consulting)에 적재 → 파이프라인(필터·정제·RAG)으로 흐름.

    네이버 검색 API는 제목+요약 스니펫만 제공(본문 전체 아님, ToS 한계)하므로
    full_content = 제목+요약으로 구성한다. content_hash로 중복 제거(pending 상태).
    """
    new = 0
    for it in items:
        title = it.get("title", "")
        link = it.get("link", "")
        desc = it.get("description", "")
        key = f"{title}{link}"
        content_hash = hashlib.sha256(key.encode()).hexdigest()[:64]
        raw_data = {
            "title": title,
            "url": link,
            "description": desc,
            "full_content": f"{title}\n\n{desc}".strip(),
            "source_detail": it.get("cafe_or_blog", ""),
            "query": it.get("query", ""),
            "postdate": it.get("postdate", ""),
            "segment": it.get("segment", "parent"),
            "domain": "edu_consulting",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            execute_query(
                """
                INSERT INTO raw_signals (source, raw_data, content_hash, full_content, status, domain)
                VALUES (%s, %s, %s, %s, 'pending', 'edu_consulting')
                ON CONFLICT (content_hash) DO NOTHING
                """,
                (it.get("source", "Naver"), json.dumps(raw_data, ensure_ascii=False),
                 content_hash, raw_data["full_content"]),
            )
            new += 1
        except Exception as e:
            print(f"  [WARN] 적재 실패: {type(e).__name__}: {e}")
    return new


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segment", choices=["parent", "worker", "both"], default="both")
    args = parser.parse_args()

    if not CLIENT_ID or not CLIENT_SECRET:
        print("=" * 64)
        print("❌ 네이버 API 자격증명이 없습니다.")
        print("  .env 에 다음 두 값을 추가하세요:")
        print("    NAVER_CLIENT_ID=...")
        print("    NAVER_CLIENT_SECRET=...")
        print()
        print("  발급 방법 (무료, 2분):")
        print("  1) https://developers.naver.com/apps/#/register 접속")
        print("  2) 애플리케이션 등록 → 사용 API: '검색' 선택")
        print("  3) 발급된 Client ID / Client Secret 을 .env 에 입력")
        print("=" * 64)
        sys.exit(1)

    segments = ["parent", "worker"] if args.segment == "both" else [args.segment]
    all_items: list[dict] = []
    for seg in segments:
        print(f"\n=== 세그먼트: {seg} ===")
        all_items.extend(collect(seg))

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = ROOT / "data" / "edu_research" / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "naver_collected.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 총 {len(all_items)}건 수집 → {out_path}")
    # 세그먼트·소스별 집계
    from collections import Counter
    by_src = Counter(f"{i['segment']}/{i['source']}" for i in all_items)
    for k, v in sorted(by_src.items()):
        print(f"   {k}: {v}건")

    # raw_signals 적재 (edu 파이프라인 진입)
    ingested = ingest_raw_signals(all_items)
    print(f"📥 raw_signals(edu_consulting) 적재 시도 {ingested}건 (중복은 자동 스킵)")


if __name__ == "__main__":
    main()
