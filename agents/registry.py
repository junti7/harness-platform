"""Persona registry — the runtime source of truth for the Harness org chart.

Each persona maps an AGENTS.md team to: a primary LLM provider, a Slack channel,
a system prompt, a memory file, and an `active` flag. The orchestrator and the
single-persona runner read from here.

Scalability contract (Charter §2.3): adding a team later is NOT a code change to
the runner or orchestrator — it is a registry entry + `active=True` + three persona
files (SYSTEM_PROMPT/MEMORY/CHANNEL) + one logged Slack channel. Conference-room
convening iterates `get_active_personas()`, so flipping a flag auto-enrolls a team.

`active=False` entries are part of the org chart but not yet wired (no channel /
files required until activated). `frozen` entries are the unmapped video personas
held until the first paid subscriber (Charter §2.3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parent

# Proper-cased display names for handles that aren't simple capitalizations.
_DISPLAY_NAMES = {"kitt": "KITT", "c3po": "C3PO", "tars": "TARS"}


@dataclass(frozen=True)
class Persona:
    handle: str            # registry key / codename (e.g. "friday")
    team_ko: str           # Korean org-chart team name
    role: str              # short role description
    agents_md_ref: str     # section in AGENTS.md this inherits from
    provider: str          # primary LLM CLI: claude | gemini | codex | copilot
    escalation: str | None # secondary LLM for hard/long/cross-check work
    channel_env: str | None  # env var holding the Slack channel ID (None until activated)
    active: bool
    phase: str             # phase at which this persona is/was activated
    frozen: bool = False   # True = held until first paid subscriber (no new personas)

    @property
    def name(self) -> str:
        """Proper-cased codename (KITT, C3PO, TARS, Friday, ...)."""
        return _DISPLAY_NAMES.get(self.handle, self.handle.capitalize())

    @property
    def team_short(self) -> str:
        """Korean team name without the English parenthetical."""
        return self.team_ko.split(" (")[0].strip()

    @property
    def display(self) -> str:
        """e.g. 'Friday(사업운영팀)' — name + team for Slack/UI."""
        return f"{self.name}({self.team_short})"

    @property
    def dir(self) -> Path:
        return AGENTS_DIR / self.handle

    @property
    def system_prompt_path(self) -> Path:
        return self.dir / "SYSTEM_PROMPT.md"

    @property
    def memory_path(self) -> Path:
        return self.dir / "MEMORY.md"


# ── Harness org chart ──────────────────────────────────────────────────────────
# Active now: Jarvis (Phase 0), Friday + KITT (Phase 1).
# Defined-but-inactive: the rest of the AGENTS.md org — flip `active` to enroll.
# Frozen: Eve / Data / Tron / Joi — no mapping, held until first paid subscriber.

_PERSONAS: list[Persona] = [
    Persona(
        handle="jarvis",
        team_ko="비서실장 (Chief of Staff)",
        role="orchestrator, 최종 게이트웨이, OpenClaw 릴레이 수신",
        agents_md_ref="§3.-1",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS",
        active=True,
        phase="0",
    ),
    Persona(
        handle="friday",
        team_ko="사업운영팀 (Business Operations)",
        role="PM / 사업운영 — KPI 진단, 목표 forecast, anomaly",
        agents_md_ref="§3.14B",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_TEAM_FRIDAY",
        active=True,
        phase="1",
    ),
    Persona(
        handle="vision",
        team_ko="상품기획팀 (Product Planning)",
        role="제품 정의·패키징·가격 ladder·기능 우선순위",
        agents_md_ref="§3.12",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_TEAM_VISION",
        active=True,
        phase="1",
    ),
    Persona(
        handle="kitt",
        team_ko="법무팀 (Legal)",
        role="법적 리스크 검토, disclaimer, 약관",
        agents_md_ref="§3.11",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_TEAM_KITT",
        active=True,
        phase="1",
    ),
    # ── defined, not yet activated (flip active + add files + logged channel) ──
    Persona(
        handle="c3po",
        team_ko="마케팅팀 (Marketing + Subscriber Growth)",
        role="acquisition 전략, 카피, 채널 mix",
        agents_md_ref="§3.13 + §3.10A",
        provider="gemini",
        escalation=None,
        channel_env="SLACK_CHANNEL_TEAM_C3PO",
        active=True,
        phase="2",
    ),
    Persona(
        handle="coach",
        team_ko="인사팀 (HR Training)",
        role="부대표 OJT, 평가, 교육 보고",
        agents_md_ref="§3.7",
        provider="gemini",
        escalation=None,
        channel_env="SLACK_CHANNEL_TEAM_COACH",
        active=True,
        phase="2",
    ),
    Persona(
        handle="watchman",
        team_ko="리스크팀 (Red Team + BRM)",
        role="cross-LLM red team 코디네이션, 전사 리스크 레지스터",
        agents_md_ref="§3.8 + §3.16",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_TEAM_WATCHMAN",
        active=True,
        phase="2",
    ),
    Persona(
        handle="scribe",
        team_ko="QA팀",
        role="fact/format/link/schema 발행 직전 검증",
        agents_md_ref="§3.14A",
        provider="gemini",
        escalation="claude",
        channel_env="SLACK_CHANNEL_TEAM_SCRIBE",
        active=True,
        phase="2",
    ),
    Persona(
        handle="tars",
        team_ko="엔지니어링팀",
        role="codebase, schema, automation, tests",
        agents_md_ref="Codex engineering",
        provider="gemini",
        escalation="copilot",
        channel_env="SLACK_CHANNEL_TEAM_TARS",
        active=True,
        phase="2",
    ),
    # ── frozen: 신규 persona 신설 동결 (Charter §2.3) ──
    Persona(
        handle="eve",
        team_ko="(미매핑) 리서치",
        role="대규모 리서치 — 동결",
        agents_md_ref="(none)",
        provider="gemini",
        escalation=None,
        channel_env=None,
        active=False,
        phase="4",
        frozen=True,
    ),
    Persona(
        handle="data",
        team_ko="(미매핑) 데이터 사이언스",
        role="행동 데이터/시뮬레이션 — 동결",
        agents_md_ref="(none)",
        provider="gemini",
        escalation=None,
        channel_env=None,
        active=False,
        phase="4",
        frozen=True,
    ),
    Persona(
        handle="tron",
        team_ko="(미매핑) 보안",
        role="보안 — 동결",
        agents_md_ref="(none)",
        provider="gemini",
        escalation=None,
        channel_env=None,
        active=False,
        phase="4",
        frozen=True,
    ),
    Persona(
        handle="joi",
        team_ko="(미매핑) 디자인",
        role="UX/UI — 동결",
        agents_md_ref="(none)",
        provider="gemini",
        escalation=None,
        channel_env=None,
        active=False,
        phase="4",
        frozen=True,
    ),
]

REGISTRY: dict[str, Persona] = {p.handle: p for p in _PERSONAS}


def get_persona(handle: str) -> Persona:
    key = handle.strip().lower()
    if key not in REGISTRY:
        raise KeyError(f"Unknown persona handle: {handle!r}. Known: {sorted(REGISTRY)}")
    return REGISTRY[key]


def get_active_personas() -> list[Persona]:
    """Personas currently wired for orchestration. Conference-room participants."""
    return [p for p in _PERSONAS if p.active]


def get_org_chart() -> list[Persona]:
    """Full org chart (active + inactive), excluding frozen unmapped personas."""
    return [p for p in _PERSONAS if not p.frozen]


def find_mentioned_personas(text: str) -> list[Persona]:
    """Active personas a message addresses, by codename or Korean team name.

    Matches 'Friday', 'friday', '@friday', 'Friday님', or the team name
    ('사업운영팀'). Jarvis is included so the orchestrator can be addressed.
    """
    low = text.lower()
    found: list[Persona] = []
    for p in get_active_personas():
        handle = re.escape(p.handle.lower())
        name = re.escape(p.name.lower())
        # 영문 이름은 앞뒤가 영문자가 아니어야 매칭 (뒤에 한글 '님'이 붙어도 인식).
        if (
            re.search(rf"(?<![a-z]){handle}(?![a-z])", low)
            or re.search(rf"(?<![a-z]){name}(?![a-z])", low)
            or p.team_short in text
        ):
            found.append(p)
    return found


if __name__ == "__main__":
    print("Harness persona registry")
    print(f"  active   : {[p.handle for p in get_active_personas()]}")
    print(f"  inactive : {[p.handle for p in _PERSONAS if not p.active and not p.frozen]}")
    print(f"  frozen   : {[p.handle for p in _PERSONAS if p.frozen]}")
