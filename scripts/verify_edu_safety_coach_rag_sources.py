#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import html
import json
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "harness-os" / "backend" / "main.py"

QUESTIONS = [
    "AI가 아이 공부를 망친다는 말이 진짜야?",
    "아이들이 이미 AI 챗봇을 많이 쓰고 있다면 부모는 뭘 정해야 해?",
    "AI를 아예 못 쓰게 하는 것보다 어떻게 쓰게 하는 게 좋아?",
    "아이가 AI에 너무 기대게 될까 봐 걱정돼. 어떤 신호를 봐야 해?",
    "수학을 불안해하는 아이가 AI 답에 더 의존할 수 있어?",
    "AI 학습앱이 틀린 답을 줄 수도 있다면 어떻게 확인해야 해?",
    "아이에게 AI 문해력을 가르친다는 게 무슨 뜻이야?",
    "AI 시대에 부모가 아이 교육에서 가장 먼저 잡아줘야 할 기준은 뭐야?",
    "아이 스크린 시간이 늘어나는 게 걱정돼. AI 영상이나 유튜브 학습은 어떻게 봐야 해?",
    "AI 때문에 아이 진로가 불안한데 지금 뭘 준비해야 해?",
]


def _load_backend():
    spec = importlib.util.spec_from_file_location("backend_main_source_verify", BACKEND)
    if spec is None or spec.loader is None:
        raise RuntimeError("backend import spec failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(text or ""))).strip().lower()


def _fetch(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 HarnessSourceVerifier/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(req, timeout=16) as resp:  # noqa: S310 - verifier follows curated source URLs.
        raw = resp.read(2_000_000)
    return raw.decode("utf-8", errors="ignore")


def main() -> int:
    mod = _load_backend()
    page_cache: dict[str, str] = {}
    rows = []
    ok = True
    for question in QUESTIONS:
        _, selected, meta = mod._edu_vp_safety_coach_evidence(question, limit=2)
        question_ok = int(meta.get("selected_count") or 0) >= 1
        selected_rows = []
        for item in selected:
            url = str(item.get("source_url") or "").strip()
            quote = str(item.get("source_quote") or "").strip()
            source_ok = False
            error = ""
            if not url or not quote:
                error = "missing_url_or_quote"
            else:
                try:
                    if url not in page_cache:
                        page_cache[url] = _fetch(url)
                    source_ok = _normalize(quote) in _normalize(page_cache[url])
                    if not source_ok:
                        error = "quote_not_found_in_source"
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {str(exc)[:160]}"
            question_ok = question_ok and source_ok
            selected_rows.append(
                {
                    "id": item.get("id"),
                    "source": item.get("source"),
                    "source_url": url,
                    "source_quote": quote,
                    "source_quote_verified": source_ok,
                    "error": error,
                }
            )
        ok = ok and question_ok
        rows.append(
            {
                "question": question,
                "ok": question_ok,
                "meta": {
                    "candidate_mode": meta.get("candidate_mode"),
                    "candidate_count": meta.get("candidate_count"),
                    "selected_count": meta.get("selected_count"),
                    "skip_reason": meta.get("skip_reason"),
                },
                "selected": selected_rows,
            }
        )
    print(json.dumps({"ok": ok, "rows": rows}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
