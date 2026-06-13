# AR-044 운영 체크리스트 (edu 공개 전 개인정보/법무 게이트)

> 작성일: 2026-06-13 · 개정: 2026-06-13 (red-team r1~r3 반영)  
> 상태: **red_team_clear 통과(r3, Gemini+Codex) — Legal Counsel 점검·qa_clear·대표 confirm 후 ACTIVE 승격**  
> 상위 게이트: `AR-044` (owner: Legal Counsel, category: HUMAN_REQUIRED, 현재 status: hold)  
> 근거 문서: [edu_ar044_legal_gate_handoff_2026-06-13.md](../handoffs/edu_ar044_legal_gate_handoff_2026-06-13.md), [legal_review_edu_conversation_log_2026-06-11.md](../reports/legal/legal_review_edu_conversation_log_2026-06-11.md)

---

## 0. 이 문서의 목적

`AR-044 completed`의 기준을 **감(感)이 아니라 증빙(artifact) 기준**으로 고정한다.

- 코드가 있다고 닫지 않는다.
- 화면 문구만 넣었다고 닫지 않는다.
- 아래 모든 항목이 **증빙 artifact + 객관적 확인 방법**으로 검증될 때만 닫는다.
- 단순 "문서가 존재함"은 충족이 아니다. 각 항목은 **적법성·운영가능성**까지 증빙해야 한다.

핵심 trigger 원칙(legal review 2026-06-11 재확인): **현재 실 외부 익명 트래픽 = 0**(테스트 계정 + 대표/부대표 IP 2개)이라 runway가 있다. 본 게이트의 모든 항목은 **실 외부 익명 고객 트래픽이 edu 경로로 유입되기 전**에 충족돼야 한다. 미충족 상태로 실 트래픽을 수집하면 기존 `legal_review_approve`(조건부)가 **무효**가 된다.

> ⚠️ false-completed 경고: 본 게이트는 "AR-044를 닫아도 안전하다"는 착각을 막기 위해 존재한다. 아래 PIPA 비협상 항목(C-1의 ⓐ~ⓕ) 중 하나라도 미충족이면 C-1~C-9를 형식적으로 ✅ 처리해도 **법무상 미완료**이며, 그 상태의 close는 무효다.

---

## 1. 완료 정의 (handoff §7 — 5개 모두 충족 시에만 close)

| # | 완료 정의 | 대응 체크 항목 |
|---|---|---|
| D1 | 공개 화면에 실제 고지 문구가 연결됨 | C-1, C-2 |
| D2 | 실제 수집 필드와 문구가 일치함 | C-3, C-3S |
| D3 | 보유기간/삭제/열람·정정/철회·처리정지 대응 절차가 존재함 | C-4, C-5 |
| D4 | operator 접근통제와 resume link 정책이 실제 구현 전제와 맞음 | C-6, C-7, C-8, C-10 |
| D5 | 법무 관점에서 "내부 테스트 only" → "실고객 공개 가능"으로 상태 전환 가능 | C-9 |

---

## 2. 체크리스트 항목

> 각 항목: **완료 기준 / owner / 증빙 artifact / 확인 방법 / 상태**  
> 상태 표기: ⬜ 미착수 · 🟡 진행중 · ✅ 증빙완료

### C-1. 개인정보 처리방침 본문 확정 (PIPA 의무 포함)

- **완료 기준**: edu 공개 UX 기준 처리방침에 아래 **기본 7요소 + PIPA 비협상 6항목(ⓐ~ⓕ)**이 모두 포함.
  - 기본 7요소: ① 수집 항목 ② 수집 목적 ③ 보유 기간 ④ 삭제/파기 기준 ⑤ 제3자 제공/위탁 여부 ⑥ 문의처(개인정보 보호책임자) ⑦ 권리행사(열람/정정/삭제/처리정지) 방법
  - **PIPA 비협상 항목 (하나라도 누락 시 BLOCKER):**
    - **ⓐ 만 14세 미만 아동 법정대리인 동의**: `child_grade`·자녀 관련 대화본문 등 아동 개인정보 수집 가능성이 있으므로, 14세 미만 데이터에 대한 법정대리인 동의 수집·검증 절차를 명시. (수집하지 않겠다면 "아동 직접 데이터 미수집" 정책 + 그 강제 방식을 증빙)
    - **ⓑ 민감정보 별도 동의**: `gender_identity` 및 대화본문 내 잠재 민감정보(건강/사상 등)에 대해 일반 동의와 **분리된** 별도 동의. 또는 민감정보 미수집 설계로 회피했음을 증빙.
    - **ⓒ 동의 철회권 + 처리정지권**: 장래 처리에 대한 동의 철회 및 처리정지 요구를 언제든 할 수 있음 + 철회 시 resume link 무효화·후속 서비스개선/모델참조 사용 중단까지 연결.
    - **ⓓ 국외 이전 고지**: 외부 LLM/클라우드 API(Claude/Gemini/GPT 등) 사용 시 국외 이전이 발생하므로 **이전 국가·받는 자·이전 목적·항목·보유기간**을 고지하고 필요 시 별도 동의. 또는 국내 처리/비식별화로 회피했음을 증빙.
    - **ⓔ 마케팅 활용 별도 동의**: `email`/`phone`/`name`을 광고·마케팅에 사용한다면 서비스 제공 동의와 **분리된** 마케팅 수신 동의(옵트인) + 표시광고법 disclaimer.
    - **ⓕ 위탁/제3자 처리 명시**: LLM API·인프라·분석 도구 등 처리위탁 현황을 수탁자·위탁업무 단위로 명시.
- **owner**: Legal Counsel (초안) → 대표 confirm
- **증빙 artifact**: `docs/legal/edu_privacy_policy_v1.md` (신규) + 공개 URL 경로 + ⓐ~ⓕ 각 항목이 본문 어느 조항에 있는지 매핑표
- **확인 방법**: 7요소 + ⓐ~ⓕ 체크리스트 전수 대조 + Legal Counsel 서명 라인 + 버전 태그(`consent_version` 값과 일치)
- **상태**: ⬜

### C-2. 수집 고지 문구를 실제 공개 화면에 연결

- **완료 기준**: PoC 랜딩/intake 동의 흐름에 처리방침 링크 + 핵심 고지 노출. **분리 동의가 필요한 항목(민감정보·국외이전·마케팅·아동)은 별도 동의 UI로 구현**(일괄 동의 금지). `edu_customers.consent_version` 및 동의 audit 필드 기록 경로 확인.
- **owner**: Engineering (구현) / Legal Counsel (문구·동의분리 검수)
- **증빙 artifact**: 공개 화면 스크린샷(모바일 세로 + 데스크톱) + 동의 audit 기록 스키마 + DB 실측 로그
- **확인 방법**: 모바일 첫 진입에서 고지·분리동의 노출 육안 확인(Mobile-First Rule) + DB row에 **동의 시각·동의 주체·동의 UI variant·동의 항목별 값·정책 버전**이 기록되는지 확인(단순 non-null 불가). 철회 시 동의 상태 변경 이력이 남는지 확인.
- **상태**: ⬜

### C-3. 실제 수집 필드 ↔ 고지 문구 ↔ 최소수집 원칙 대조

- **완료 기준**: 아래 현재 설계 수집 필드 전부가 처리방침에 명시되고, **필드별 법적 근거(동의/계약이행/정당이익 등)와 "없으면 서비스 제공 불가인지(필수 정당성)"가 증빙**되며, 과도수집이 없음. (`gender_identity`·`phone`·`name`·`child_grade`·대화본문 전체 저장은 과수집 위험 高 → 필수 정당성 우선 검토.)
  - intake: `age_band`, `gender_identity`, `current_device_type`, `current_os_family`, `current_browser_context`, `selected_llm`, `email`, `phone`, `name`, `segment`
  - case/target: `seeker_role`, `target_person_type`, `child_grade`, `primary_concern`, `ai_usage_context`, `edu_case_targets.*`
  - 대화 본문: `edu_conversation_log` (요청 history + 응답 본문, 학부모/자녀 PII 포함 가능)
- **owner**: Legal Counsel + Engineering
- **증빙 artifact**: 필드 × (목적·법적근거·필수/선택·필수 정당성·보유근거) 대조표 (`docs/legal/edu_field_data_map_v1.md` 신규)
- **확인 방법**: DB 스키마(`EDU_STANDALONE_APP_IMPLEMENTATION.md §4`) ↔ 처리방침 ↔ 실제 저장 row 3중 대조. 문구에 없는데 저장되는 필드 = 0건. 필수 정당성 미증빙 필드는 선택화 또는 제거.
- **상태**: ⬜

### C-3S. 데이터 민감도 분류표 (신규 — Codex/Gemini r1)

- **완료 기준**: 모든 수집 필드를 **일반 개인정보 / 민감정보 후보 / 아동(14세 미만) 정보**로 분류. 이 분류가 별도 동의(C-1 ⓐⓑ)·step-up 강도(C-8)·보존기간(C-4)·operator 접근통제(C-6)의 일관된 기준이 됨.
- **owner**: Legal Counsel + Engineering
- **증빙 artifact**: 필드×민감도등급 분류표 (C-3 대조표에 통합 가능)
- **확인 방법**: 각 후속 항목(C-1ⓐⓑ/C-4/C-6/C-8)이 이 분류표를 근거로 차등 처리하는지 추적
- **상태**: ⬜

### C-4. 보존기간(retention) + 파기 절차 정의

- **완료 기준**: 대화로그/매직링크/고객식별정보의 보존기간 + 자동 파기/익명화 기준 문서화. append-only 원장(`edu_conversation_log`) 파기/익명화 잡 설계.
- **owner**: Legal Counsel (정책) / Engineering (파기 잡 설계)
- **증빙 artifact**: 테이블별 보존정책 표 + 파기 잡 설계 노트
- **확인 방법 (존재성 아닌 적법성 기준)**:
  - 보존기간 N값의 **근거**(법정 의무기간/서비스 목적 비례성) 명시 — "예: N개월"만으로는 불가
  - append-only ↔ 파기 의무 충돌 해소 방식(소프트삭제/익명화 컬럼) + **백업·로그·서드파티(LLM API) 전송본**까지 파기 범위 포함
  - **익명화 방식의 재식별 방지 기준** 명시(또는 내부 표준 참조)
  - 파기/익명화 **실행 증빙 로그** 포맷 정의(언제·무엇을·몇 건)
- **상태**: ⬜

### C-5. 열람/정정/삭제/철회/처리정지(권리행사) 대응 절차

- **완료 기준**: 고객 read/export/delete + **동의 철회/처리정지** 요청 대응 경로 정의. 누가 받고, 어떻게 본인확인하고, **법정 처리기한 내** 처리하는지.
- **owner**: Legal Counsel + Operations
- **증빙 artifact**: 권리행사 SOP + 문의처 + 요청 접수/처리 **로그 포맷** + SLA(처리기한)·위반 감지·escalation 경로
- **확인 방법**:
  - 접수→본인확인→처리→회신 흐름이 단계로 존재 + 처리기한(SLA) 수치 명시
  - shadow customer/merge(연락처 미입력 이탈자): 본인확인 **불가 시 처리 불가/부분 처리/재식별 금지** 원칙 명시
  - 철회/처리정지 시 resume link 무효화 + 후속 사용 중단 연결(C-1ⓒ와 정합)
- **상태**: ⬜

### C-6. operator 접근통제 확정

- **완료 기준**: `edu_conversation_log` 등 대화 원문은 **최소권한 내부 운영자만** 접근. 누가 어떤 케이스를 볼 수 있는지 권한 범위 정의. 로그/대시보드 원문 무단 노출 금지.
- **owner**: Operations + Engineering
- **증빙 artifact**: 접근권한 매트릭스(역할×테이블×읽기/쓰기) + 승인권자 + 현재 접근 가능 인원 실측 목록 + 접근 로그 보존 정책
- **확인 방법**:
  - 운영자 외 계정에서 대화 원문 접근 시도 차단 확인
  - **최소권한·승인권자·access review 주기·퇴사/권한회수 절차·접근 로그 보존** 명시("내부 운영자"라는 광범위 표현 금지)
  - payer vs actual participant ownership/authority semantics 확정(S-3 참조) — "분리 식별 가능 여부"가 아니라 권리행사·동의·복구링크 소유 주체가 누구인지 확정돼야 함
- **상태**: ⬜

### C-7. resume link 정책 확정 (public_share vs private_resume)

- **완료 기준**: 공유/홍보 링크(`public_share`)와 개인 복구 링크(`private_resume`)가 코드·UX·데이터에서 분리. 복구 링크는 **특정 case**를 열고(최신-by-email 금지), 보안 정책 보유.
- **owner**: Engineering + Legal Counsel
- **증빙 artifact**: `edu_magic_link_events.link_kind` 분기 코드 + 링크 종류별 UX 카피 차이 스크린샷 + 토큰 보안 정책 표
- **확인 방법**:
  - 공유 링크로 개인 기록 접근 불가 확인(IDOR 차단) + 복구 링크가 case 단위로 정확히 열림
  - **토큰 보안**: TTL, 1회성/재사용 여부, 재발급 시 기존 링크 폐기, rate limiting, brute-force/relay 방지, 감사로그 필수 필드
- **상태**: ⬜

### C-8. step-up verification (민감 케이스 / 새 기기)

- **완료 기준**: 민감 케이스 또는 새 기기/브라우저에서 복구 링크를 여는 경우 2차 확인(이메일 일회용 코드 / 전화 뒷자리 / 동일기기 한정) 중 최소 1개 적용. **민감도 판정(C-3S)에 의존하되, 판정 실패 시 fail-safe(보수적으로 step-up 요구)**.
- **owner**: Engineering + Legal Counsel
- **증빙 artifact**: `verify_case_access()` 정책 함수 + step-up 트리거 조건 표 + 이메일 탈취 시 대응 절차
- **확인 방법**: 새 기기 복구 링크 단독 접근 시 step-up 요구 확인 + 민감도 미판정 케이스가 step-up을 우회하지 않음 + 실패/재발급/검증실패가 operator에 기록(관측성)
- **상태**: ⬜

### C-10. 다중기기 세션/복구 동시성 안전성 (신규 — Codex r2)

- **완료 기준**: 구현 설계가 이미 전제하는 다중기기 세션 제어(`version_no`, `active_device_session_id`, `edu_device_sessions`, `lock_case_session()`, lock TTL)가 AR-044 close 전에 **개인정보/권리행사 무결성 관점**에서 race를 막도록 확정. 단순 UX 편의가 아니라 게이트 항목으로 취급.
- **owner**: Engineering + Legal Counsel
- **증빙 artifact**: 동시성 정책 표(잠금 TTL·`version_no` 충돌 시 저장 거부·takeover 시 기존 세션 강제 종료) + race 테스트 시나리오 결과
- **확인 방법**:
  - same-case 동시 접근 시 입력 유실/덮어쓰기 없음(`version_no` 불일치 저장 거부)
  - **stale resume link**: 만료/재발급된 복구 링크로 기존 세션 재개 불가(C-7 토큰 폐기와 정합)
  - **철회 직후 잔존 세션**: 동의 철회/처리정지 시 열려 있던 기존 기기 세션을 강제 종료·읽기차단(C-1ⓒ·C-5와 정합)
- **상태**: ⬜

### C-9. 법무 상태 전환 판정 ("내부 테스트 only" → "실고객 공개 가능")

- **완료 기준**: C-1~C-8(및 C-3S) 증빙 검토 후 Legal Counsel이 `legal_review_approve`(갱신, 무조건부)를 기록하고, 대표가 외부 공개 confirm.
- **owner**: Legal Counsel → 대표
- **증빙 artifact**: `docs/reports/legal/legal_review_edu_conversation_log_v2_<date>.md` (조건 해제 명시) + 대표 confirm 기록
- **확인 방법**:
  - 2026-06-11 조건부 승인의 조건 1~3이 C-1~C-8로 모두 해소됐음을 명시
  - **외부 변호사 자문**: 고위험 미해소 사안(아동·민감·국외이전 중 모호점)이 남으면 외부 변호사 자문 완료가 **close 차단 조건**(단순 참고 아님). 자문 결과 첨부.
- **상태**: ⬜

---

## 3. close 조건 (AR-044 → completed 전환 게이트)

다음을 **모두** 충족할 때만 `AR-044 completed`로 기록한다.

1. C-1 ~ C-10 (및 C-3S) 전 항목 상태 = ✅ (증빙 artifact 경로 첨부), **C-1의 PIPA 비협상 ⓐ~ⓕ 전부 충족**
2. 완료 정의 D1~D5 매핑 충족
3. `legal_review_approve`(갱신) 기록 — 2026-06-11 조건부 승인의 조건 해제 + (고위험 잔여 시) 외부 변호사 자문 완료
4. **`qa_clear`** — C-1/C-2의 공개 고지 문구·링크·버전 표기는 고객-facing 산출물이므로 발행 직전 QA Agent qa_clear 통과 (CLAUDE.md Must)
5. 본 체크리스트 자체가 `red_team_clear` 통과 (저자 Claude 제외, 서로 다른 LLM 2개 이상 cross-verification)
6. 대표 외부 공개 confirm
7. **§5 정합성 차단 항목 해소** (S-1 segment 모델 / S-2 shadow customer 파기범위 / S-3 payer·participant ownership)

> 배포 위생 분리(Codex r1): 위 산출물들의 commit→push→origin + Mac Mini 배포 + 양쪽 청결은 **배포 SoT 규약(별도 운영 의무)**으로 준수하되, 이는 개인정보/법무 의무의 충족 증빙이 **아니다**. git 상태가 맞아도 법무 증빙이 약하면 close 불가, 반대로 법무가 충족됐는데 git 미배포면 배포만 마치면 된다 — 두 축을 혼동하지 않는다.

> AR_PROTOCOL 원칙: "말로만 보고"는 완료 불인정. 각 항목에 파일 경로/URL/실측 로그가 첨부돼야 완료 처리.

---

## 4. 현재 상태 (2026-06-13 기준)

- AR-044 status: **hold** (정당) — 실 외부 익명 트래픽 0, runway 확보.
- legal_review: 2026-06-11 **조건부** `legal_review_approve`(코드/스키마 배포만 승인, 조건 1~3 미해제).
- 본 체크리스트: handoff §2 권장 순서 ①번 산출물 = **이 문서(초안)**.
- runway 근거 관리: "실 외부 익명 트래픽 0"의 예외(테스트 계정·대표/부대표 IP)는 **명시적 allowlist로 관리**해야 하며, 예외 범위가 임의 확장되면 runway 근거가 무너진다.
- 다음 순서(handoff §6):
  1. ✅(이 문서) AR-044 운영 체크리스트 초안
  2. ⬜ 개인정보 처리방침 / 수집 고지 공개 UX 초안 (→ C-1, C-2)
  3. ⬜ 현재 설계 필드 ↔ 최소수집 대조표 + 민감도 분류표 (→ C-3, C-3S)
  4. ⬜ resume link / step-up / operator access 정책 초안 (→ C-6, C-7, C-8)

---

## 5. 정합성 차단 항목 (close-blocking — 미해소 시 close 불가)

> red-team r1 반영: 아래는 단순 "정리 대상"이 아니라 **close 차단 조건**이다. 하위 문서가 상위 설계를 암묵적으로 덮어쓰는 것을 막는다.

- **S-1. segment 모델 충돌**: `edu_customers.segment`가 `parent | worker` 2값 고정(impl §4.1)인데, 상위 지침의 `seeker / target_person / goal` 확장 및 handoff §9-1 "2세그먼트 과도 고정" 지적과 충돌. C-3 대조 시 정리하거나, 확장 모델로 마이그레이션 경로 확정해야 close 가능.
- **S-2. shadow customer 파기/권리행사 범위**: 연락처 미입력 이탈자(shadow)가 C-4 파기 대상·C-5 권리행사 대상에 포함되는지, 본인확인 불가 시 처리 원칙이 정의돼야 close 가능.
- **S-3. payer vs actual participant ownership/authority 확정**: `payer_customer_id`는 모델에 있으나 실질 분리가 impl §8 Phase 3로 미뤄져 있다(impl §4.8). 누가 권리행사 주체이고, 동의 주체이고, 복구 링크 소유자이고, operator 최소권한의 기준 주체인지 — 이 ownership/authority semantics가 확정돼야 C-1·C-5·C-6·C-7이 성립한다. close 전 확정 필수(C-6과 연계).

---

## 6. red-team / 검증 메모

본 문서는 **DRAFT**다. 권위 문서(ACTIVE)로 승격하려면 아래를 **모두** 충족(단독 상태 전환 금지):

- 저자=Claude. **법무/외부 공개 게이트이므로 독립 법무 관점 검토 필수** — 본 문서는 Claude(저자) + Gemini + Codex로 cross-verification 수행.
- `scripts/redteam_review.sh`로 read-only cross-verification → `red_team_clear`
- Legal Counsel 관점 누락 항목 점검 (아동·민감·국외이전·철회·마케팅·위탁 = C-1 ⓐ~ⓕ로 반영됨)
- 상위 게이트 상태(AR-044) · `qa_clear` · 대표 confirm과 **동기화**된 뒤에만 ACTIVE 전환
- 통과 후 RED_TEAM_LOG.md에 기록
- **cross-LLM 검증 기록 영속화**(AGENTS.md 요건: 모델명 + context path + verdict): 각 라운드 verdict·context 스냅샷은 [ar044_checklist_redteam_2026-06-13.md](../reports/llm_outputs/ar044_checklist_redteam_2026-06-13.md)에 보존.

### red-team 이력

- **r1 (2026-06-13)**: Gemini `block` + Codex `block`. 공통 BLOCKER — PIPA 비협상(아동 법정대리인 동의·민감정보 별도 동의·동의 철회·국외 이전) 누락 → C-1 ⓐ~ⓕ 신설로 반영. Codex 추가 — qa_clear 누락(close §4-4 반영), git/배포 게이트 오염(close 분리 주석 반영), 증빙 주관성(C-4/C-5 적법성 기준화), 민감도 분류 부재(C-3S 신설), resume 보안 약함(C-7 강화), operator 최소권한(C-6 강화), 외부변호사 자문 block 조건화(C-9), 정합성 close 차단 승격(§5). Gemini 추가 — 마케팅 별도 동의(C-1ⓔ), 익명화 재식별 방지(C-4).
- **r2 (2026-06-13)**: Gemini `clear`(r1 BLOCKER 전부 반영 확인). Codex `block` — BLOCKER 0, MAJOR 2 + MINOR("r1 핵심 대부분 반영됨" 인정). 잔여 MAJOR 2건 직접 반영: ① 동시성/복구 race를 close 게이트로 승격 → **C-10 신설**(same-case 동시접근·stale resume link·철회 직후 세션 잔존). ② payer vs actual participant를 "관찰"에서 close-blocking ownership/authority 확정으로 승격 → **S-3 신설 + C-6 강화**.
- **r3 (2026-06-13)**: **Gemini `clear`**(BLOCKER 0 / MAJOR 0 / MINOR 0) + **Codex `clear`**(BLOCKER 0 / MAJOR 0 / MINOR 1 비차단). Codex가 r2 잔여 2건(C-10·S-3·C-6) 해소 확인. Codex MINOR(cross-LLM artifact path 영속화)는 [ar044_checklist_redteam_2026-06-13.md](../reports/llm_outputs/ar044_checklist_redteam_2026-06-13.md) 생성 + §6 참조로 해소. → **✅ red_team_clear (2026-06-13)**: 서로 다른 비저자 LLM 2개가 동일 최종본 clear.
