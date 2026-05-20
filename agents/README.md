# agents/ — Persona Layout

# 상위 규약: docs/governance/AGENTIC_ORCHESTRATION_CHARTER.md

이 디렉토리는 agentic orchestration의 persona 정의를 담는다. 각 persona는 기존 `AGENTS.md` 에이전트를 인격화한 것이며, persona handle은 cosmetic layer다 — 권한·금지·decision boundary는 `AGENTS.md`를 상속한다.

## 표준 레이아웃

각 persona는 다음 3개 파일을 가진다.

```
agents/<handle>/
  SYSTEM_PROMPT.md   # persona identity + 책임 + 거버넌스 경계
  MEMORY.md          # episodic memory (일기, append-only) — Charter §8 형식
  CHANNEL.md         # home 채널 + 회의실 참여 규칙
```

## Persona → LLM 매핑

primary LLM은 기본 호출 대상, escalation은 고난도/장문/cross-check 시 호출. **게이트(red_team_clear/legal_review_approve/qa_clear)는 persona 단일 LLM으로 충족 불가** — Charter §3, 반드시 cross-LLM 절차.

| Persona | 기존 에이전트 | Primary LLM | Escalation | Phase |
|---|---|---|---|---|
| **Jarvis** | Chief of Staff (§3.-1) | Codex | Claude (장문 synthesis) | 0 |
| **Friday** | BizOps (§3.14B) + Product (§3.12) | Claude | Codex (데이터 계산) | 1 |
| **C3PO** | Marketing (§3.13) + Growth (§3.10A) | Claude | — | 1 |
| **KITT** | Legal Counsel (§3.11) | Claude | Gemini (게이트 cross-LLM 의무) | 1 |
| **TARS** | Codex engineering | Codex | Copilot CLI (command hints) | 1 |
| **Watchman** | Red Team (§3.8) + BRM (§3.16) | Claude | Gemini+Codex (게이트 cross-LLM 의무) | 1 |
| **Scribe** | QA (§3.14A) | Codex (format/link) | Claude+Gemini (fact, 다국어) | 1 |
| **Coach** | HR Training (§3.7) | Claude | — | 2 |
| Eve / Data / Tron / Joi | (미매핑) | — | — | **동결** |

신규 persona 신설은 첫 paid subscriber 확보 시까지 동결 (Charter §2.3).

## 비용 인지

모든 persona 호출은 per-order 비용 cap($2.00/order) 하에서 동작한다 (Charter §5). primary(저비용 Codex/local) → escalation(고비용 Claude/Gemini) 순서를 지킨다.
