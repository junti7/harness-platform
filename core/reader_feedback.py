"""
T-05: 독자 피드백 분류 및 DB 저장 헬퍼

customer_profiles, customer_memory_events, customer_questions 테이블.
이메일은 SHA-256 해시로만 저장 (PIPA 준수).
"""
import hashlib
import json
import re
from typing import Optional

from core.database import execute_query

# ── 패턴 분류 ────────────────────────────────────────────────────────────────

_UNSUBSCRIBE = re.compile(
    r"(구독\s*해지|구독\s*취소|탈퇴|그만\s*받|unsubscribe|cancel\s*sub|stop\s*send)",
    re.IGNORECASE,
)
_COMPLAINT = re.compile(
    r"(별로|실망|어렵|이해\s*안|모르겠|오류|틀렸|잘못|bad|terrible|confusing|difficult|wrong|error|unclear)",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"[?？]|^(뭐|어떻게|언제|왜|누가|어디|무엇|어떤|얼마나|how|what|when|why|who|which|where)\b",
    re.IGNORECASE | re.MULTILINE,
)
_PRAISE = re.compile(
    r"(좋아|훌륭|최고|감사|유익|재밌|흥미|도움|great|thanks|thank|excellent|love|useful|helpful|awesome|amazing)",
    re.IGNORECASE,
)


def classify_feedback(text: str) -> dict:
    """텍스트에서 intent와 sentiment를 추론."""
    if _UNSUBSCRIBE.search(text):
        return {"intent": "unsubscribe_signal", "sentiment": "negative"}
    if _COMPLAINT.search(text):
        return {"intent": "complaint", "sentiment": "negative"}
    if _QUESTION.search(text):
        return {"intent": "question", "sentiment": "neutral"}
    if _PRAISE.search(text):
        return {"intent": "praise", "sentiment": "positive"}
    return {"intent": "other", "sentiment": "neutral"}


def hash_email(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


# ── DB ────────────────────────────────────────────────────────────────────────

def upsert_reader_profile(
    external_ref: str,
    email_hash: Optional[str] = None,
) -> int:
    """reader의 customer_profile을 get-or-create. customer_id 반환."""
    row = execute_query(
        "SELECT id FROM customer_profiles WHERE external_ref = %s",
        (external_ref,), fetch=True,
    )
    if row:
        return row[0]["id"]
    result = execute_query(
        """INSERT INTO customer_profiles
               (external_ref, email_hash, tier, consent_marketing,
                consent_personalization, preferred_language)
           VALUES (%s, %s, 'free', FALSE, FALSE, 'ko')
           RETURNING id""",
        (external_ref, email_hash), fetch=True,
    )
    return result[0]["id"]


def record_feedback(
    customer_id: int,
    text: str,
    classification: dict,
    source_channel: str,
) -> None:
    """customer_memory_event 삽입. intent=question이면 customer_questions도 삽입."""
    execute_query(
        """INSERT INTO customer_memory_events
               (customer_id, event_type, event_key, event_value,
                source_channel, sensitivity_level)
           VALUES (%s, 'reader_feedback', %s, %s::jsonb, %s, 'low')""",
        (
            customer_id,
            classification["intent"],
            json.dumps({"text": text[:500], **classification}, ensure_ascii=False),
            source_channel,
        ),
    )
    if classification["intent"] == "question":
        execute_query(
            """INSERT INTO customer_questions
                   (customer_id, question, status, sensitivity_level)
               VALUES (%s, %s, 'open', 'low')""",
            (customer_id, text[:1000]),
        )
