"""Evidence-first, local-LLM product selection for recommerce OJT."""

from __future__ import annotations

import html
import json
import os
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from core.atomic_io import update_json_atomic


DISCOVERY_QUERIES = (
    "성인 공예 정리 수납함",
    "소형 부품 정리함",
    "서랍 정리 트레이 세트",
    "A4 문서 정리함 세트",
)
RESTRICTED_TERMS = (
    "유아", "어린이", "아동", "완구", "식품", "건강기능", "화장품", "의약", "전기", "배터리", "충전",
)
SAFE_CATEGORY1 = {"생활/건강", "가구/인테리어"}
MIN_ITEM_PRICE = 12_000
MIN_COMPETITOR_SAMPLES = 4
MIN_COMPETITOR_MALLS = 2
MIN_LLM_SCORE = 70
MAX_PRICE_SPREAD_RATIO = 2.1
CONSERVATIVE_PLATFORM_FEE_RATE = 0.15
CONSERVATIVE_RETURN_RESERVE_RATE = 0.08
CONSERVATIVE_AD_RATE = 0.10
TARGET_CONTRIBUTION_RATE = 0.20
CONSERVATIVE_SHIPPING_COST = 4_000
CONSERVATIVE_LABOR_PACKAGING_COST = 2_000
MAX_SHORTLIST = 3
LLMSelector = Callable[[list[dict[str, Any]]], tuple[dict[str, Any], dict[str, Any]]]

# Only market/economic thresholds adapt. Safety scope, item identity, LLM use and
# commercial blocking never relax. Profiles are evaluated in this exact order.
SELECTION_PROFILES = (
    {
        "id": "strict", "label": "엄격 기준", "adaptive": False,
        "minimum_item_price": 15_000, "minimum_competitor_samples": 5,
        "minimum_competitor_malls": 3, "minimum_llm_score": 75,
        "maximum_price_spread_ratio": 1.60, "minimum_allowable_supply_cost": 3_000,
    },
    {
        "id": "adaptive_1", "label": "적응 1단계 · 제한 완화", "adaptive": True,
        "minimum_item_price": 14_000, "minimum_competitor_samples": 5,
        "minimum_competitor_malls": 3, "minimum_llm_score": 72,
        "maximum_price_spread_ratio": 1.90, "minimum_allowable_supply_cost": 2_500,
    },
    {
        "id": "adaptive_2", "label": "적응 2단계 · 최종 보수 완화", "adaptive": True,
        "minimum_item_price": 12_000, "minimum_competitor_samples": 4,
        "minimum_competitor_malls": 2, "minimum_llm_score": 70,
        "maximum_price_spread_ratio": 2.10, "minimum_allowable_supply_cost": 1_500,
    },
)


def _clean_title(value: str) -> str:
    return re.sub(r"<[^>]+>", "", html.unescape(value or "")).strip()


def _tokens(value: str) -> set[str]:
    return {
        token for token in re.findall(r"[0-9a-zA-Z가-힣]+", _clean_title(value).lower())
        if len(token) > 1 and token not in {"정리", "수납", "다용도", "보관", "세트", "투명"}
    }


def _similarity(left: str, right: str) -> float:
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _naver_search(client: httpx.Client, headers: dict[str, str], query: str, *, display: int = 100) -> dict[str, Any]:
    for attempt in range(4):
        response = client.get(
            "https://openapi.naver.com/v1/search/shop.json",
            params={"query": query, "display": display, "sort": "sim"},
            headers=headers,
        )
        if response.status_code != 429:
            response.raise_for_status()
            time.sleep(0.12)
            return response.json()
        if attempt < 3:
            time.sleep(1.5 * (attempt + 1))
    response.raise_for_status()
    raise RuntimeError("naver_search_unreachable")


def _normalize_item(item: dict[str, Any], query: str) -> dict[str, Any] | None:
    price_text = str(item.get("lprice") or "")
    if not price_text.isdigit() or int(price_text) <= 0:
        return None
    return {
        "id": f"naver_{item.get('productId') or abs(hash(_clean_title(str(item.get('title') or ''))))}",
        "product_id": str(item.get("productId") or ""),
        "name": _clean_title(str(item.get("title") or "")),
        "query": query,
        "category": str(item.get("category4") or item.get("category3") or "수납·정리"),
        "category1": str(item.get("category1") or ""),
        "brand": str(item.get("brand") or ""),
        "maker": str(item.get("maker") or ""),
        "market_low_price": int(price_text),
        "market_link": str(item.get("link") or ""),
        "image_url": str(item.get("image") or ""),
        "mall_name": str(item.get("mallName") or "unknown"),
    }


def _eligible(item: dict[str, Any]) -> tuple[bool, str]:
    if item["category1"] not in SAFE_CATEGORY1:
        return False, "허용하지 않은 상위 category"
    if any(term in item["name"] for term in RESTRICTED_TERMS):
        return False, "규제·안전 범위 keyword 포함"
    if item["market_low_price"] < MIN_ITEM_PRICE:
        return False, "낮은 객단가로 배송·수수료 흡수 곤란"
    return True, ""


def _competitor_evidence(
    client: httpx.Client,
    headers: dict[str, str],
    anchor: dict[str, Any],
) -> dict[str, Any]:
    payload = _naver_search(client, headers, anchor["name"], display=40)
    matches: list[dict[str, Any]] = []
    for raw in payload.get("items", []):
        item = _normalize_item(raw, anchor["query"])
        if not item:
            continue
        same_catalog = bool(anchor["product_id"] and item["product_id"] == anchor["product_id"])
        similarity = _similarity(anchor["name"], item["name"])
        if same_catalog or similarity >= 0.72:
            matches.append({**item, "title_similarity": round(similarity, 3)})
    prices = sorted(item["market_low_price"] for item in matches)
    malls = sorted({item["mall_name"] for item in matches})
    return {
        "result_count": int(payload.get("total") or 0),
        "sample_size": len(prices),
        "sample_mall_count": len(malls),
        "median_price": int(statistics.median(prices)) if prices else None,
        "price_p25": prices[len(prices) // 4] if prices else None,
        "price_p75": prices[(len(prices) * 3) // 4] if prices else None,
        "competitor_samples": [
            {"name": item["name"], "price": item["market_low_price"], "mall": item["mall_name"], "link": item["market_link"]}
            for item in matches[:8]
        ],
    }


def _candidate_pool(client: httpx.Client, headers: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    unique: dict[str, dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    query_summaries: list[dict[str, Any]] = []
    for query in DISCOVERY_QUERIES:
        payload = _naver_search(client, headers, query)
        accepted_count = 0
        for raw in payload.get("items", []):
            item = _normalize_item(raw, query)
            if not item:
                continue
            allowed, reason = _eligible(item)
            if not allowed:
                if len(rejected) < 30:
                    rejected.append({"query": item["name"], "reason": reason, "median_price": item["market_low_price"]})
                continue
            key = item["product_id"] or re.sub(r"\s+", "", item["name"].lower())
            unique.setdefault(key, item)
            accepted_count += 1
        query_summaries.append({"query": query, "result_count": int(payload.get("total") or 0), "eligible_sample_count": accepted_count})

    # Evaluate a bounded evidence packet; favor prices that can absorb delivery while avoiding very bulky/expensive items.
    anchors = sorted(unique.values(), key=lambda row: (abs(row["market_low_price"] - 22_000), row["name"]))[:10]
    enriched = [{**item, **_competitor_evidence(client, headers, item)} for item in anchors]
    return enriched, rejected, query_summaries


def _ollama_select(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    host = os.getenv("RECOMMERCE_OLLAMA_HOST", os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
    model = os.getenv("RECOMMERCE_OLLAMA_MODEL", "gemma4:latest").strip()
    evidence = [
        {
            "id": item["id"], "name": item["name"], "category": item["category"],
            "market_low_price": item["market_low_price"], "sample_size": item["sample_size"],
            "sample_mall_count": item["sample_mall_count"], "price_p25": item["price_p25"],
            "median_price": item["median_price"], "price_p75": item["price_p75"],
            "competitor_samples": item["competitor_samples"][:3],
        }
        for item in candidates
    ]
    prompt = (
        "당신은 초보 셀러를 보호하는 한국 온라인커머스 상품심사자다. 제공된 데이터 밖의 사실을 만들지 마라. "
        "도매가 배수로 판매가를 정하지 말고 경쟁가격, 가격분산, 판매처 표본, 낮은 객단가와 배송비 위험을 먼저 본다. "
        "조금이라도 애매하면 탈락시키고 점수 75 미만은 선택하지 마라. 반드시 상품을 고를 필요는 없다. "
        "최대 3개만 OJT 조사대상으로 고른다. 근거 부족이면 아무것도 고르지 않는다. 실제 매입 추천은 금지다. "
        "selected 최대 3개, rejected 최대 5개만 짧게 쓴다. JSON 외 텍스트는 금지다. "
        "형식: {\"status\":\"selected|no_selection\",\"selected\":[{\"id\":\"...\",\"score\":0,"
        "\"reason\":\"...\",\"risks\":[\"...\"],\"training_goal\":\"...\"}],\"rejected\":[{\"id\":\"...\",\"reason\":\"...\"}]}\n"
        f"evidence={json.dumps(evidence, ensure_ascii=False)}"
    )
    output_schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["selected", "no_selection"]},
            "selected": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}, "score": {"type": "integer"},
                        "reason": {"type": "string", "maxLength": 180},
                        "risks": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 100}},
                        "training_goal": {"type": "string", "maxLength": 180},
                    },
                    "required": ["id", "score", "reason", "risks", "training_goal"],
                },
            },
            "rejected": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "reason": {"type": "string", "maxLength": 140}},
                    "required": ["id", "reason"],
                },
            },
        },
        "required": ["status", "selected", "rejected"],
    }
    response = httpx.post(
        f"{host}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": output_schema,
            "options": {"temperature": 0, "num_ctx": 16384, "num_predict": 2000},
        },
        timeout=float(os.getenv("RECOMMERCE_OLLAMA_TIMEOUT", "240")),
    )
    response.raise_for_status()
    text = str(((response.json().get("message") or {}).get("content") or "")).strip()
    try:
        decision = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        decision = json.loads(match.group(0))
    if not isinstance(decision, dict) or not isinstance(decision.get("selected"), list):
        raise ValueError("invalid_llm_selection_schema")
    return decision, {"provider": "ollama", "model": model, "required": True}


def _apply_selection(
    candidates: list[dict[str, Any]],
    decision: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {item["id"]: item for item in candidates}
    selected: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for choice in decision.get("selected", [])[:MAX_SHORTLIST]:
        item_id = str(choice.get("id") or "")
        item = by_id.get(item_id)
        if not item or item_id in seen:
            continue
        seen.add(item_id)
        if any(_similarity(item["name"], prior["name"]) >= 0.65 for prior in selected):
            blocked.append({"query": item["name"], "reason": "선정 상품과 동일·유사 SKU 중복", "median_price": item["median_price"]})
            continue
        failures = []
        if item["sample_size"] < profile["minimum_competitor_samples"]:
            failures.append(f"고유사도 경쟁가격 표본 {profile['minimum_competitor_samples']}개 미만")
        if item["sample_mall_count"] < profile["minimum_competitor_malls"]:
            failures.append(f"독립 판매처 표본 {profile['minimum_competitor_malls']}곳 미만")
        if not item["price_p25"] or item["price_p25"] < profile["minimum_item_price"]:
            failures.append("보수적 경쟁가격이 최소 객단가 미달")
        price_spread_ratio = (
            float(item["price_p75"]) / float(item["price_p25"])
            if item["price_p25"] and item["price_p75"] else 999.0
        )
        if price_spread_ratio > profile["maximum_price_spread_ratio"]:
            failures.append("경쟁가격 분산 과다")
        llm_score = max(0, min(100, int(choice.get("score") or 0)))
        if llm_score < profile["minimum_llm_score"]:
            failures.append(f"LLM 보수점수 {profile['minimum_llm_score']}점 미만")
        if not item["product_id"] or not item["image_url"]:
            failures.append("상품 동일성 식별자 또는 이미지 누락")
        conservative_sale_price = int(item["price_p25"] or 0)
        max_supply_cost = int(
            conservative_sale_price
            * (1 - CONSERVATIVE_PLATFORM_FEE_RATE - CONSERVATIVE_RETURN_RESERVE_RATE - CONSERVATIVE_AD_RATE - TARGET_CONTRIBUTION_RATE)
            - CONSERVATIVE_SHIPPING_COST
            - CONSERVATIVE_LABOR_PACKAGING_COST
        )
        if max_supply_cost < profile["minimum_allowable_supply_cost"]:
            failures.append(f"최악비용 역산 후 허용 공급가 {profile['minimum_allowable_supply_cost']:,}원 미만")
        if failures:
            blocked.append({"query": item["name"], "reason": " · ".join(failures), "median_price": item["median_price"]})
            continue
        selected.append({
            **item,
            "rank": len(selected) + 1,
            "why": str(choice.get("reason") or "LLM evidence review")[:300],
            "training_goal": str(choice.get("training_goal") or "동일상품 총 결제가격과 공급조건을 검증합니다.")[:240],
            "risks": [str(value)[:160] for value in choice.get("risks", [])[:5]],
            "llm_score": llm_score,
            "conservative_sale_price": conservative_sale_price,
            "max_allowable_supply_cost": max_supply_cost,
            "price_spread_ratio": round(price_spread_ratio, 3),
            "selection_profile": profile["id"],
            "selection_profile_label": profile["label"],
            "adaptive_selection_note": (
                "엄격 기준 통과 상품이 없어, 공개된 적응 기준으로만 재심사해 선정했습니다."
                if profile["adaptive"] else "엄격 기준을 그대로 통과했습니다."
            ),
            "selection_scope": "ojt_research_target_only",
            "shipping_evidence_status": "not_available_from_naver_api",
            "commercial_readiness": "blocked_until_supplier_and_shipping_evidence",
        })
    return selected, blocked


def _selection_policy() -> dict[str, Any]:
    return {
        "human_manual_selection_allowed": False,
        "llm_required": True,
        "fail_closed": True,
        "adaptive_fallback_enabled": True,
        "profiles": list(SELECTION_PROFILES),
        "worst_case_cost_assumptions": {
            "platform_fee_rate": CONSERVATIVE_PLATFORM_FEE_RATE,
            "return_reserve_rate": CONSERVATIVE_RETURN_RESERVE_RATE,
            "ad_rate": CONSERVATIVE_AD_RATE,
            "target_contribution_rate": TARGET_CONTRIBUTION_RATE,
            "shipping_cost": CONSERVATIVE_SHIPPING_COST,
            "labor_packaging_cost": CONSERVATIVE_LABOR_PACKAGING_COST,
        },
    }


def run_market_research(
    path: Path,
    *,
    client_id: str | None = None,
    client_secret: str | None = None,
    llm_selector: LLMSelector | None = None,
) -> dict[str, Any]:
    client_id = (client_id or os.getenv("NAVER_CLIENT_ID", "")).strip()
    client_secret = (client_secret or os.getenv("NAVER_CLIENT_SECRET", "")).strip()
    if not client_id or not client_secret:
        raise RuntimeError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET are required")
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    try:
        with httpx.Client(timeout=15) as client:
            pool, rejected, query_summaries = _candidate_pool(client, headers)
    except Exception as exc:
        snapshot = {
            "status": "selection_blocked_source_unavailable",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "source": "Naver Shopping Search API + local Ollama LLM",
            "method_note": "시장 원천 데이터가 완전하게 수집되지 않아 상품을 추천하지 않습니다.",
            "selection_policy": _selection_policy(),
            "llm": {"provider": "ollama", "model": os.getenv("RECOMMERCE_OLLAMA_MODEL", "gemma4:latest"), "required": True, "error": None, "error_detail": "not_called_source_unavailable"},
            "collection_error": type(exc).__name__,
            "candidate_pool_count": 0,
            "candidate_evidence": [],
            "query_summaries": [],
            "candidates": [],
            "rejected": [],
        }

        def replace_source_failure(fresh: dict[str, Any]) -> None:
            fresh.clear()
            fresh.update(snapshot)

        update_json_atomic(path, replace_source_failure)
        return snapshot

    selector = llm_selector or _ollama_select
    selected_profile = SELECTION_PROFILES[-1]
    strict_candidate_count = 0
    try:
        decision, llm_meta = selector(pool)
        selected = []
        gate_rejections = []
        for profile in SELECTION_PROFILES:
            profile_selected, profile_rejections = _apply_selection(pool, decision, profile)
            if profile["id"] == "strict":
                strict_candidate_count = len(profile_selected)
            gate_rejections = profile_rejections
            if profile_selected:
                selected = profile_selected
                selected_profile = profile
                break
        status = "llm_selected_ojt_targets_not_purchase_recommendation" if selected else "selection_blocked_no_evidence_qualified_product"
        llm_error = None
    except Exception as exc:
        selected, gate_rejections = [], []
        status = "selection_blocked_llm_unavailable"
        llm_meta = {"provider": "ollama", "required": True, "model": os.getenv("RECOMMERCE_OLLAMA_MODEL", "gemma4:latest")}
        llm_error = type(exc).__name__
        llm_error_detail = str(exc)[:240]
    else:
        llm_error_detail = None

    snapshot = {
        "status": status,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": "Naver Shopping Search API + local Ollama LLM",
        "method_note": "LLM이 실제 API 가격표본만 심사합니다. 배송비는 Naver API에 없어 별도 검증 전 매입·판매가 확정이 금지됩니다.",
        "selection_policy": _selection_policy(),
        "selection_result": {
            "profile_id": selected_profile["id"] if selected else None,
            "profile_label": selected_profile["label"] if selected else None,
            "adaptive": bool(selected and selected_profile["adaptive"]),
            "strict_candidate_count": strict_candidate_count,
            "fallback_profiles_checked": [profile["id"] for profile in SELECTION_PROFILES],
        },
        "llm": {**llm_meta, "error": llm_error, "error_detail": llm_error_detail},
        "query_summaries": query_summaries,
        "candidate_pool_count": len(pool),
        "candidate_evidence": pool,
        "candidates": selected,
        "rejected": (gate_rejections + rejected)[:40],
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
