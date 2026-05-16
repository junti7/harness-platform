import hashlib
import re

from core.database import execute_query
from core.logger import HarnessLogger


SIGNAL_TYPE_KEYWORDS = {
    "paper": ["arxiv", "benchmark", "dataset", "paper", "model", "learning"],
    "product": ["launch", "release", "product", "platform", "robot", "humanoid"],
    "funding": ["funding", "raises", "series", "investment", "valuation"],
    "hiring": ["hiring", "jobs", "recruiting", "talent"],
    "patent": ["patent", "filing"],
    "open_source": ["github", "open source", "repository", "repo"],
    "regulatory": ["regulation", "policy", "export control", "sec", "filing"],
}

MONETIZATION_KEYWORDS = [
    "humanoid", "robot", "robotics", "physical ai", "agi", "semiconductor",
    "gpu", "inference", "factory", "automation", "defense", "space",
    "manufacturing", "chip", "nvidia", "tesla", "figure ai",
]

NOVELTY_KEYWORDS = [
    "first", "new", "novel", "breakthrough", "state-of-the-art", "sota",
    "launch", "unveil", "release", "raises", "funding",
]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def stable_hash(*parts: str) -> str:
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:64]


def keyword_score(text: str, keywords: list[str], weight: float) -> float:
    normalized = normalize_text(text)
    hits = sum(1 for keyword in keywords if keyword in normalized)
    return min(1.0, hits * weight)


def infer_signal_type(source: str, title: str, category: str) -> str:
    text = normalize_text(f"{source} {title} {category}")
    for signal_type, keywords in SIGNAL_TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return signal_type
    return "news"


def compute_scores(row: dict) -> dict:
    title = row.get("title") or ""
    summary = row.get("summary") or ""
    text = f"{title} {summary}"

    source_confidence = float(row.get("source_reliability") or 0.5)
    relevance_score = max(0.0, min(1.0, float(row.get("score") or 0.0)))
    novelty_score = max(0.15, keyword_score(text, NOVELTY_KEYWORDS, 0.25))
    monetization_potential = max(0.1, keyword_score(text, MONETIZATION_KEYWORDS, 0.12))

    preliminary_score = (
        relevance_score * 0.40 +
        source_confidence * 0.25 +
        novelty_score * 0.20 +
        monetization_potential * 0.15
    )

    return {
        "source_confidence": round(source_confidence, 3),
        "relevance_score": round(relevance_score, 3),
        "novelty_score": round(novelty_score, 3),
        "monetization_potential": round(monetization_potential, 3),
        "preliminary_score": round(preliminary_score, 3),
    }


def get_unpromoted_filtered_signals() -> list[dict]:
    return execute_query("""
        SELECT
            fs.id,
            fs.raw_signal_id,
            fs.source,
            fs.title,
            fs.summary,
            fs.score,
            fs.category,
            fs.content_hash,
            rs.raw_data->>'url' AS source_url,
            COALESCE(
                NULLIF(rs.raw_data->>'source_reliability', '')::float,
                sc.reliability_score,
                0.5
            ) AS source_reliability,
            COALESCE(
                rs.raw_data->>'expected_signal_type',
                sc.expected_signal_type,
                'news'
            ) AS expected_signal_type
        FROM filtered_signals fs
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        LEFT JOIN source_catalog sc ON sc.source_name = fs.source
        LEFT JOIN signals s ON s.filtered_signal_id = fs.id
        WHERE s.id IS NULL
        ORDER BY fs.score DESC, fs.created_at DESC
    """, fetch=True)


def save_signal_candidate(row: dict, scores: dict, signal_type: str):
    title = row.get("title") or ""
    summary = row.get("summary") or ""
    source_url = row.get("source_url") or ""
    content_hash = row.get("content_hash") or stable_hash(title, source_url)
    signal_summary = summary or title

    execute_query("""
        INSERT INTO signals (
            raw_signal_id,
            filtered_signal_id,
            source,
            signal_type,
            signal_summary,
            why_now,
            source_url,
            content_hash,
            novelty_score,
            relevance_score,
            source_confidence,
            monetization_potential,
            preliminary_score,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'candidate')
        ON CONFLICT (content_hash) DO NOTHING
    """, (
        row["raw_signal_id"],
        row["id"],
        row["source"],
        signal_type,
        signal_summary,
        f"source={row['source']}; tier2_score={row.get('score')}",
        source_url,
        content_hash,
        scores["novelty_score"],
        scores["relevance_score"],
        scores["source_confidence"],
        scores["monetization_potential"],
        scores["preliminary_score"],
    ))


def promote_signals(correlation_id: str = None) -> int:
    logger = HarnessLogger(tier=2, correlation_id=correlation_id)
    logger.info("=== Tier 2 Signal 승격 시작 ===")

    rows = get_unpromoted_filtered_signals()
    if not rows:
        logger.info("승격할 filtered signal 없음")
        return 0

    promoted = 0
    for row in rows:
        row = dict(row)
        signal_type = infer_signal_type(
            row.get("source") or "",
            row.get("title") or "",
            row.get("expected_signal_type") or row.get("category") or "",
        )
        scores = compute_scores(row)
        save_signal_candidate(row, scores, signal_type)
        promoted += 1

        if promoted % 20 == 0:
            logger.info(f"Signal 승격 진행 중: {promoted}/{len(rows)}")

    logger.info(f"=== Tier 2 Signal 승격 완료: {promoted}개 ===")
    return promoted


if __name__ == "__main__":
    promote_signals()
