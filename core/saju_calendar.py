"""Deterministic Four Pillars facts for NotebookLM interpretation."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from core.notebook_query_planning import SupplementalFacts

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
KOREAN_STEMS = "갑을병정무기경신임계"
KOREAN_BRANCHES = "자축인묘진사오미신유술해"

_DATE_RE = re.compile(r"(?P<year>19\d{2}|20\d{2})년\s*(?P<month>\d{1,2})월\s*(?P<day>\d{1,2})일")
_HOUR_BRANCHES = {
    "자시": 0, "축시": 2, "인시": 4, "묘시": 6, "진시": 8, "사시": 10,
    "오시": 12, "미시": 14, "신시": 16, "유시": 18, "술시": 20, "해시": 22,
}
_RELATIVE_DATES = {"오늘": 0, "내일": 1, "어제": -1}


def normalize_relative_saju_dates(
    question: str, *, today: date | None = None
) -> str:
    """Resolve Korean relative target dates deterministically in Korea time."""
    if not any(
        word in question
        for word in ("사주", "일진", "운세", "명리", "전체운", "재물운", "건강운", "대인운")
    ):
        return question
    base = today or datetime.now(ZoneInfo("Asia/Seoul")).date()
    pattern = re.compile(r"(?<![가-힣])(?P<marker>오늘|내일|어제)(?!날|모레)")
    matches = [match.group("marker") for match in pattern.finditer(question)]
    if not matches:
        return question
    if len(set(matches)) != 1:
        raise ValueError("계산형 사주 질문은 오늘/내일/어제 중 대상일 하나만 지원합니다")
    marker = matches[0]
    target = base + timedelta(days=_RELATIVE_DATES[marker])
    resolved = f"{target.year}년 {target.month}월 {target.day}일"
    replacement = f"{resolved}(Asia/Seoul 기준 {marker})"
    return pattern.sub(replacement, question)


def _gz_text(gz: object) -> str:
    stem = int(getattr(gz, "tg"))
    branch = int(getattr(gz, "dz"))
    return f"{KOREAN_STEMS[stem]}{KOREAN_BRANCHES[branch]}({STEMS[stem]}{BRANCHES[branch]})"


def _pillars(year: int, month: int, day: int, hour: int | None = None) -> str:
    try:
        import sxtwl
    except ImportError as exc:  # pragma: no cover - deployment guard
        raise RuntimeError("sxtwl calendar engine is unavailable") from exc
    value = sxtwl.fromSolar(year, month, day)
    if value.hasJieQi():
        raise ValueError(
            f"{year:04d}-{month:02d}-{day:02d}은 절기 경계일이므로 정확한 시각과 "
            "시간대 기반 계산이 필요합니다"
        )
    fields = [
        _gz_text(value.getYearGZ()),
        _gz_text(value.getMonthGZ()),
        _gz_text(value.getDayGZ()),
    ]
    if hour is not None:
        fields.append(_gz_text(value.getHourGZ(hour)))
    return " ".join(fields)


def enrich_saju_question(question: str) -> SupplementalFacts | None:
    """Return derived facts only when a question contains birth and target dates."""
    compact_question = re.sub(r"\s+", "", question).lower()
    lunar_marked = any(
        marker in compact_question
        for marker in ("음력", "구력", "陰曆", "陰历", "阴曆", "阴历", "農曆", "农历", "lunar")
    )
    lunar_marked = lunar_marked or "윤달" in compact_question or bool(
        re.search(r"윤\d{1,2}월", compact_question)
    )
    if lunar_marked:
        raise ValueError("음력 입력은 현재 지원하지 않으며 검증된 양력 날짜가 필요합니다")
    dates = list(_DATE_RE.finditer(question))
    is_saju_request = any(
        word in question
        for word in ("사주", "일진", "운세", "명리", "전체운", "재물운", "건강운", "대인운")
    )
    if not is_saju_request:
        return None
    if len(dates) < 2:
        raise ValueError("계산형 사주 질문에는 출생일과 대상일 두 날짜가 필요합니다")
    if len(dates) != 2:
        raise ValueError("사주 계산에는 출생일과 대상일 두 날짜를 명확히 지정해야 합니다")
    parsed = sorted(
        [
            (
            tuple(int(match.group(key)) for key in ("year", "month", "day")),
            match,
            )
            for match in dates
        ],
        key=lambda item: item[0],
    )
    if parsed[0][0] == parsed[1][0]:
        raise ValueError("출생일과 대상일 역할이 모호합니다")
    (birth_parts, birth), (target_parts, target) = parsed
    # Only a compact token attached to the birth date (유시생, 18시생) may define
    # the natal hour. Later appointments, target times, and other people's times
    # must never become a fabricated 시주.
    birth_context = question[birth.end() : birth.end() + 20]
    if "자시" in birth_context and not re.search(
        r"(?<!\d)(?:00|0)\s*시", birth_context
    ):
        raise ValueError("자시는 00시 출생만 지원하며 23시는 야자시 경계로 지원하지 않습니다")
    twelve_hour_marker = re.search(
        r"(?:오전|오후|밤|a\.?m\.?|p\.?m\.?)",
        birth_context,
        flags=re.IGNORECASE,
    )
    if twelve_hour_marker and re.search(r"\d{1,2}\s*시", birth_context):
        raise ValueError("오전/오후 시간은 24시간제 출생 시각으로 명시해야 합니다")
    if re.search(r"23\s*시", birth_context):
        raise ValueError("23시는 야자시 일주 경계 규칙이 필요하므로 현재 지원하지 않습니다")
    branch_matches = [
        (name, value)
        for name, value in _HOUR_BRANCHES.items()
        if re.search(rf"{name}\s*생", birth_context)
    ]
    if len(branch_matches) > 1:
        raise ValueError("출생 시지 표현이 둘 이상이라 모호합니다")
    hour = branch_matches[0][1] if branch_matches else None
    any_numeric_birth_hour = re.search(r"\d{1,2}\s*시\s*(?:생|출생)", birth_context)
    explicit_hour = re.search(
        r"(?<!\d)(?P<hour>[01]?\d|2[0-3])\s*시\s*(?:생|출생)", birth_context
    )
    if any_numeric_birth_hour and not explicit_hour:
        raise ValueError("출생 시각은 00시부터 23시 사이 24시간제로 입력해야 합니다")
    if explicit_hour:
        if hour is not None:
            raise ValueError("출생 시지와 숫자 시각이 중복되어 모호합니다")
        hour = int(explicit_hour.group("hour"))
    # Validate Gregorian dates before calling the native calendar library.
    datetime(*birth_parts, hour or 12)
    datetime(*target_parts)
    gender = "남성" if any(x in question for x in ("남자", "남성")) else (
        "여성" if any(x in question for x in ("여자", "여성")) else "미지정"
    )
    warnings = ("한국 표준시 기준이며 출생지 경도 보정은 적용하지 않음",)
    if hour is None:
        warnings += ("출생 시각이 없어 시주는 계산하지 않음",)
    return SupplementalFacts(
        provider="sxtwl-2.0.7 deterministic calendar",
        facts=(
            f"출생 양력 {birth_parts[0]:04d}-{birth_parts[1]:02d}-{birth_parts[2]:02d}, "
            f"{gender}, 사주 원국: {_pillars(*birth_parts, hour)}",
            f"대상일 양력 {target_parts[0]:04d}-{target_parts[1]:02d}-{target_parts[2]:02d}, "
            f"연주·월주·일주: {_pillars(*target_parts)}",
        ),
        warnings=warnings,
    )
