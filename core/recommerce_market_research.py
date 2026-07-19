"""Low-cost, repeatable market screening for recommerce OJT candidates."""

from __future__ import annotations

import html
import json
import os
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from core.atomic_io import update_json_atomic


CANDIDATES = (
    {
        "id": "adult_craft_parts_organizer",
        "query": "공예 부품 수납함",
        "name": "성인 공예·소형부품 수납함",
        "category": "adult_hobby_supplies_non_regulated",
        "rank": 1,
        "why": "비교 후보가 상대적으로 적고, 비전기·비식품·성인 취미 용도로 범위를 제한하기 쉽습니다.",
        "training_goal": "공급처 증빙과 성인용 표기를 확인하고 칸 수·재질·잠금 구조를 비교합니다.",
        "risks": ["어린이용으로 광고하면 제외", "얇은 경첩·잠금 불량", "소형 부품은 포함하지 않음"],
    },
    {
        "id": "modular_drawer_tray_set",
        "query": "서랍 정리 트레이 세트",
        "name": "모듈형 서랍 정리 트레이 세트",
        "category": "storage_organization",
        "rank": 2,
        "why": "규제 위험이 낮고 중첩 포장·세트 구성이 가능해 공급가와 배송비 훈련에 적합합니다.",
        "training_goal": "단품이 아니라 4~8개 묶음 기준으로 치수·포장·반품 원인을 비교합니다.",
        "risks": ["서랍 치수 불일치", "플라스틱 파손", "단품 가격경쟁"],
    },
    {
        "id": "a4_document_organizer_bundle",
        "query": "A4 파일 정리함",
        "name": "A4 문서 정리함 묶음",
        "category": "stationery",
        "rank": 3,
        "why": "수요·가격 비교 자료가 풍부해 초보자가 경쟁 과밀과 부피 배송비를 학습하기 좋습니다.",
        "training_goal": "A4 실측 규격, 적층 안정성, 부피 배송비를 반영해 탈락 여부를 판단합니다.",
        "risks": ["경쟁 과밀", "부피 배송비", "모서리 파손"],
    },
)

REJECTED = (
    {"query": "케이블 정리 클립", "reason": "표본 중간가가 지나치게 낮아 배송·노동비를 흡수하기 어렵습니다."},
    {"query": "길이조절 서랍 칸막이", "reason": "낮은 객단가와 치수 불일치 반품 위험이 큽니다."},
    {"query": "책상 밑 부착 서랍", "reason": "접착력·하중·책상 재질에 따른 반품 위험이 큽니다."},
    {"query": "데스크 오거나이저 트레이", "reason": "검색 경쟁이 매우 높고 기존 브랜드·가격 경쟁이 강합니다."},
)


def _clean_title(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def _screen_query(client: httpx.Client, headers: dict[str, str], query: str) -> dict[str, Any]:
    response = client.get(
        "https://openapi.naver.com/v1/search/shop.json",
        params={"query": query, "display": 100, "sort": "sim"},
        headers=headers,
    )
    response.raise_for_status()
    payload = response.json()
    prices = sorted(int(item["lprice"]) for item in payload.get("items", []) if str(item.get("lprice", "")).isdigit() and int(item["lprice"]) > 0)
    malls = {str(item.get("mallName") or "unknown") for item in payload.get("items", [])}
    return {
        "result_count": int(payload.get("total") or 0),
        "sample_size": len(prices),
        "median_price": int(statistics.median(prices)) if prices else None,
        "price_p25": prices[len(prices) // 4] if prices else None,
        "price_p75": prices[(len(prices) * 3) // 4] if prices else None,
        "sample_mall_count": len(malls),
        "sample_titles": [_clean_title(item.get("title", "")) for item in payload.get("items", [])[:3]],
    }


def run_market_research(path: Path, *, client_id: str | None = None, client_secret: str | None = None) -> dict[str, Any]:
    client_id = (client_id or os.getenv("NAVER_CLIENT_ID", "")).strip()
    client_secret = (client_secret or os.getenv("NAVER_CLIENT_SECRET", "")).strip()
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required")
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    rows = []
    with httpx.Client(timeout=15) as client:
        for candidate in CANDIDATES:
            rows.append({**candidate, **_screen_query(client, headers, candidate["query"])})
        rejected = [{**item, **_screen_query(client, headers, item["query"])} for item in REJECTED]
    snapshot = {
        "status": "training_shortlist_not_purchase_recommendation",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "Naver Shopping Search API",
        "method_note": "검색 결과 수와 100개 표본 가격은 수요·판매량 증명이 아니며 공급가 인터뷰 전 매입 판단에 사용할 수 없습니다.",
        "candidates": sorted(rows, key=lambda row: row["rank"]),
        "rejected": rejected,
    }

    def replace(fresh: dict[str, Any]) -> None:
        fresh.clear()
        fresh.update(snapshot)

    update_json_atomic(path, replace)
    return snapshot


def load_market_research(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "not_run", "candidates": [], "rejected": [], "observed_at": None}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"status": "invalid", "candidates": [], "rejected": []}
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "candidates": [], "rejected": [], "observed_at": None}
