from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.database import execute_query

ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "docs" / "trading" / "universe.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_trading_db_url() -> None:
    if os.getenv("TRADING_DATABASE_URL"):
        os.environ["DATABASE_URL"] = os.environ["TRADING_DATABASE_URL"]
        return
    if os.getenv("TRADING_USE_PROD_DB", "true").strip().lower() in {"1", "true", "yes", "on"}:
        os.environ["DATABASE_URL"] = "postgresql://localhost/harness_prod"


def ensure_trading_schema() -> None:
    ensure_trading_db_url()
    statements = [
        "ALTER TABLE raw_signals ADD COLUMN IF NOT EXISTS domain VARCHAR(64) DEFAULT 'physical_ai'",
        "CREATE INDEX IF NOT EXISTS idx_raw_signals_domain ON raw_signals(domain)",
        "ALTER TABLE filtered_signals ADD COLUMN IF NOT EXISTS extracted_facts JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE filtered_signals ADD COLUMN IF NOT EXISTS domain VARCHAR(64) DEFAULT 'physical_ai'",
        "CREATE INDEX IF NOT EXISTS idx_filtered_signals_domain_created_at ON filtered_signals(domain, created_at DESC)",
        "ALTER TABLE signals ADD COLUMN IF NOT EXISTS domain VARCHAR(64) DEFAULT 'physical_ai'",
        "CREATE INDEX IF NOT EXISTS idx_signals_domain_created_at ON signals(domain, created_at DESC)",
    ]
    for stmt in statements:
        execute_query(stmt)


def _load_seed_registry() -> list[dict[str, Any]]:
    if UNIVERSE_PATH.exists():
        try:
            data = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except Exception:
            pass
    return [
        {"region": "US", "symbol": "NVDA", "exchange": "SMART", "currency": "USD", "name": "NVIDIA", "sector": "AI Chip"},
        {"region": "US", "symbol": "AVGO", "exchange": "SMART", "currency": "USD", "name": "Broadcom", "sector": "AI Chip"},
        {"region": "US", "symbol": "TSM", "exchange": "SMART", "currency": "USD", "name": "TSMC ADR", "sector": "Foundry"},
        {"region": "US", "symbol": "MU", "exchange": "SMART", "currency": "USD", "name": "Micron Technology", "sector": "Memory"},
        {"region": "US", "symbol": "ANET", "exchange": "SMART", "currency": "USD", "name": "Arista Networks", "sector": "AI Network"},
        {"region": "US", "symbol": "VRT", "exchange": "SMART", "currency": "USD", "name": "Vertiv", "sector": "Power Infra"},
        {"region": "US", "symbol": "TER", "exchange": "SMART", "currency": "USD", "name": "Teradyne", "sector": "Test Equip"},
        {"region": "US", "symbol": "SYM", "exchange": "SMART", "currency": "USD", "name": "Symbotic", "sector": "Robotics"},
        {"region": "US", "symbol": "ISRG", "exchange": "SMART", "currency": "USD", "name": "Intuitive Surgical", "sector": "Medical Robot"},
        {"region": "US", "symbol": "ROK", "exchange": "SMART", "currency": "USD", "name": "Rockwell Automation", "sector": "Industrial Auto"},
        {"region": "US", "symbol": "GOOG", "exchange": "NASDAQ", "currency": "USD", "name": "Alphabet", "sector": "AI Platform"},
        {"region": "US", "symbol": "TSLA", "exchange": "NASDAQ", "currency": "USD", "name": "Tesla", "sector": "Humanoid Robotics"},
        {"region": "US", "symbol": "META", "exchange": "NASDAQ", "currency": "USD", "name": "Meta Platforms", "sector": "AI Platform"},
        {"region": "KR", "symbol": "005930", "exchange": "KRX", "currency": "KRW", "name": "삼성전자", "sector": "Memory/Foundry"},
        {"region": "KR", "symbol": "000660", "exchange": "KRX", "currency": "KRW", "name": "SK하이닉스", "sector": "HBM Memory"},
        {"region": "KR", "symbol": "042700", "exchange": "KRX", "currency": "KRW", "name": "한미반도체", "sector": "Chip Equip"},
        {"region": "KR", "symbol": "005380", "exchange": "KRX", "currency": "KRW", "name": "현대차", "sector": "Physical AI Deployment"},
        {"region": "JP", "symbol": "8035", "exchange": "TSEJ", "currency": "JPY", "name": "Tokyo Electron", "sector": "Chip Equip"},
        {"region": "JP", "symbol": "6861", "exchange": "TSEJ", "currency": "JPY", "name": "Keyence", "sector": "Factory Auto"},
        {"region": "JP", "symbol": "6954", "exchange": "TSEJ", "currency": "JPY", "name": "FANUC", "sector": "Robotics"},
    ]


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _alias_map(symbol: str, name: str) -> list[str]:
    base = {_normalize(symbol), _normalize(name)}
    manual = {
        "NVDA": ["nvidia", "gr00t", "cosmos", "h100", "gb200"],
        "AVGO": ["broadcom", "custom ai asic", "vmware"],
        "TSM": ["tsmc", "taiwan semiconductor", "2nm", "wafer"],
        "MU": ["micron", "hbm", "hbm4", "hbm3e"],
        "ANET": ["arista", "ethernet switch", "ai networking"],
        "VRT": ["vertiv", "liquid cooling", "data center cooling"],
        "TER": ["teradyne", "universal robots"],
        "SYM": ["symbotic", "warehouse automation"],
        "ISRG": ["intuitive surgical", "da vinci"],
        "ROK": ["rockwell automation"],
        "GOOG": ["google", "alphabet", "deepmind", "gemini robotics"],
        "TSLA": ["tesla", "optimus"],
        "META": ["meta", "llama"],
        "005930": ["삼성전자", "samsung electronics", "samsung"],
        "000660": ["sk하이닉스", "sk hynix", "hynix"],
        "042700": ["한미반도체", "hanmi semiconductor"],
        "005380": ["현대차", "hyundai", "hyundai motor", "metaplant"],
        "8035": ["tokyo electron"],
        "6861": ["keyence"],
        "6954": ["fanuc"],
    }
    base.update(_normalize(item) for item in manual.get(symbol, []))
    return [item for item in base if item]


def _alias_patterns(symbol: str, name: str) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for alias in _alias_map(symbol, name):
        if re.fullmatch(r"[a-z0-9.\-]+", alias):
            patterns.append(re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"))
        else:
            patterns.append(re.compile(re.escape(alias)))
    return patterns


@dataclass
class EvidenceRow:
    title: str
    summary: str
    full_content: str
    score: float
    source: str
    created_at: str

    @property
    def text(self) -> str:
        return _normalize(" ".join([self.title, self.summary, self.full_content[:4000]]))


def _load_candidate_rows(domain: str, lookback_days: int) -> list[EvidenceRow]:
    ensure_trading_db_url()
    rows = execute_query(
        """
        SELECT
            fs.title,
            fs.summary,
            COALESCE(rs.full_content, '') AS full_content,
            COALESCE(fs.score, 0) AS score,
            fs.source,
            fs.created_at::text AS created_at
        FROM filtered_signals fs
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE COALESCE(fs.domain, %s) = %s
          AND COALESCE(rs.domain, rs.raw_data->>'domain', %s) = %s
          AND fs.created_at >= NOW() - (%s || ' days')::interval
        ORDER BY fs.created_at DESC, fs.score DESC
        """,
        (domain, domain, domain, domain, str(lookback_days)),
        fetch=True,
    )
    return [
        EvidenceRow(
            title=row.get("title") or "",
            summary=row.get("summary") or "",
            full_content=row.get("full_content") or "",
            score=float(row.get("score") or 0.0),
            source=row.get("source") or "",
            created_at=row.get("created_at") or "",
        )
        for row in rows
    ]


_RELIABILITY_CACHE: dict[str, float] | None = None


def _reliability_map() -> dict[str, float]:
    """source_catalog의 소스별 신뢰도(1회 캐시)."""
    global _RELIABILITY_CACHE
    if _RELIABILITY_CACHE is not None:
        return _RELIABILITY_CACHE
    out: dict[str, float] = {}
    try:
        for r in execute_query("SELECT source_name, reliability_score FROM source_catalog", fetch=True) or []:
            if r.get("reliability_score") is not None:
                out[str(r["source_name"])] = float(r["reliability_score"])
    except Exception:
        pass
    _RELIABILITY_CACHE = out
    return out


def _reliability_for(source: str) -> float:
    """소스 신뢰도(0~1). 카탈로그에 없으면 prefix 휴리스틱 → 기본 0.55."""
    src = source or ""
    m = _reliability_map()
    if src in m:
        return m[src]
    low = src.lower()
    if low.startswith("arxiv"):
        return 0.85
    if "ieee" in low or "mit" in low:
        return 0.8
    if low.startswith("google_news") or "news" in low:
        return 0.6
    if low.startswith("youtube"):
        return 0.5
    if low.startswith("naver"):
        return 0.45
    return 0.55


def _recency_factor(created_at: str, lookback_days: int) -> float:
    """최신 evidence 우대(오늘=1.0 → 윈도우 끝=0.4)."""
    try:
        ts = datetime.fromisoformat((created_at or "").replace("Z", "+00:00")) if created_at else None
    except Exception:
        ts = None
    if ts is None:
        return 0.7
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / 86400.0)
    return 0.4 + 0.6 * max(0.0, 1.0 - age_days / max(1, lookback_days))


def build_trading_universe(domain: str = "physical_ai", lookback_days: int = 45, max_symbols: int = 24) -> list[dict[str, Any]]:
    ensure_trading_db_url()
    ensure_trading_schema()
    registry = _load_seed_registry()
    evidence_rows = _load_candidate_rows(domain, lookback_days)
    if not evidence_rows:
        return []

    scores: dict[str, dict[str, Any]] = {}
    for item in registry:
        symbol = item["symbol"]
        alias_patterns = _alias_patterns(symbol, item.get("name", ""))
        total = 0.0
        matched_titles: list[str] = []
        matched_sources: set[str] = set()
        seen_titles: set[str] = set()
        evidence_count = 0
        for row in evidence_rows:
            if any(pattern.search(row.text) for pattern in alias_patterns):
                # 교차게재/중복 제목(같은 논문 cs.AI+cs.LG 등)은 1회만 카운트 — 인플레 방지
                tkey = _normalize(row.title)[:80]
                if tkey and tkey in seen_titles:
                    continue
                if tkey:
                    seen_titles.add(tkey)
                # 품질 가중치: 관련도(score) × 소스 신뢰도 × 최신성
                weight = max(0.2, row.score) * _reliability_for(row.source) * _recency_factor(row.created_at, lookback_days)
                total += weight
                evidence_count += 1
                matched_sources.add(row.source)
                if row.title and row.title not in matched_titles:
                    matched_titles.append(row.title)
        if evidence_count == 0:
            continue
        distinct_sources = len(matched_sources)
        # 양(volume)보다 서로 다른 소스의 교차 확인(diversity)을 우대 →
        # 한 소스 대량 멘션보다 여러 채널 동시 포착이 강한 신호
        harness_score = min(10, max(1, round(total * 3.0 + distinct_sources * 0.6)))
        selection_reason = "; ".join(matched_titles[:3])[:500]
        scores[symbol] = {
            **item,
            "harness_score": harness_score,
            "evidence_count": evidence_count,
            "evidence_score": round(total, 3),
            "distinct_sources": distinct_sources,
            "selection_reason": selection_reason,
            "matched_sources": sorted(matched_sources),
            "brokers": ["alpaca", "ibkr"] if item.get("region") == "US" else ["ibkr"],
        }

    ranked = sorted(
        scores.values(),
        key=lambda row: (row["harness_score"], row["evidence_score"], row.get("distinct_sources", 0), row["evidence_count"]),
        reverse=True,
    )[:max_symbols]
    ranked = _translate_reasons_ko(ranked)
    return ranked


def explain_trading_symbol(symbol: str, domain: str = "physical_ai", lookback_days: int = 45, limit: int = 5) -> list[dict[str, Any]]:
    ensure_trading_db_url()
    ensure_trading_schema()
    registry = _load_seed_registry()
    meta = next((row for row in registry if row.get("symbol") == symbol), None)
    if not meta:
        return []
    alias_patterns = _alias_patterns(symbol, meta.get("name", ""))
    matches: list[dict[str, Any]] = []
    for row in _load_candidate_rows(domain, lookback_days):
        if any(pattern.search(row.text) for pattern in alias_patterns):
            matches.append({
                "title": row.title,
                "summary": row.summary[:400],
                "source": row.source,
                "score": round(row.score, 3),
                "created_at": row.created_at,
            })
    matches.sort(key=lambda item: (item["score"], item["created_at"]), reverse=True)
    return matches[:limit]


def write_trading_universe(universe: list[dict[str, Any]], output_path: Path = UNIVERSE_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(universe, ensure_ascii=False, indent=2), encoding="utf-8")


def _translate_reasons_ko(universe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """selection_reason_ko가 없는 항목을 Claude Haiku로 일괄 번역."""
    to_translate = {
        row["symbol"]: row["selection_reason"]
        for row in universe
        if row.get("symbol") and row.get("selection_reason") and not row.get("selection_reason_ko")
    }
    if not to_translate:
        return universe
    ko_map: dict[str, str] = {}
    try:
        import anthropic as _ant
        client = _ant.Anthropic()
        input_text = json.dumps(to_translate, ensure_ascii=False)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=(
                "영어 기사 제목들을 한국어로 번역하세요.\n"
                "입력 형식: {\"심볼\": \"title1; title2; title3\", ...}\n"
                "출력 형식: {\"심볼\": \"한국어1; 한국어2; 한국어3\", ...}\n"
                "규칙: 세미콜론 구분 유지. 번역 결과만 포함된 JSON만 반환. 설명 금지."
            ),
            messages=[{"role": "user", "content": input_text}],
        )
        raw = resp.content[0].text.strip() if resp.content else "{}"
        parsed = json.loads(raw)
        ko_map = {k: str(v) for k, v in parsed.items() if k in to_translate}
    except Exception:
        pass
    result = []
    for row in universe:
        sym = row.get("symbol", "")
        if sym in ko_map:
            result.append({**row, "selection_reason_ko": ko_map[sym]})
        else:
            result.append(row)
    return result


def enrich_universe_ko(output_path: Path = UNIVERSE_PATH) -> int:
    """기존 universe.json에 selection_reason_ko 필드 추가. 업데이트된 항목 수 반환."""
    universe, source = load_trading_universe()
    if source == "fallback":
        return 0
    enriched = _translate_reasons_ko(universe)
    changed = sum(
        1 for old, new in zip(universe, enriched)
        if old.get("selection_reason_ko") != new.get("selection_reason_ko")
    )
    if changed > 0:
        write_trading_universe(enriched, output_path)
    return changed


def load_trading_universe(broker: str | None = None, fallback: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], str]:
    if UNIVERSE_PATH.exists():
        try:
            data = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                if broker:
                    data = [row for row in data if broker in row.get("brokers", [broker])]
                return data, "universe.json"
        except Exception:
            pass
    fallback_rows = fallback or _load_seed_registry()
    if broker:
        if broker == "alpaca":
            fallback_rows = [row for row in fallback_rows if row.get("region") == "US"]
    return fallback_rows, "fallback"
