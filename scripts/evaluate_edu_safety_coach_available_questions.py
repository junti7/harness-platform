#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "harness-os" / "backend" / "main.py"
SIM_DIR = ROOT / "docs" / "reviews" / "edu_coach_simulations"

DEFAULT_PATTERNS = (
    "corpus_utterances_*.jsonl",
    "gold_set_seed_2026-06-27.jsonl",
    "judge_calibration_20260627T085846Z.jsonl",
    "run_20260627T104048Z_adversarial_current_fallback.jsonl",
)

GENERIC_TEMPLATE_MARKER = "AI 교육이나 학습을 시작할 때는 도구 이름보다"


def _load_backend() -> Any:
    module_name = "backend_main_available_question_eval"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, BACKEND)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import backend: {BACKEND}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                rows.append({"_parse_error": True, "_path": str(path), "_line": line_number})
                continue
            if isinstance(value, dict):
                value["_path"] = str(path.relative_to(ROOT))
                value["_line"] = line_number
                rows.append(value)
    return rows


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", str(question or "").strip()).lower()


def _question_like(question: str) -> bool:
    q = str(question or "").strip()
    if len(q) < 5:
        return False
    if not re.search(r"[가-힣]", q):
        return False
    question_markers = (
        "?",
        "어떻게",
        "무엇",
        "뭐",
        "왜",
        "어디",
        "언제",
        "괜찮",
        "좋을",
        "해야",
        "할까",
        "할까요",
        "해요",
        "인가요",
        "일까요",
        "진짜",
        "걱정",
        "불안",
    )
    return any(marker in q for marker in question_markers)


def _specific_parent_ai_intent(question: str) -> bool:
    q = str(question or "").lower()
    if not any(marker in q for marker in ("ai", "챗봇", "gpt", "생성형", "인공지능", "유튜브", "스크린", "영상", "학습앱")):
        return False
    intent_markers = (
        "숙제",
        "과제",
        "대신",
        "공부",
        "학습",
        "교육",
        "기준",
        "원칙",
        "부모",
        "학부모",
        "아이",
        "의존",
        "불안",
        "틀린",
        "확인",
        "문해력",
        "리터러시",
        "진로",
        "직업",
        "스크린",
        "영상",
        "유튜브",
    )
    return any(marker in q for marker in intent_markers)


def _source_quote_present(source_html: str, quote: str) -> bool:
    normalized_source = html.unescape(re.sub(r"\s+", " ", source_html or "")).lower()
    normalized_quote = html.unescape(re.sub(r"\s+", " ", quote or "").strip()).lower()
    return bool(normalized_quote and normalized_quote in normalized_source)


def _fetch_url(url: str, *, timeout: float) -> tuple[bool, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "HarnessSafetyCoachSourceVerifier/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - verifier uses stored public source URLs.
            raw = response.read(1_500_000)
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
    return True, raw.decode("utf-8", errors="ignore")


def _load_questions(patterns: tuple[str, ...]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(SIM_DIR.glob(pattern)))
    unique_paths = sorted(set(paths))
    rows_seen = 0
    parse_errors = 0
    by_question: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    per_file: dict[str, int] = {}
    for path in unique_paths:
        rows = _iter_jsonl(path)
        per_file[str(path.relative_to(ROOT))] = len(rows)
        for row in rows:
            rows_seen += 1
            if row.get("_parse_error"):
                parse_errors += 1
                continue
            question = str(row.get("question") or "").strip()
            if not question:
                continue
            key = _normalize_question(question)
            if key in by_question:
                duplicate_count += 1
                by_question[key].setdefault("seen_in", []).append(row.get("_path"))
                continue
            row["seen_in"] = [row.get("_path")]
            by_question[key] = row
    return list(by_question.values()), {
        "patterns": patterns,
        "files": [str(path.relative_to(ROOT)) for path in unique_paths],
        "per_file_rows": per_file,
        "rows_seen": rows_seen,
        "parse_errors": parse_errors,
        "duplicates_removed": duplicate_count,
        "unique_questions": len(by_question),
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _sample_append(samples: dict[str, list[dict[str, Any]]], key: str, row: dict[str, Any], *, limit: int) -> None:
    if len(samples[key]) >= limit:
        return
    samples[key].append(row)


def evaluate(*, patterns: tuple[str, ...], sample_limit: int, verify_sources: bool, source_timeout: float) -> dict[str, Any]:
    mod = _load_backend()
    rows, inventory = _load_questions(patterns)
    started = time.monotonic()
    counters: Counter[str] = Counter()
    issue_counts: Counter[str] = Counter()
    source_cache: dict[str, tuple[bool, str]] = {}
    source_quote_failures: list[dict[str, Any]] = []
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_segment: Counter[str] = Counter()
    by_channel: Counter[str] = Counter()
    by_input_category: Counter[str] = Counter()
    eligible_issue_counts: Counter[str] = Counter()

    for index, row in enumerate(rows, start=1):
        question = str(row.get("question") or "").strip()
        concept_title = str(row.get("concept_title") or "수집 corpus 기반 사용자 질문")
        concept_body = str(row.get("concept_body") or row.get("evidence_excerpt") or "")
        segment = str(row.get("segment") or "unknown")
        channel = str(row.get("source_channel") or "unknown")
        question_like = _question_like(question)
        specific_intent = _specific_parent_ai_intent(question)
        input_category = mod._edu_vp_safety_coach_input_category(question, source_channel=channel, segment=segment)
        category = str(input_category.get("category") or "unknown")
        eligible_for_answer_quality = bool(input_category.get("eligible_for_answer_quality"))
        anchor_ids = list(mod._edu_vp_safety_coach_anchor_match_ids(question))
        rag_expected = bool(anchor_ids)
        fallback = mod._edu_vp_safety_coach_fallback(concept_title, question)
        evidence_text, evidence_items, evidence_meta = mod._edu_vp_safety_coach_evidence(question, limit=2) if rag_expected else ("", [], {"selected_count": 0})
        answer, rag_infused = mod._edu_vp_safety_coach_blend_rag_sentence(fallback, question, evidence_items)
        answer = mod._edu_vp_safety_coach_prepare_answer(answer)
        if eligible_for_answer_quality:
            review = mod._edu_vp_safety_coach_quality_review(
                question=question,
                answer=answer,
                concept_body=concept_body,
                evidence_items=evidence_items,
                llm_judge_enabled=False,
            )
            issues = list(review.get("issues") or [])
        else:
            review = {"issues": [], "skipped_reason": "not_real_user_question"}
            issues = []
        verdict = "needs_work" if issues else "clear"

        counters["evaluated"] += 1
        counters[f"input_category:{category}"] += 1
        by_input_category[category] += 1
        if eligible_for_answer_quality:
            counters["answer_quality_eligible"] += 1
            counters[f"answer_quality_eligible_verdict:{verdict}"] += 1
        else:
            counters["answer_quality_skipped_non_user_question"] += 1
        counters[f"verdict:{verdict}"] += 1
        if question_like:
            counters["question_like"] += 1
            counters[f"question_like_verdict:{verdict}"] += 1
        if specific_intent:
            counters["specific_parent_ai_intent"] += 1
            counters[f"specific_parent_ai_intent_verdict:{verdict}"] += 1
        by_segment[segment] += 1
        by_channel[channel] += 1
        for issue in issues:
            issue_counts[issue] += 1
            if eligible_for_answer_quality:
                eligible_issue_counts[issue] += 1
        if not eligible_for_answer_quality:
            _sample_append(
                samples,
                f"input_category_{category}",
                {
                    "question": question[:500],
                    "reasons": input_category.get("reasons") or [],
                    "source_path": row.get("_path"),
                    "segment": segment,
                    "source_channel": channel,
                },
                limit=sample_limit,
            )

        if rag_expected:
            counters["rag_expected"] += 1
            if evidence_items and rag_infused and "출처:" in answer and "http" in answer:
                counters["rag_pass"] += 1
            else:
                counters["rag_fail"] += 1
                _sample_append(
                    samples,
                    "rag_fail",
                    {
                        "question": question,
                        "anchor_ids": anchor_ids,
                        "selected_count": evidence_meta.get("selected_count"),
                        "skip_reason": evidence_meta.get("skip_reason"),
                        "answer_preview": answer[:360],
                        "source_path": row.get("_path"),
                    },
                    limit=sample_limit,
                )
            for item in evidence_items:
                quote = str(item.get("source_quote") or "").strip()
                url = str(item.get("source_url") or "").strip()
                if not quote or not url:
                    counters["source_quote_missing"] += 1
                    _sample_append(
                        samples,
                        "source_quote_missing",
                        {"question": question, "item": {"id": item.get("id"), "source": item.get("source"), "source_url": url, "source_quote": quote}},
                        limit=sample_limit,
                    )
                    continue
                if verify_sources:
                    if url not in source_cache:
                        source_cache[url] = _fetch_url(url, timeout=source_timeout)
                    fetched, body_or_error = source_cache[url]
                    if not fetched or not _source_quote_present(body_or_error, quote):
                        counters["source_quote_verify_fail"] += 1
                        failure = {
                            "question": question,
                            "item_id": item.get("id"),
                            "source": item.get("source"),
                            "source_url": url,
                            "source_quote": quote,
                            "error": "" if fetched else body_or_error[:220],
                        }
                        source_quote_failures.append(failure)
                        _sample_append(samples, "source_quote_verify_fail", failure, limit=sample_limit)
                    else:
                        counters["source_quote_verified"] += 1

        if "**" in answer:
            counters["markdown_bold_marker_leak"] += 1
            _sample_append(samples, "markdown_bold_marker_leak", {"question": question, "answer_preview": answer[:360]}, limit=sample_limit)
        if GENERIC_TEMPLATE_MARKER in answer:
            counters["generic_template"] += 1
            if question_like:
                counters["question_like_generic_template"] += 1
            if specific_intent:
                counters["specific_parent_ai_intent_generic_template"] += 1
                _sample_append(samples, "specific_generic_template", {"question": question, "answer_preview": answer[:360], "source_path": row.get("_path")}, limit=sample_limit)
        if issues:
            _sample_append(
                samples,
                "needs_work",
                {
                    "question": question,
                    "issues": issues,
                    "answer_preview": answer[:360],
                    "source_path": row.get("_path"),
                    "segment": segment,
                    "source_channel": channel,
                    "input_category": category,
                },
                limit=sample_limit,
            )

        if index % 10000 == 0:
            print(json.dumps({"progress": index, "total": len(rows), "elapsed_s": round(time.monotonic() - started, 1)}, ensure_ascii=False), file=sys.stderr)

    elapsed = time.monotonic() - started
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend_answer_version": getattr(mod, "_EDU_VP_SAFETY_COACH_ANSWER_VERSION", None),
        "inventory": inventory,
        "elapsed_seconds": round(elapsed, 3),
        "verify_sources": verify_sources,
        "counts": dict(counters),
        "issue_counts": dict(issue_counts.most_common()),
        "answer_quality_eligible_issue_counts": dict(eligible_issue_counts.most_common()),
        "segment_counts": dict(by_segment.most_common()),
        "input_category_counts": dict(by_input_category.most_common()),
        "source_channel_counts_top30": dict(by_channel.most_common(30)),
        "source_urls_checked": len(source_cache),
        "source_quote_failures": source_quote_failures[:sample_limit],
        "samples": dict(samples),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate all available edu safety coach simulation questions.")
    parser.add_argument("--pattern", action="append", dest="patterns", help="jsonl glob under docs/reviews/edu_coach_simulations")
    parser.add_argument("--sample-limit", type=int, default=50)
    parser.add_argument("--no-source-verify", action="store_true")
    parser.add_argument("--source-timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    patterns = tuple(args.patterns or DEFAULT_PATTERNS)
    report = evaluate(
        patterns=patterns,
        sample_limit=max(1, args.sample_limit),
        verify_sources=not args.no_source_verify,
        source_timeout=max(1.0, args.source_timeout),
    )
    output = args.output or SIM_DIR / f"full_available_safety_coach_eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {
        "output": _display_path(output),
        "backend_answer_version": report.get("backend_answer_version"),
        "unique_questions": report["inventory"]["unique_questions"],
        "counts": report["counts"],
        "top_issues": dict(list(report["issue_counts"].items())[:10]),
        "source_urls_checked": report.get("source_urls_checked"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    counts = report["counts"]
    hard_failures = int(counts.get("rag_fail", 0)) + int(counts.get("source_quote_missing", 0)) + int(counts.get("source_quote_verify_fail", 0)) + int(counts.get("markdown_bold_marker_leak", 0))
    return 1 if hard_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
