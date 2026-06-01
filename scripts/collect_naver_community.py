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
load_dotenv(ROOT / ".env", override=True)

CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "").strip()

API = "https://openapi.naver.com/v1/search"

# 세그먼트별 검색어 (부모 = 학부모 AI 불안·의존 / 직장인 = 커리어 AI 압박)
QUERIES = {
    "parent": [
        "아이 AI 의존 걱정", "챗GPT 숙제 베끼기", "초등 AI 교육 고민",
        "중학생 챗GPT 사용", "아이 AI 너무 많이", "AI 시대 자녀 교육 불안",
        "아이 스스로 생각 안해", "숙제 AI 그대로",
    ],
    "worker": [
        "직장인 AI 불안", "회사 AI 못쓰면 도태", "AI 때문에 이직 고민",
        "AI 공부 어디서 시작", "AI 못따라가 불안", "직장 생성형 AI 압박",
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


def _search(endpoint: str, query: str, display: int = 20) -> list[dict]:
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }
    params = {"query": query, "display": display, "sort": "sim"}
    resp = httpx.get(f"{API}/{endpoint}.json", headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("items", [])


def collect(segment: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for endpoint, label in TARGETS:
        for q in QUERIES[segment]:
            try:
                items = _search(endpoint, q)
            except httpx.HTTPStatusError as e:
                print(f"  [WARN] {label}/{q}: HTTP {e.response.status_code} {e.response.text[:120]}")
                continue
            except Exception as e:
                print(f"  [WARN] {label}/{q}: {type(e).__name__}: {e}")
                continue
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


if __name__ == "__main__":
    main()
