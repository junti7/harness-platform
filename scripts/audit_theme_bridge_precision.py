#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.trading_universe import UNIVERSE_PATH, _load_candidate_rows, _load_seed_registry, _alias_patterns, _theme_patterns_for_symbol, _negative_patterns_for_symbol, build_trading_universe  # noqa: E402

OUT_DIR = ROOT / "docs" / "reviews" / "trading_theme_bridge_precision"


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit theme-bridge precision for physical_ai trading universe.")
    parser.add_argument("--domain", default="physical_ai")
    parser.add_argument("--lookback-days", type=int, default=45)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()

    rows = _load_candidate_rows(args.domain, args.lookback_days)
    registry = _load_seed_registry()
    if UNIVERSE_PATH.exists():
        try:
            universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
        except Exception:
            universe = build_trading_universe(domain=args.domain, lookback_days=args.lookback_days, max_symbols=24)
    else:
        universe = build_trading_universe(domain=args.domain, lookback_days=args.lookback_days, max_symbols=24)
    universe_map = {row["symbol"]: row for row in universe}

    audits: list[dict] = []
    total_theme_hits = 0
    total_negative_hits = 0
    total_direct_hits = 0
    matched_any_rows: set[str] = set()
    theme_only_rows: set[str] = set()

    for item in registry:
        symbol = item["symbol"]
        direct_patterns = _alias_patterns(symbol, item.get("name", ""))
        theme_patterns = _theme_patterns_for_symbol(symbol)
        negative_patterns = _negative_patterns_for_symbol(symbol)
        if not theme_patterns and symbol not in universe_map:
            continue

        samples = []
        source_counter = Counter()
        direct_hits = 0
        theme_hits = 0
        negative_hits = 0

        symbol_seen: set[str] = set()
        for row in rows:
            text = row.text
            row_key = f"{row.created_at}|{row.source}|{row.title[:120]}"
            direct = any(p.search(text) for p in direct_patterns)
            matched_theme = None
            matched_negative = None
            if not direct:
                for p, _w in theme_patterns:
                    if p.search(text):
                        matched_theme = p.pattern
                        break
            for p, _w in negative_patterns:
                if p.search(text):
                    matched_negative = p.pattern
                    break
            if not direct and not matched_theme and not matched_negative:
                continue

            if row_key not in symbol_seen:
                symbol_seen.add(row_key)
                matched_any_rows.add(row_key)
                if matched_theme and not direct:
                    theme_only_rows.add(row_key)
            total_direct_hits += 1 if direct else 0
            total_theme_hits += 1 if matched_theme and not direct else 0
            total_negative_hits += 1 if matched_negative else 0
            direct_hits += 1 if direct else 0
            theme_hits += 1 if matched_theme and not direct else 0
            negative_hits += 1 if matched_negative else 0
            source_counter[row.source] += 1

            if len(samples) < args.limit:
                samples.append({
                    "title": row.title,
                    "source": row.source,
                    "created_at": row.created_at,
                    "match_kind": "negative" if matched_negative and not direct and not matched_theme else ("direct" if direct else "theme"),
                    "matched_theme": matched_theme,
                    "matched_negative": matched_negative,
                })

        if direct_hits or theme_hits or negative_hits:
            audits.append({
                "symbol": symbol,
                "name": item.get("name"),
                "harness_score": universe_map.get(symbol, {}).get("harness_score"),
                "direct_hits": direct_hits,
                "theme_hits": theme_hits,
                "negative_hits": negative_hits,
                "theme_share_pct": round((theme_hits / max(1, direct_hits + theme_hits)) * 100, 1),
                "top_sources": source_counter.most_common(5),
                "samples": samples,
            })

    audits.sort(key=lambda row: (row["theme_hits"], row["negative_hits"], row["direct_hits"]), reverse=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = _now_tag()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": args.domain,
        "lookback_days": args.lookback_days,
        "summary": {
            "candidate_rows": len(rows),
            "matched_any_rows": len(matched_any_rows),
            "match_rate_pct": round((len(matched_any_rows) / max(1, len(rows))) * 100, 1),
            "theme_only_rows": len(theme_only_rows),
            "direct_hits": total_direct_hits,
            "theme_hits": total_theme_hits,
            "negative_hits": total_negative_hits,
        },
        "symbols": audits,
    }
    json_path = OUT_DIR / f"trading_theme_bridge_precision_{tag}.json"
    md_path = OUT_DIR / f"trading_theme_bridge_precision_{tag}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Trading Theme Bridge Precision Audit",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- candidate_rows: {payload['summary']['candidate_rows']}",
        f"- matched_any_rows: {payload['summary']['matched_any_rows']}",
        f"- match_rate_pct: {payload['summary']['match_rate_pct']}",
        f"- direct_hits: {payload['summary']['direct_hits']}",
        f"- theme_hits: {payload['summary']['theme_hits']}",
        f"- negative_hits: {payload['summary']['negative_hits']}",
        "",
    ]
    for row in audits[:12]:
        lines.append(f"## {row['symbol']} ({row['name']})")
        lines.append(f"- harness_score: {row.get('harness_score')}")
        lines.append(f"- direct_hits: {row['direct_hits']}")
        lines.append(f"- theme_hits: {row['theme_hits']}")
        lines.append(f"- negative_hits: {row['negative_hits']}")
        lines.append(f"- theme_share_pct: {row['theme_share_pct']}")
        lines.append(f"- top_sources: {row['top_sources']}")
        lines.append("- sample_matches:")
        for sample in row["samples"]:
            lines.append(f"  - [{sample['match_kind']}] {sample['source']} | {sample['title']}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path), "summary": payload["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
