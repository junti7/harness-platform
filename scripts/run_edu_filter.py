"""
교육 컨설팅 DEEP RESEARCH — Tier 2 필터
Ollama 로컬 모델로 arXiv/Semantic Scholar 논문의 관련성을 판별한다.

사용법:
  .venv/bin/python scripts/run_edu_filter.py
  .venv/bin/python scripts/run_edu_filter.py --model gemma2:27b   # 고품질 (느림)
  .venv/bin/python scripts/run_edu_filter.py --limit 30

AR-026 | correlation_id: edu-consulting-20260524
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import httpx
from core.database import execute_query
from core.logger import HarnessLogger

DOMAIN = "edu_consulting"
CORRELATION_ID = "edu-consulting-20260524"
OLLAMA_HOST = "http://localhost:11434"

RELEVANCE_PROMPT = """You are a research analyst for an AI education consulting firm targeting Korean parents and workers.

Evaluate if this paper/article is relevant to our business. We care about:
- AI dependency / cognitive offloading in students or workers
- Parental anxiety or public sentiment about children's and teens' AI use
- Critical thinking skills, metacognition, and creativity vs AI use
- AI literacy, AI skills training, prompt engineering education (K-12, university, adults, corporate workplace)
- Psychological effects of AI on learning, productivity, or career development
- Workplace AI adoption, job market changes, career transition anxiety, or job displacement fears (including how workers, faculty, and students view AI replacement/augmentation)
- Practical EdTech, Web 2.0 tools in education, and Generative AI applications for teaching and learning

NOT relevant (strictly exclude):
- Pure ML/AI technical papers (deep learning architecture math, model training benchmarks, hardware accelerators)
- AI applied to non-human/non-cognitive domains (autonomous vehicle hardware, industrial manufacturing robotics, material science simulations)
- Medical/clinical AI papers completely unrelated to psychology, cognitive distress, or education

Paper title: {title}
Abstract: {abstract}

Respond in JSON only. Write "reason" and "key_insight" in Korean (한국어):
{{"relevant": true/false, "score": 1-10, "reason": "한 문장으로 판단 근거", "key_insight": "관련이 있을 경우 마케팅용 핵심 인사이트 한 문장"}}"""


def fetch_pending(limit: int, logger: HarnessLogger):
    rows = execute_query(
        """SELECT id, raw_data FROM raw_signals
           WHERE status = 'pending' AND domain = %s
           ORDER BY ingested_at DESC LIMIT %s""",
        (DOMAIN, limit),
        fetch=True,
    )
    return rows or []


def call_ollama(model: str, prompt: str) -> dict:
    resp = httpx.post(
        f"{OLLAMA_HOST}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "{}")
    return json.loads(raw)


def run_filter(model: str, limit: int, logger: HarnessLogger):
    rows = fetch_pending(limit, logger)
    logger.info(f"필터 대상: {len(rows)}개 | model={model}")

    passed = failed = error = 0

    for row in rows:
        sig_id = row["id"]
        raw = row["raw_data"]
        title = raw.get("title", "")[:300]
        abstract = raw.get("abstract", raw.get("summary", ""))[:1000]

        prompt = RELEVANCE_PROMPT.format(title=title, abstract=abstract)

        try:
            result = call_ollama(model, prompt)
            is_relevant = result.get("relevant", False)
            score = int(result.get("score", 0))
            reason = result.get("reason", "")
            insight = result.get("key_insight", "")

            # 관련성이 true이거나, 점수가 4점 이상인 경우 유연하게 통과시킴
            is_passed = is_relevant or (score >= 4)
            status = "filtered_pass" if is_passed else "filtered_fail"
            
            execute_query(
                """UPDATE raw_signals
                   SET status = %s,
                       raw_data = raw_data || %s::jsonb
                   WHERE id = %s""",
                (status, json.dumps({
                    "tier2_score": score,
                    "tier2_reason": reason,
                    "tier2_insight": insight,
                }), sig_id),
            )

            mark = "✅" if is_passed else "❌"
            logger.info(f"  {mark} [{score}/10] {title[:60]} — {reason[:80]}")
            if is_passed:
                passed += 1
            else:
                failed += 1

        except Exception as exc:
            logger.warning(f"  ⚠️  ID={sig_id} 오류: {exc}")
            error += 1

    logger.info(f"=== Tier 2 필터 완료 | 통과={passed} 탈락={failed} 오류={error} ===")
    return passed, failed, error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:1.5b",
                        help="Ollama 모델 (기본: qwen2.5:1.5b / 고품질: gemma2:27b)")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    logger = HarnessLogger(tier=2, correlation_id=CORRELATION_ID)
    logger.info(f"=== 교육 Tier 2 필터 시작 | model={args.model} | limit={args.limit} ===")

    run_filter(args.model, args.limit, logger)


if __name__ == "__main__":
    main()
