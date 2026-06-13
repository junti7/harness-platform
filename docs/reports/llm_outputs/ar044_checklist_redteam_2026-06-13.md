# AR-044 운영 체크리스트 — Red Team cross-LLM 검증 기록

> date: 2026-06-13  
> 대상: `docs/governance/AR044_OPERATIONAL_CHECKLIST.md`  
> 저자: Claude (self-review 아님 — 아래 검토자는 모두 비저자 독립 LLM)  
> 래퍼: `scripts/redteam_review.sh <model> <ctx>` (read-only: gemini `--approval-mode plan` / codex `-s read-only`)  
> 결과: **red_team_clear** (r3에서 Gemini + Codex 동시 clear)

이 문서는 AGENTS.md cross-LLM 성립 요건(모델명 + prompt/context path + verdict)을 충족하기 위한 영속 기록이다. 원시 검토는 세션 작업 디렉터리에서 수행됐고, 각 라운드의 context 스냅샷과 verdict를 아래에 보존한다.

---

## 라운드별 verdict

| 라운드 | context 스냅샷 | Gemini | Codex |
|---|---|---|---|
| r1 | `/tmp/ar044_checklist_review.md` (157줄) | **block** | **block** |
| r2 | `/tmp/ar044_checklist_review_r2.md` (203줄) | **clear** | **block** (BLOCKER 0, MAJOR 2) |
| r3 | `/tmp/ar044_checklist_review_r3.md` (216줄) | **clear** (B0/M0/MINOR0) | **clear** (B0/M0/MINOR1 비차단) |

> 검토자 LLM 생성 셸은 read-only sandbox로 강제됨. 저자(Claude)는 검토에 참여하지 않음.

---

## r1 — 공통 BLOCKER (PIPA 비협상)

두 모델이 수렴 지적: **만 14세 미만 아동 법정대리인 동의 / 민감정보 별도 동의 / 동의 철회·처리정지권 / 국외 이전 고지(외부 LLM API)** 누락. 이 상태로는 C-1~C-9를 형식 충족해도 법무상 미완료를 `completed`로 오인(false-completed).

- Codex 추가: `qa_clear` 누락(고객-facing 공개물), git/배포 청결을 법무 게이트에 혼입(오염), 증빙 주관성(C-4/C-5 존재성만), 민감도 분류 부재, resume link 보안 약함, operator 최소권한 부재, 외부 변호사 자문이 block 조건인지 불명확, 정합성(segment/shadow)을 close 차단으로 미승격.
- Gemini 추가: 마케팅 별도 동의, 익명화 재식별 방지 기준.

**반영(r1→r2)**: C-1에 PIPA 비협상 ⓐ~ⓕ 신설 / C-3S 민감도 분류표 신설 / C-4·C-5 적법성 기준화 / C-6·C-7·C-8 강화 / close에 qa_clear 추가·배포위생 분리 / §5 정합성 close 차단 승격 / C-9 외부변호사 자문 block 조건화.

---

## r2 — Codex 잔여 MAJOR 2 (Gemini clear)

- Gemini: r1 BLOCKER 전부 반영 확인 → **clear**.
- Codex: BLOCKER 0, MINOR("r1 핵심 대부분 반영됨" 인정). 잔여 MAJOR 2:
  1. 동시성/복구 race(same-case 동시접근·stale resume link·철회 직후 세션 잔존)를 close 게이트로 미승격 (설계는 이미 `version_no`/`edu_device_sessions`/`lock_case_session()` 전제).
  2. payer vs actual participant가 "분리 식별 가능 여부" 관찰 항목일 뿐 — ownership/authority semantics를 close-blocking으로 승격 필요.

**반영(r2→r3)**: C-10(다중기기 세션/복구 동시성 안전성) 신설 + S-3(payer/participant ownership) close-blocking 신설 + C-6 강화.

---

## r3 — 최종 clear

- **Gemini r3**: BLOCKER 0 / MAJOR 0 / MINOR 0 → **VERDICT: clear**
- **Codex r3**: BLOCKER 0 / MAJOR 0 / MINOR 1 → **VERDICT: clear**
  - Codex 확인: r2 잔여 2건 모두 해소(C-10 신설로 race가 C-1ⓒ·C-5·C-7과 정합, §3 close에 C-1~C-10 ✅ 못박음; S-3 close-blocking 승격 + C-6 ownership 직접 연결).
  - Codex MINOR(비차단): §6에 cross-LLM artifact path 기록을 본문 체크로 승격 권고 → **본 문서 생성으로 해소**, 체크리스트 §6에 참조 추가.

---

## 결론

서로 다른 비저자 LLM 2개(Gemini, Codex)가 동일 최종본(r3)에서 clear → **red_team_clear (2026-06-13)**.

단, 본 문서는 AR-044를 *닫는* 체크리스트의 품질 검증일 뿐, AR-044 자체의 close가 아니다. AR-044 close는 체크리스트 C-1~C-10 전 항목의 실제 증빙 + legal_review_approve(갱신) + qa_clear + 대표 confirm이 필요하다(체크리스트 §3).
