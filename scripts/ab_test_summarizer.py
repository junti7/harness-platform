import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama
from core.database import execute_query

PROMPT = "다음 영문 기술 기사 제목과 요약을 한국어로 2문장 이내로 요약하세요.\n다른 말 없이 요약문만 출력하세요."

MODELS = ["gemma2:27b"]


def summarize(model: str, title: str, summary: str) -> tuple[str, float]:
    content = f"Title: {title[:150]}\n\n{summary[:300]}"
    start = time.time()
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": content},
        ],
        options={"temperature": 0.3, "num_predict": 200},
    )
    return resp["message"]["content"].strip(), round(time.time() - start, 1)


def main():
    rows = execute_query("""
        SELECT fs.title, fs.score, rs.raw_data->>'summary' AS raw_summary
        FROM filtered_signals fs
        JOIN raw_signals rs ON rs.content_hash = fs.content_hash
        WHERE fs.category = 'keyword_pass'
        ORDER BY fs.score DESC, fs.created_at DESC
        LIMIT 5
    """, fetch=True)

    if not rows:
        print("샘플 데이터 없음")
        return

    for i, row in enumerate(rows, 1):
        title = row["title"]
        raw = (row["raw_summary"] or "")[:300]
        score = row["score"]

        print(f"\n{'='*65}")
        print(f"[{i}] score={score:.2f} | {title[:65]}")
        print(f"{'='*65}")

        for model in MODELS:
            result, sec = summarize(model, title, raw)
            print(f"\n  ▶ {model} ({sec}s)")
            for line in result.split("\n"):
                print(f"    {line}")

    print(f"\n{'='*65}")


if __name__ == "__main__":
    main()
