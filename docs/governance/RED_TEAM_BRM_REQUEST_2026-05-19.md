# RED-TEAM Final Pass — BRM Playbook 검토 요청
**Date:** 2026-05-19  
**Issued by:** Claude (Sonnet 4.6)  
**Protocol status:** Claude 1차 pass 완료 → Gemini + Codex final pass 필요  
**Scope:** `docs/governance/BRM_PLAYBOOK.md`, `docs/governance/RISK_REGISTER.md`

---

## 배경

Harness 플랫폼에 Business Risk Management(BRM) 팀이 신설되었다 (commit `e138235`).  
BRM Playbook(`docs/governance/BRM_PLAYBOOK.md`)이 작성되어 운영 표준으로 사용될 예정이다.

AGENTS.md §3.8 규약: MD 문서 개정은 **Claude + Gemini** cross-LLM verification 최소 요건.  
완전한 3-LLM pass (Claude + Gemini + Codex)를 목표로 한다.

Claude 1차 pass 결과: `red_team_block` (B-1~B-5 수정 필요 판정).

---

## Claude 1차 pass 발견사항 요약

| ID | 등급 | 항목 |
|----|------|------|
| B-1 | MEDIUM | §2.2 발생 확률 기준값 미정의 |
| B-2 | MEDIUM | §5.3 `accepted` 전환 시 CEO audit trail 없음 |
| B-3 | MEDIUM | §6.2 `pre_mortem_approve` 기록 주체 미명시 |
| B-4 | MEDIUM | `risk_register` DB가 roadmap임에도 현재 운영 가능한 것처럼 기술 |
| B-5 | MEDIUM | 실시간 임계값 모니터링 자동화/수동 여부 미명시 |
| B-6 | LOW | ESC-STR-1 fallback 없음 |
| B-7 | LOW | Kill Criteria 트리거 항목 정합성 미검증 |

---

## Gemini에게 요청하는 검토 사항

### 1. B-1~B-5 재검증

Claude가 발견한 5개 MEDIUM 항목에 대해 독립적으로 동의/불동의 여부를 판정하라.  
특히 다음을 확인하라:

- **B-2 (accepted audit trail)**: `accepted` 상태 전환이 CEO 승인 없이 가능한지, `ceo_decisions` 테이블에 기록해야 하는지 governance 관점에서 검토
- **B-3 (pre_mortem_approve issuer)**: `PRE_MORTEM_PROTOCOL.md` §4의 절차와 BRM Playbook §6.2가 충돌하는지, 누가 bridge 명령을 실행해야 하는지
- **B-4 (DB roadmap gap)**: `AGENTS.md §5` roadmap 테이블 목록과 BRM Playbook의 기술이 실제로 오해를 일으키는지

### 2. 신규 취약점 독립 스캔

Claude가 놓쳤을 가능성이 있는 항목을 독립적으로 스캔하라:

- **내부 일관성**: §4 임계값과 §2.2 매트릭스 사이의 충돌 (예: P=low + I=critical이 "완화 조치" → ESC-FIN-2는 자동 escalation인데 매트릭스상 "완화 조치" 수준에 해당)
- **CLAUDE.md §4 approval semantics와의 충돌**: BRM이 새로운 approval_type을 암묵적으로 요구하거나 기존 approval semantics를 침범하는지
- **순환 의존**: BRM이 Red Team 출력을 받아 리스크를 등록하는데, Red Team이 BRM Playbook을 검토하는 역방향 의존이 운영상 순환을 만드는지
- **범위 과대 설정**: Phase 1 단계(무료 구독자 50명 목표)에서 BRM이 관리하기로 한 9개 escalation 임계값이 현재 사업 단계에 비해 과도하게 복잡하지 않은지

### 3. Kill Criteria 정합성 검증

`docs/governance/KILL_CRITERIA.md` (존재하는 경우)의 내용과 BRM Playbook §7.1의 5개 트리거 항목이 일치하는지 확인하라.

---

## Codex에게 요청하는 검토 사항

### 1. B-1~B-5 재검증

Claude + Gemini 발견사항에 대한 독립적 판정.

### 2. 구현 가능성 검토 (Engineering 관점)

- **실시간 모니터링 (B-5)**: Phase 1에서 임계값 자동 감지를 구현하려면 어떤 변경이 필요한가? 현재 codebase(`scripts/`, `adapters/`)에서 LLM API 비용, subscriber 수를 실시간으로 읽는 경로가 존재하는가?
- **`accepted` DB 기록 (B-2)**: `ceo_decisions` 테이블의 현재 스키마로 `accepted` 상태 승인을 기록할 수 있는가? 별도 `approval_type`이 필요한가?
- **`risk_register` DB 구현 필요성**: 현재 MD 파일 기반으로 Phase 1을 운영하다가 DB로 마이그레이션 할 때 schema가 어떻게 되어야 하는가? `AGENTS.md §5`의 roadmap 필드 정의와 BRM Playbook §5.2 필드가 일치하는지 확인.

### 3. AGENTS.md, CLAUDE.md와의 문서 일관성

- BRM Agent(AGENTS.md §3.16)의 역할 정의가 BRM Playbook(§8.3 팀별 경계)과 충돌하는지 확인
- CLAUDE.md의 기존 approval semantics(§4)에 BRM이 새로운 approval_type을 추가해야 하는지 검토

### 4. 최종 판정

`red_team_clear` 또는 `red_team_block` (이유 포함).

---

## 참조 파일

- `docs/governance/BRM_PLAYBOOK.md` (검토 대상)
- `docs/governance/RISK_REGISTER.md` (레지스터 초기 데이터)
- `docs/governance/RED_TEAM_LOG.md` (Claude 1차 결과)
- `docs/governance/PRE_MORTEM_PROTOCOL.md` (B-3 관련)
- `AGENTS.md` §3.16, §5 (B-4 관련)
- `CLAUDE.md` §4 (approval semantics 충돌 검토)
- `docs/governance/KILL_CRITERIA.md` (B-7 관련)

---

## 최종 판정 기준

| 조건 | 결과 |
| --- | --- |
| Claude + Gemini + Codex 3개 모두 clear 또는 수정 후 clear | `red_team_clear` |
| Claude + Gemini clear (Codex block) | `red_team_clear` (2-of-3) |
| Claude + Codex clear (Gemini block) | `red_team_clear` (2-of-3) |
| 2개 이상 block | `red_team_block` — 추가 수정 후 재검토 |
| non-negotiable finding 1개라도 존재 | 2-of-3 무관하게 수정 후 재검토 |

판정 결과는 `docs/governance/RED_TEAM_LOG.md` 2026-05-19 BRM Playbook 섹션에 기록.

---

*Gemini + Codex final pass 후 판정을 `docs/governance/RED_TEAM_LOG.md`에 날짜, 모델명, 미해결 항목과 함께 기록해 주세요.*
