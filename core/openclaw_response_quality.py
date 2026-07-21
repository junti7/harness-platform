"""Fail-closed, domain-independent delivery verification for OpenClaw.

Facts originate from evidence adapters. Models may choose non-factual prose, but
they cannot mint factual claims or evidence IDs. Factual delivery is rendered
from adapter-issued ``EvidenceFact.text`` only.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


SCHEMA_VERSION = "1.0"

TaskType = Literal[
    "conversation",
    "transform",
    "creative",
    "explanation",
    "lookup",
    "status",
    "summary",
    "analysis",
    "recommendation",
    "action",
]
DeliveryVerdict = Literal["deliver", "partial", "abstain"]

_CURRENT_RE = re.compile(
    r"오늘|지금|현재|최근|최신|실시간|현황|상태|어때|이번\s*주|"
    r"today|now|current|latest|recent|status|live",
    re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"실행|보내|전송|발행|게시|업로드|삭제|수정|저장|승인|결제|구매|주문|소집|오케스트레이션|"
    r"execute|send|publish|post|upload|delete|write|approve|purchase|order",
    re.IGNORECASE,
)
_RECOMMEND_RE = re.compile(r"추천|권고|전략|어떻게\s*해야|다음\s*(?:행동|조치)|recommend|strategy", re.IGNORECASE)
_ANALYSIS_RE = re.compile(r"분석|판단|검토|원인|왜|리스크|진단|analysis|assess|diagnos|risk", re.IGNORECASE)
_SUMMARY_RE = re.compile(r"요약|브리핑|핵심|정리|summary|summari[sz]e|brief", re.IGNORECASE)
_STATUS_RE = re.compile(r"현황|상태|어때|운영\s*중|status|health", re.IGNORECASE)
_TRANSFORM_RE = re.compile(r"번역|고쳐\s*써|다듬|문체|표로|변환|translate|rewrite|reformat", re.IGNORECASE)
_CREATIVE_RE = re.compile(r"창작|아이디어|브레인스토밍|이름\s*지어|카피\s*초안|poem|story|brainstorm", re.IGNORECASE)
_GREETING_RE = re.compile(r"^(?:안녕|hello|hi|반가워|고마워|감사)(?:[\s!?.]*)$", re.IGNORECASE)
_TIMELESS_EXPLANATION_RE = re.compile(r"설명|원리|개념|의미|작동\s*방식|explain|principle|concept|how\s+does", re.IGNORECASE)
_FACTUAL_QUESTION_RE = re.compile(
    r"누구|언제|어디|얼마|몇\s|무엇|뭐야|알려|확인|사실|"
    r"who|when|where|what|which|how\s+many|tell\s+me|is\s+it",
    re.IGNORECASE,
)
_QUESTION_STOP_WORDS = {
    "현재", "오늘", "지금", "최근", "최신", "실시간", "상태", "현황", "정리", "요약", "분석",
    "판단", "검토", "브리핑", "추천", "권고", "전략", "알려", "알려줘", "보여", "보여줘", "확인", "확인해", "해줘",
    "해주세요", "어때", "어떻게", "무엇", "뭐", "왜", "the", "a", "an", "please", "show", "tell",
    "온", "받은", "내용", "결과", "현재", "이번", "top", "즉시", "조치안", "준비됐어",
    "개와", "요약해줘", "요약해주세요", "정리해줘", "정리해주세요", "확인해줘", "확인해주세요",
    "current", "latest", "status", "summary", "analyze", "analysis", "review", "report",
    "실제", "데이터", "기준", "근거", "근거도", "시각과", "표시", "표시해", "확인한",
    "기반", "바탕", "정확히", "구체적", "객관적", "팩트", "팩트로", "출처", "출처도",
    "actual", "data", "evidence", "basis", "timestamp", "time", "source", "sources", "verified",
}
_BROAD_CLAIM_RE = re.compile(
    r"모든|전체|전부|완벽|완료|정상\s*운영|문제\s*없|준비\s*완료|"
    r"all|every|fully|complete|no\s+issue|ready",
    re.IGNORECASE,
)
_GENERIC_SUBJECT_IDS = {
    "시스템", "서비스", "플랫폼", "상태", "현황", "내용", "결과", "메일", "이메일", "문서", "파일",
    "system", "service", "platform", "status", "content", "result", "email", "document", "file",
}
_SECRET_RE = re.compile(
    r"\b(?:xox[abprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|"
    r"CANARY_SECRET_[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)
_PROMPT_INJECTION_RE = re.compile(
    r"ignore\s+(?:all\s+)?previous|system\s+prompt|developer\s+message|"
    r"지시를\s*무시|이전\s*명령|도구를\s*실행|권한을\s*(?:변경|상승)",
    re.IGNORECASE,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _tokens(text: str) -> tuple[str, ...]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]{1,}|[가-힣]{2,}", (text or "").lower())
    cleaned: list[str] = []
    for token in raw:
        token = re.sub(r"(?:에서|으로|에게|부터|까지|의|을|를|이|가|은|는|에|로)$", "", token)
        if re.fullmatch(r"(?:요약|정리|확인|검토|판단|브리핑|알려|보여|보고)(?:해|해줘|해주세요|줘|주세요)?", token):
            continue
        if len(token) < 2 or token in _QUESTION_STOP_WORDS:
            continue
        if token not in cleaned:
            cleaned.append(token)
    return tuple(cleaned[:12])


def extract_subject_ids(text: str) -> tuple[str, ...]:
    return _tokens(text)


def _stable_id(prefix: str, *values: str) -> str:
    digest = hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class AnswerContract:
    schema_version: str
    task_type: TaskType
    subject_ids: tuple[str, ...]
    requested_dimensions: tuple[str, ...]
    time_kind: Literal["current", "historical", "timeless"]
    minimum_authority: Literal["none", "secondary", "primary", "authoritative_runtime"]
    freshness_seconds: int | None
    required_coverage: Literal["complete", "representative", "best_effort"]
    action_boundary: Literal["read_only", "draft_only", "approval_required", "authorized"]
    response_shape: str
    ambiguities: tuple[str, ...] = ()

    @property
    def requires_evidence(self) -> bool:
        return self.minimum_authority != "none"


@dataclass(frozen=True)
class EvidenceFact:
    fact_id: str
    subject_ids: tuple[str, ...]
    dimension: str
    text: str
    scope: Literal["bounded", "all"] = "bounded"


@dataclass(frozen=True)
class EvidenceItem:
    schema_version: str
    evidence_id: str
    subject_ids: tuple[str, ...]
    dimensions: tuple[str, ...]
    source_type: str
    authority: Literal["unverified", "secondary", "primary", "authoritative_runtime"]
    observed_at: datetime
    coverage: Literal["complete", "representative", "partial", "unknown"]
    privacy_class: Literal["public", "internal", "private", "secret"]
    payload_ref: str
    fetch_status: Literal["ok", "partial", "failed"]
    facts: tuple[EvidenceFact, ...]


@dataclass(frozen=True)
class Claim:
    claim_id: str
    claim_type: Literal["observed", "derived", "opinion", "proposal"]
    fact_ids: tuple[str, ...]
    derivation_id: str | None = None


@dataclass(frozen=True)
class ClaimLedger:
    claims: tuple[Claim, ...] = ()


@dataclass(frozen=True)
class DeliveryDecision:
    schema_version: str
    verdict: DeliveryVerdict
    rendered_text: str
    eligible_claim_ids: tuple[str, ...] = ()
    missing_dimensions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


class VerifiedText(str):
    """String-compatible response carrying its immutable delivery decision."""

    decision: DeliveryDecision

    def __new__(cls, decision: DeliveryDecision) -> "VerifiedText":
        obj = str.__new__(cls, decision.rendered_text)
        obj.decision = decision
        return obj


def infer_answer_contract(message: str, *, authorized: bool = False) -> AnswerContract:
    text = " ".join((message or "").split())
    current = bool(_CURRENT_RE.search(text))
    subjects = _tokens(text)

    if _GREETING_RE.fullmatch(text):
        task: TaskType = "conversation"
    elif _ACTION_RE.search(text):
        task = "action"
    elif _RECOMMEND_RE.search(text):
        task = "recommendation"
    elif _STATUS_RE.search(text):
        task = "status"
    elif _ANALYSIS_RE.search(text):
        task = "analysis"
    elif _SUMMARY_RE.search(text):
        task = "summary"
    elif _TRANSFORM_RE.search(text):
        task = "transform"
    elif _CREATIVE_RE.search(text):
        task = "creative"
    elif current:
        task = "lookup"
    elif _TIMELESS_EXPLANATION_RE.search(text):
        task = "explanation"
    elif _FACTUAL_QUESTION_RE.search(text) or text.endswith(("?", "까", "나요", "인가요")):
        task = "lookup"
    else:
        task = "explanation"

    dimensions: list[str] = []
    if task in {"lookup", "status"}:
        dimensions.append("state")
    if task == "summary":
        dimensions.append("content")
    if task == "analysis":
        dimensions.extend(("evidence", "analysis"))
    if task == "recommendation":
        dimensions.extend(("evidence", "risk", "next_action"))
    if task == "action":
        dimensions.extend(("authorization", "execution_result"))

    evidence_required = task in {"lookup", "status", "summary", "analysis", "recommendation", "action"}
    authority: Literal["none", "secondary", "primary", "authoritative_runtime"] = "none"
    if task == "status" or task == "action":
        authority = "authoritative_runtime"
    elif evidence_required:
        authority = "primary"

    coverage: Literal["complete", "representative", "best_effort"] = "best_effort"
    if task in {"status", "summary", "action"}:
        coverage = "complete"
    elif task in {"analysis", "recommendation"}:
        coverage = "representative"

    boundary: Literal["read_only", "draft_only", "approval_required", "authorized"] = "read_only"
    if task == "action":
        boundary = "authorized" if authorized else "approval_required"

    ambiguities: tuple[str, ...] = ()
    if evidence_required and not subjects:
        ambiguities = ("subject_missing",)

    return AnswerContract(
        schema_version=SCHEMA_VERSION,
        task_type=task,
        subject_ids=subjects,
        requested_dimensions=tuple(dict.fromkeys(dimensions)),
        time_kind="current" if current or task in {"status", "action"} else "timeless",
        minimum_authority=authority,
        freshness_seconds=300 if task in {"status", "action"} else (86400 if current else None),
        required_coverage=coverage,
        action_boundary=boundary,
        response_shape="brief" if task in {"status", "summary", "analysis", "recommendation"} else "direct",
        ambiguities=ambiguities,
    )


_AUTHORITY_RANK = {"unverified": 0, "secondary": 1, "primary": 2, "authoritative_runtime": 3, "none": 0}


def _subject_match(contract: AnswerContract, evidence: EvidenceItem) -> bool:
    if not contract.subject_ids:
        return False
    requested = set(contract.subject_ids)
    available = set(evidence.subject_ids)
    specific = requested - _GENERIC_SUBJECT_IDS
    if specific:
        overlap = len(specific & available)
        required = max(1, (len(specific) + 1) // 2)
        return overlap >= required
    # Require a meaningful token overlap; one generic token cannot validate a
    # multi-token subject such as a named subsystem within a larger platform.
    overlap = len(requested & available)
    required = 1 if len(requested) <= 2 else max(2, (len(requested) + 1) // 2)
    return overlap >= required


def _fresh_enough(contract: AnswerContract, evidence: EvidenceItem, now: datetime) -> bool:
    if contract.freshness_seconds is None:
        return True
    observed = evidence.observed_at
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return 0 <= (now - observed.astimezone(timezone.utc)).total_seconds() <= contract.freshness_seconds


def verify_delivery(
    contract: AnswerContract,
    evidence_items: tuple[EvidenceItem, ...] = (),
    ledger: ClaimLedger | None = None,
    *,
    non_factual_text: str = "",
    now: datetime | None = None,
) -> DeliveryDecision:
    now = now or _now_utc()
    if not contract.requires_evidence:
        if _SECRET_RE.search(non_factual_text):
            return DeliveryDecision(SCHEMA_VERSION, "abstain", "민감정보가 감지되어 응답을 전달하지 않습니다.", reasons=("secret_detected",))
        return DeliveryDecision(SCHEMA_VERSION, "deliver", non_factual_text.strip() or "요청을 처리했습니다.")

    if contract.ambiguities:
        return DeliveryDecision(
            SCHEMA_VERSION,
            "abstain",
            "확인할 대상을 특정할 수 없습니다. 대상 이름이나 범위를 한 줄로 지정해 주세요.",
            reasons=contract.ambiguities,
        )
    if contract.task_type == "action" and contract.action_boundary != "authorized":
        return DeliveryDecision(
            SCHEMA_VERSION,
            "abstain",
            "상태 변경 요청은 명시적 승인과 실행 전 검증이 필요합니다.",
            reasons=("authorization_required",),
        )

    eligible: list[EvidenceItem] = []
    reasons: list[str] = []
    for item in evidence_items:
        if item.schema_version != SCHEMA_VERSION or item.fetch_status == "failed":
            continue
        if item.privacy_class == "secret":
            reasons.append("secret_evidence_blocked")
            continue
        if not _subject_match(contract, item):
            reasons.append("evidence_subject_mismatch")
            continue
        if _AUTHORITY_RANK[item.authority] < _AUTHORITY_RANK[contract.minimum_authority]:
            reasons.append("evidence_authority_insufficient")
            continue
        if not _fresh_enough(contract, item, now):
            reasons.append("evidence_stale")
            continue
        eligible.append(item)

    if not eligible:
        return DeliveryDecision(
            SCHEMA_VERSION,
            "abstain",
            "요청한 대상과 일치하는 최신 근거를 확인하지 못했습니다. 확인되지 않은 내용을 추측해 답하지 않습니다.",
            reasons=tuple(dict.fromkeys(reasons or ["eligible_evidence_missing"])),
        )

    covered = {dimension for item in eligible for dimension in item.dimensions}
    missing = tuple(dimension for dimension in contract.requested_dimensions if dimension not in covered)
    fact_by_id = {fact.fact_id: (item, fact) for item in eligible for fact in item.facts}
    claims = (ledger or ClaimLedger()).claims
    if not claims:
        claims = tuple(
            Claim(_stable_id("claim", fact.fact_id), "observed", (fact.fact_id,))
            for item in eligible
            for fact in item.facts
            if (
                fact.dimension in contract.requested_dimensions
                or any(dimension in item.dimensions for dimension in contract.requested_dimensions)
                or not contract.requested_dimensions
            )
        )

    rendered: list[str] = []
    accepted_claims: list[str] = []
    for claim in claims:
        if claim.claim_type == "derived" and not claim.derivation_id:
            reasons.append("unregistered_derivation")
            continue
        if not claim.fact_ids or any(fact_id not in fact_by_id for fact_id in claim.fact_ids):
            reasons.append("unknown_fact_id")
            continue
        claim_rendered = False
        for fact_id in claim.fact_ids:
            item, fact = fact_by_id[fact_id]
            if fact.scope == "all" and item.coverage != "complete":
                reasons.append("unsupported_broad_claim")
                continue
            if _SECRET_RE.search(fact.text):
                reasons.append("secret_detected")
                continue
            if fact.text not in rendered:
                rendered.append(fact.text)
            claim_rendered = True
        if claim_rendered:
            accepted_claims.append(claim.claim_id)

    if not rendered:
        return DeliveryDecision(
            SCHEMA_VERSION,
            "abstain",
            "검증 가능한 사실 문장을 만들 수 없습니다. 근거 수집 범위를 확인해 주세요.",
            missing_dimensions=missing,
            reasons=tuple(dict.fromkeys(reasons or ["verified_claim_missing"])),
        )

    coverage_incomplete = any(item.coverage in {"partial", "unknown"} or item.fetch_status == "partial" for item in eligible)
    verdict: DeliveryVerdict = "partial" if missing or coverage_incomplete or reasons else "deliver"
    prefix = "확인된 범위만 답합니다.\n" if verdict == "partial" else ""
    suffix = ""
    if missing:
        suffix = f"\n미확인 범위: {', '.join(missing)}"
    return DeliveryDecision(
        SCHEMA_VERSION,
        verdict,
        prefix + "\n".join(rendered) + suffix,
        eligible_claim_ids=tuple(accepted_claims),
        missing_dimensions=missing,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def evidence_from_text(
    *,
    source_id: str,
    subject_ids: tuple[str, ...],
    dimensions: tuple[str, ...],
    text: str,
    authority: Literal["secondary", "primary", "authoritative_runtime"],
    coverage: Literal["complete", "representative", "partial", "unknown"] = "complete",
    privacy_class: Literal["public", "internal", "private"] = "internal",
    observed_at: datetime | None = None,
    fetch_status: Literal["ok", "partial"] = "ok",
) -> EvidenceItem:
    """Create adapter-issued facts from already bounded deterministic text."""
    observed_at = observed_at or _now_utc()
    clean_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not _PROMPT_INJECTION_RE.search(line) and not _SECRET_RE.search(line)
    ]
    facts = tuple(
        EvidenceFact(
            fact_id=_stable_id("fact", source_id, str(index), line),
            subject_ids=subject_ids,
            dimension=dimensions[0] if dimensions else "state",
            text=line,
            scope="all" if _BROAD_CLAIM_RE.search(line) else "bounded",
        )
        for index, line in enumerate(clean_lines)
    )
    return EvidenceItem(
        schema_version=SCHEMA_VERSION,
        evidence_id=_stable_id("evidence", source_id, observed_at.isoformat()),
        subject_ids=subject_ids,
        dimensions=dimensions,
        source_type=source_id,
        authority=authority,
        observed_at=observed_at,
        coverage=coverage,
        privacy_class=privacy_class,
        payload_ref=_stable_id("payload", source_id),
        fetch_status=fetch_status,
        facts=facts,
    )
