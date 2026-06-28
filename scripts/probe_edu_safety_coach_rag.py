#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


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
    spec = importlib.util.spec_from_file_location("backend_main_probe", BACKEND)
    if spec is None or spec.loader is None:
        raise RuntimeError("backend import spec failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    mod = _load_backend()
    rows = []
    for question in QUESTIONS:
        text, items, meta = mod._edu_vp_safety_coach_evidence(question, limit=2)
        rows.append(
            {
                "question": question,
                "text": text,
                "meta": {
                    key: meta.get(key)
                    for key in (
                        "keywords",
                        "candidate_count",
                        "selected_count",
                        "rejected_count",
                        "skip_reason",
                        "rejected",
                    )
                },
                "selected": [
                    {
                        "id": item.get("id"),
                        "source": item.get("source"),
                        "source_url": item.get("source_url"),
                        "source_quote": item.get("source_quote"),
                        "cite": item.get("cite"),
                    }
                    for item in items
                ],
            }
        )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
