"""Safe runtime workspace for the recommerce opportunity discovery dashboard."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.atomic_io import update_json_atomic


CHECKLIST_ITEMS = (
    ("roles", "두 운영자 역할 확정"),
    ("time_cap", "주당 시간 한도 확정"),
    ("blocked_categories", "SKU 금지 목록 승인"),
    ("economics_sheet", "손익 계산 기준 확인"),
    ("supplier_questions", "공급처 인터뷰 질문 작성"),
    ("supplier_list", "후보 공급처 20곳 작성"),
    ("sku_list", "후보 SKU 30개 기록 시작"),
    ("day10_review", "Day 10 stop/go 회의 일정 확정"),
)

ALLOWED_CATEGORIES = {
    "stationery": "문구·사무용품",
    "storage_organization": "수납·정리용품",
    "non_electric_household_small_goods": "비전기 소형 생활용품",
    "adult_hobby_supplies_non_regulated": "성인 취미용 비규제 용품",
}

RESTRICTED_INDICATORS = (
    "어린이", "아동", "유아", "베이비", "키즈", "전기", "전자", "배터리", "충전",
    "식품", "먹는", "건강기능", "영양제", "화장품", "의료", "치료", "유통기한",
    "명품", "정품", "브랜드", "의류", "신발", "설치", "대형",
    "child", "children", "baby", "kids", "electric", "electronic", "battery", "food",
    "supplement", "cosmetic", "medical", "expiry", "luxury", "authentic", "apparel",
    "shoes", "installation", "oversized",
)

CONTACT_STATUSES = {"not_contacted", "contacted", "interviewed"}
EVIDENCE_STATUSES = {"unverified", "requested", "verified"}
SCORE_KEYS = ("demand", "supply", "competition", "shipping", "returns", "evidence", "turnover", "content")
COST_KEYS = (
    "unit_purchase_cost",
    "platform_fee",
    "inbound_shipping",
    "outbound_shipping",
    "packaging_cost",
    "ad_coupon_cost",
    "return_defect_reserve",
    "labor_cost",
    "aging_markdown_loss",
    "dispute_tax_reserve",
)
OPTIONAL_ZERO_COST_KEYS = tuple(key for key in COST_KEYS if key != "unit_purchase_cost")


class WorkspaceValidationError(ValueError):
    pass


class WorkspaceConflictError(RuntimeError):
    def __init__(self, workspace: dict[str, Any]):
        super().__init__("workspace version conflict")
        self.workspace = workspace


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_workspace() -> dict[str, Any]:
    return {
        "workspace_version": 0,
        "weekly_hours": 0.0,
        "checklist": {key: False for key, _ in CHECKLIST_ITEMS},
        "suppliers": [],
        "sku_candidates": [],
        "updated_at": None,
        "updated_by": None,
    }


def _text(value: Any, field: str, max_length: int, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise WorkspaceValidationError(f"{field} is required")
    if len(text) > max_length:
        raise WorkspaceValidationError(f"{field} is too long")
    return text


def _number(value: Any, field: str, *, minimum: float = 0.0, maximum: float = 1_000_000_000.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise WorkspaceValidationError(f"{field} must be numeric") from exc
    if number < minimum or number > maximum:
        raise WorkspaceValidationError(f"{field} is out of range")
    return round(number, 2)


def _integer(value: Any, field: str, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise WorkspaceValidationError(f"{field} must be an integer") from exc
    if number < minimum or number > maximum:
        raise WorkspaceValidationError(f"{field} is out of range")
    return number


def _date(value: Any, field: str) -> str:
    text = _text(value, field, 10)
    if not text:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise WorkspaceValidationError(f"{field} must be YYYY-MM-DD")
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise WorkspaceValidationError(f"{field} is not a valid date") from exc
    return text


def _restricted_text(*values: str) -> str | None:
    haystack = " ".join(values).casefold()
    return next((indicator for indicator in RESTRICTED_INDICATORS if indicator.casefold() in haystack), None)


def _normalize_scores(raw: Any) -> dict[str, int]:
    source = raw if isinstance(raw, dict) else {}
    return {key: _integer(source.get(key, 0), f"scores.{key}", minimum=0, maximum=5) for key in SCORE_KEYS}


def _normalize_supplier(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    supplier_id = _text(raw.get("id"), "supplier.id", 80)
    name = _text(raw.get("name"), "supplier.name", 80)
    if not supplier_id or not name:
        return None
    contact_status = str(raw.get("contact_status") or "not_contacted")
    evidence_status = str(raw.get("evidence_status") or "unverified")
    if contact_status not in CONTACT_STATUSES:
        contact_status = "not_contacted"
    if evidence_status not in EVIDENCE_STATUSES:
        evidence_status = "unverified"
    return {
        "id": supplier_id,
        "name": name,
        "contact_status": contact_status,
        "evidence_status": evidence_status,
        "available_quantity": max(0, int(raw.get("available_quantity") or 0)),
        "quote_valid_until": _date(raw.get("quote_valid_until"), "supplier.quote_valid_until"),
        "note": _text(raw.get("note"), "supplier.note", 240),
        "created_at": _text(raw.get("created_at"), "supplier.created_at", 50),
    }


def _sku_view(raw: dict[str, Any]) -> dict[str, Any]:
    sale_price = float(raw.get("conservative_sale_price") or 0)
    cost_total = round(sum(float(raw.get(key) or 0) for key in COST_KEYS), 2)
    contribution = round(sale_price - cost_total, 2)
    contribution_rate = round((contribution / sale_price) * 100, 1) if sale_price > 0 else 0.0
    scores = _normalize_scores(raw.get("scores"))
    total_score = sum(scores.values())
    cost_review_condition_met = contribution_rate >= 20 and total_score >= 30 and scores["evidence"] >= 4
    return {
        **raw,
        "scores": scores,
        "full_variable_cost": cost_total,
        "contribution": contribution,
        "contribution_rate": contribution_rate,
        "total_score": total_score,
        "cost_review_condition_met": cost_review_condition_met,
    }


def _normalize_sku(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    sku_id = _text(raw.get("id"), "sku.id", 80)
    name = _text(raw.get("name"), "sku.name", 100)
    if not sku_id or not name:
        return None
    category = str(raw.get("category") or "")
    if category not in ALLOWED_CATEGORIES:
        return None
    note = _text(raw.get("note"), "sku.note", 240)
    if _restricted_text(name, note):
        return None
    item = {
        "id": sku_id,
        "name": name,
        "supplier_id": _text(raw.get("supplier_id"), "sku.supplier_id", 80),
        "category": category,
        "conservative_sale_price": _number(raw.get("conservative_sale_price", 0), "conservative_sale_price"),
        **{key: _number(raw.get(key, 0), key) for key in COST_KEYS},
        "zero_cost_confirmed": bool(raw.get("zero_cost_confirmed")),
        "evidence_status": str(raw.get("evidence_status") or "unverified"),
        "scores": _normalize_scores(raw.get("scores")),
        "note": note,
        "created_at": _text(raw.get("created_at"), "sku.created_at", 50),
    }
    if item["evidence_status"] not in EVIDENCE_STATUSES:
        item["evidence_status"] = "unverified"
    return _sku_view(item)


def normalize_workspace(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    workspace = empty_workspace()
    workspace["workspace_version"] = max(0, int(source.get("workspace_version") or 0))
    try:
        workspace["weekly_hours"] = _number(source.get("weekly_hours", 0), "weekly_hours", maximum=168)
    except WorkspaceValidationError:
        workspace["weekly_hours"] = 0.0
    checklist = source.get("checklist") if isinstance(source.get("checklist"), dict) else {}
    workspace["checklist"] = {key: bool(checklist.get(key)) for key, _ in CHECKLIST_ITEMS}
    workspace["suppliers"] = [item for item in (_normalize_supplier(row) for row in source.get("suppliers", [])) if item]
    workspace["sku_candidates"] = [item for item in (_normalize_sku(row) for row in source.get("sku_candidates", [])) if item]
    workspace["updated_at"] = _text(source.get("updated_at"), "updated_at", 50) or None
    workspace["updated_by"] = _text(source.get("updated_by"), "updated_by", 20) or None
    return workspace


def _read_workspace(path: Path) -> dict[str, Any]:
    try:
        return normalize_workspace(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else empty_workspace()
    except Exception:
        return empty_workspace()


def workspace_view(raw: Any) -> dict[str, Any]:
    state = normalize_workspace(raw)
    completed = sum(1 for value in state["checklist"].values() if value)
    verified_suppliers = sum(1 for item in state["suppliers"] if item["evidence_status"] == "verified")
    qualified_skus = sum(1 for item in state["sku_candidates"] if item["cost_review_condition_met"])
    stop_reasons: list[str] = []
    if state["weekly_hours"] > 6:
        stop_reasons.append("주간 투입시간이 6시간 한도를 초과했습니다. 신규 조사·등록을 중단하세요.")
    if any(item["contribution_rate"] < 20 for item in state["sku_candidates"]):
        stop_reasons.append("공헌이익률 20% 미만 SKU가 있습니다. 비용을 다시 확인하세요.")
    next_action = "Phase 0 체크리스트를 한 항목씩 완료하세요."
    if completed == len(CHECKLIST_ITEMS):
        next_action = "증빙 가능한 공급처 후보를 등록하세요."
    if completed == len(CHECKLIST_ITEMS) and state["suppliers"]:
        next_action = "허용 카테고리 안에서 SKU 후보 비용을 검토하세요."
    return {
        "opportunity": {
            "id": "HOP-2026-07-19-RECOMMERCE-01",
            "name": "Harness Value Recovery Mall",
            "status": "opportunity_candidate",
            "track": "보조 discovery track",
        },
        "guardrails": {
            "allowed": ["조사", "인터뷰", "무매입 Pretotyping"],
            "blocked": ["상품 매입", "판매", "유료 광고", "예약금", "외부 공개"],
            "weekly_hours_cap": 6,
            "workspace_scope": "Phase 0~2 only",
        },
        "phases": [
            {"id": 0, "label": "안전 경계", "state": "active"},
            {"id": 1, "label": "공급 검증", "state": "workspace"},
            {"id": 2, "label": "무매입 관심 검증", "state": "workspace"},
            {"id": 3, "label": "소량 판매 승인안", "state": "locked"},
            {"id": 4, "label": "운영 검증", "state": "locked"},
        ],
        "checklist": [
            {"key": key, "label": label, "completed": state["checklist"][key]}
            for key, label in CHECKLIST_ITEMS
        ],
        "suppliers": deepcopy(state["suppliers"]),
        "sku_candidates": deepcopy(state["sku_candidates"]),
        "metrics": {
            "weekly_hours": state["weekly_hours"],
            "checklist_completed": completed,
            "checklist_total": len(CHECKLIST_ITEMS),
            "verified_suppliers": verified_suppliers,
            "supplier_count": len(state["suppliers"]),
            "qualified_skus": qualified_skus,
            "sku_count": len(state["sku_candidates"]),
        },
        "allowed_categories": [{"value": key, "label": label} for key, label in ALLOWED_CATEGORIES.items()],
        "score_keys": list(SCORE_KEYS),
        "cost_keys": list(COST_KEYS),
        "stop_reasons": stop_reasons,
        "next_action": next_action,
        "workspace_version": state["workspace_version"],
        "updated_at": state["updated_at"],
        "updated_by": state["updated_by"],
    }


def get_workspace(path: Path) -> dict[str, Any]:
    return workspace_view(_read_workspace(path))


def _new_supplier(payload: dict[str, Any]) -> dict[str, Any]:
    contact_status = str(payload.get("contact_status") or "not_contacted")
    evidence_status = str(payload.get("evidence_status") or "unverified")
    if contact_status not in CONTACT_STATUSES or evidence_status not in EVIDENCE_STATUSES:
        raise WorkspaceValidationError("invalid supplier status")
    return {
        "id": str(uuid4()),
        "name": _text(payload.get("name"), "supplier.name", 80, required=True),
        "contact_status": contact_status,
        "evidence_status": evidence_status,
        "available_quantity": _integer(payload.get("available_quantity", 0), "available_quantity"),
        "quote_valid_until": _date(payload.get("quote_valid_until"), "quote_valid_until"),
        "note": _text(payload.get("note"), "supplier.note", 240),
        "created_at": _now(),
    }


def _new_sku(payload: dict[str, Any], suppliers: list[dict[str, Any]]) -> dict[str, Any]:
    name = _text(payload.get("name"), "sku.name", 100, required=True)
    note = _text(payload.get("note"), "sku.note", 240)
    category = str(payload.get("category") or "")
    if category not in ALLOWED_CATEGORIES:
        raise WorkspaceValidationError("category is not allowed in v1")
    indicator = _restricted_text(name, note)
    if indicator:
        raise WorkspaceValidationError(f"restricted product indicator: {indicator}")
    supplier_id = _text(payload.get("supplier_id"), "supplier_id", 80)
    if supplier_id and not any(item["id"] == supplier_id for item in suppliers):
        raise WorkspaceValidationError("supplier_id does not exist")
    sale_price = _number(payload.get("conservative_sale_price"), "conservative_sale_price", minimum=1)
    costs = {key: _number(payload.get(key), key, minimum=0) for key in COST_KEYS}
    if costs["unit_purchase_cost"] <= 0:
        raise WorkspaceValidationError("unit_purchase_cost must be greater than zero")
    zero_cost_confirmed = bool(payload.get("zero_cost_confirmed"))
    if any(costs[key] == 0 for key in OPTIONAL_ZERO_COST_KEYS) and not zero_cost_confirmed:
        raise WorkspaceValidationError("zero cost fields require confirmation")
    scores = _normalize_scores(payload.get("scores"))
    evidence_status = str(payload.get("evidence_status") or "unverified")
    if evidence_status not in EVIDENCE_STATUSES:
        raise WorkspaceValidationError("invalid evidence status")
    return _sku_view({
        "id": str(uuid4()),
        "name": name,
        "supplier_id": supplier_id,
        "category": category,
        "conservative_sale_price": sale_price,
        **costs,
        "zero_cost_confirmed": zero_cost_confirmed,
        "evidence_status": evidence_status,
        "scores": scores,
        "note": note,
        "created_at": _now(),
    })


def mutate_workspace(
    path: Path,
    *,
    expected_version: int,
    action: str,
    payload: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    allowed_actions = {"toggle_checklist", "set_weekly_hours", "add_supplier", "delete_supplier", "add_sku", "delete_sku"}
    if action not in allowed_actions:
        raise WorkspaceValidationError("action is not allowed")
    if not isinstance(payload, dict):
        raise WorkspaceValidationError("payload must be an object")

    def mutate(fresh: dict[str, Any]) -> None:
        normalized = normalize_workspace(fresh)
        if normalized["workspace_version"] != expected_version:
            raise WorkspaceConflictError(workspace_view(normalized))
        if action == "toggle_checklist":
            key = _text(payload.get("key"), "checklist.key", 80, required=True)
            if key not in normalized["checklist"]:
                raise WorkspaceValidationError("unknown checklist key")
            normalized["checklist"][key] = bool(payload.get("completed"))
        elif action == "set_weekly_hours":
            normalized["weekly_hours"] = _number(payload.get("hours"), "weekly_hours", maximum=168)
        elif action == "add_supplier":
            normalized["suppliers"].append(_new_supplier(payload))
        elif action == "delete_supplier":
            item_id = _text(payload.get("id"), "supplier.id", 80, required=True)
            if any(item.get("supplier_id") == item_id for item in normalized["sku_candidates"]):
                raise WorkspaceValidationError("supplier is referenced by a SKU")
            supplier_index = next((index for index, item in enumerate(normalized["suppliers"]) if item["id"] == item_id), None)
            if supplier_index is None:
                raise WorkspaceValidationError("supplier not found")
            del normalized["suppliers"][supplier_index]
        elif action == "add_sku":
            normalized["sku_candidates"].append(_new_sku(payload, normalized["suppliers"]))
        elif action == "delete_sku":
            item_id = _text(payload.get("id"), "sku.id", 80, required=True)
            sku_index = next((index for index, item in enumerate(normalized["sku_candidates"]) if item["id"] == item_id), None)
            if sku_index is None:
                raise WorkspaceValidationError("SKU not found")
            del normalized["sku_candidates"][sku_index]
        normalized["workspace_version"] += 1
        normalized["updated_at"] = _now()
        normalized["updated_by"] = actor
        fresh.clear()
        fresh.update(normalized)

    result = update_json_atomic(path, mutate)
    return workspace_view(result)
