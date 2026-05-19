# BUSINESS RISK MANAGEMENT PLAYBOOK
# Version: 1.0 | Owner: Business Risk Management Team | Date: 2026-05-19
# 상위 규약: CLAUDE.md §2 Business Risk Management, AGENTS.md §3.16

---

## 1. 목적

Harness 사업 전반의 위험을 *상시* 식별·평가·추적·경감한다.

Red Team(이벤트 기반 artifact 검증), Legal Counsel(법률 gate), Pre-Mortem(의사결정 직전 worst-case), Business Operations(KPI 추적)은 각자 특정 시점에 작동한다. BRM은 이 4개 팀의 출력을 통합해 전사 리스크 지형을 **상시** 관리하는 조직이다.

BRM이 없으면 개별 gate는 통과해도 전사 차원 리스크 누적을 감지하지 못한다.

---

## 2. 리스크 분류 체계

### 2.1 리스크 유형 (6개 차원)

| 유형 | 포함 범위 |
| --- | --- |
| **재무 (FIN)** | LLM API 비용 소진율, runway, 예산 대비 실적, paid subscriber ROI |
| **운영 (OPS)** | 파이프라인 장애, 데이터 품질, Slack/Notion/Anthropic/Substack 의존도, 단일 장애 지점 |
| **전략 (STR)** | 시장 타이밍, 경쟁 위협, 콘텐츠 포지셔닝 취약성, 30-day / 90-day target 달성 저해 요인 |
| **법적·규제 (LEG)** | Legal Counsel 미결 사안, 규제 변경, 외부 변호사 자문 필요 사안 |
| **평판 (REP)** | 발행 후 사실 오류 누적, 독자 반응 이상징후, 외부 채널 노출 오류 |
| **기술 (TECH)** | LLM 벤더 의존도, 보안 취약점 open 상태, API rate limit/비용 급증, infra 단일 장애점 |

### 2.2 리스크 등급 매트릭스

발생 확률(P) × 영향도(I)로 등급을 결정한다.

|  | 영향 low | 영향 medium | 영향 high | 영향 critical |
| --- | --- | --- | --- | --- |
| **확률 low** | 모니터링 | 모니터링 | 완화 조치 | 완화 조치 |
| **확률 medium** | 모니터링 | 완화 조치 | **에스컬레이션** | **에스컬레이션** |
| **확률 high** | 완화 조치 | **에스컬레이션** | **에스컬레이션** | **즉시 대응** |

- **모니터링**: 주간 레지스터에 기록, 변화 추적
- **완화 조치**: 담당 팀 배정 후 mitigation plan 실행
- **에스컬레이션**: `risk_escalation_note` → CEO 모바일 카드 발행
- **즉시 대응**: CEO 즉시 통보 + 해당 팀 동시 알림 + 운영 일시 중단 검토

---

## 3. 주간 운영 Cadence

### 3.1 일정

- **cadence**: 매주 1회 정례
- **time**: 매주 월요일 09:00 KST (Red Team 정례 1시간 전)
- **owner**: Business Risk Management Agent
- **입력 마감**: 직전 금요일 18:00 KST (각 팀 주간 출력 수신)

### 3.2 주간 작업 순서

```
1. 입력 수집 (금요일까지 수신)
   - Legal Counsel: legal_review_note, regulatory_risk_memo
   - Red Team: red_team_clear / red_team_block 결과
   - Business Operations: goal_health_brief, forecast_memo, anomaly_note
   - Pre-Mortem: 이번 주 신규 pre_mortem 문서
   - 시스템: subscriber 수, LLM API 비용, Slack/Notion/Anthropic 상태

2. 리스크 레지스터 업데이트 (docs/governance/RISK_REGISTER.md)
   - 신규 리스크 추가
   - 기존 리스크 상태/완화조치 업데이트
   - 해소된 리스크 이동

3. 임계값 점검 (§4 자동 escalation 기준 대조)
   - 임계값 초과 항목 → risk_escalation_note 즉시 발행

4. risk_brief 작성 (CEO 모바일 카드)
   - 상위 5개 리스크 요약 (등급 높은 순)
   - 이번 주 신규 / 해소 / 상태 변경 항목
   - 요청 action (있는 경우)

5. pre_mortem_review_note 작성 (이번 주 신규 Pre-Mortem이 있는 경우)
   - §6 체크리스트 검토

6. 결과 전달
   - risk_brief → CEO 모바일 (Slack #exec-president-decisions)
   - risk_escalation_note (해당 시) → CEO 즉시
   - RISK_REGISTER.md 업데이트 커밋
```

---

## 4. 자동 Escalation 임계값

아래 조건 중 하나라도 충족되면 `risk_escalation_note`를 즉시 발행하고 해당 팀에 동시 통보한다. 주간 cadence를 기다리지 않는다.

| ID | 유형 | 임계값 | 통보 대상 |
| --- | --- | --- | --- |
| ESC-FIN-1 | 재무 | 일일 LLM API 비용 ≥ `DAILY_COST_LIMIT_USD` × 80% | CEO |
| ESC-FIN-2 | 재무 | 30일 runway 미만 예상 | CEO |
| ESC-STR-1 | 전략 | 30-day target 달성 가능성 < 50% (Business Operations 예측 기준) | CEO + Business Operations |
| ESC-STR-2 | 전략 | 90일 연속 매출 0 (`KILL_CRITERIA.md` 트리거) | CEO + Business Operations |
| ESC-LEG-1 | 법적 | 미결 `legal_review_block` 존재 시 외부 발행 진행 시도 감지 | CEO + Legal Counsel |
| ESC-TECH-1 | 기술 | HIGH 등급 보안 취약점 open 7일 초과 | CEO + Red Team |
| ESC-TECH-2 | 기술 | LLM API (Anthropic/Ollama) 서비스 장애 2시간 초과 | CEO |
| ESC-REP-1 | 평판 | 발행된 콘텐츠의 사실 오류 보고 후 24시간 내 미수정 | CEO + QA Team |
| ESC-KILL-1 | 전략 | `docs/governance/KILL_CRITERIA.md` 트리거 항목 감지 | CEO + Business Operations (즉시) |

---

## 5. 리스크 레지스터 관리

### 5.1 등록 기준

다음 조건 중 하나를 만족하면 즉시 리스크 레지스터에 등록한다.

- 발생 확률 medium 이상 + 영향도 high 이상
- 발생 확률에 무관하게 영향도 critical
- Legal Counsel이 발행한 `legal_review_block`
- Red Team이 발행한 `red_team_block`
- 임계값(§4) 근접 징후 (80% 이상)

### 5.2 레지스터 필드

```
ID          : <유형코드>-<NNN>  예) FIN-001, TECH-003
유형        : 재무 / 운영 / 전략 / 법적·규제 / 평판 / 기술
설명        : 리스크 내용 요약 (1~2줄)
발생 확률   : low / medium / high
영향도      : low / medium / high / critical
현재 상태   : open / mitigating / accepted / resolved
완화 조치   : 진행 중이거나 계획된 구체적 행동
Owner       : 담당 팀/에이전트
감지일      : YYYY-MM-DD
해소일      : YYYY-MM-DD 또는 —
관련 gate   : red_team_block / legal_review_block / 해당 없음
```

### 5.3 상태 전이 규칙

```
open → mitigating   : 완화 조치가 실행 중일 때
open → accepted     : 대표가 잔존 리스크를 인지하고 수용 결정 시
                      (이유와 재검토 시점을 레지스터에 명시)
mitigating → resolved : 완화 조치 완료 + BRM 검증 완료
any → open          : 완화 조치 실패 또는 재발 시 롤백
```

`accepted` 상태의 리스크는 대표의 명시적 승인 없이 그대로 두지 않는다. 매주 `accepted` 항목의 잔존 리스크를 `risk_brief`에 포함한다.

---

## 6. Pre-Mortem 품질 검토

BRM은 제출된 Pre-Mortem 문서가 `PRE_MORTEM_PROTOCOL.md`의 요건을 충족하는지 검토하고 `pre_mortem_review_note`를 발행한다.

### 6.1 검토 체크리스트

- [ ] 최악 시나리오 3개 이상 작성됨
- [ ] 각 시나리오에 발생 확률 (low/medium/high 또는 %) 명시됨
- [ ] 최대 손실이 금전적/평판/운영 3개 측면 중 최소 2개 포함됨
- [ ] 회복 가능성 (recoverable / partially recoverable / unrecoverable) 표기됨
- [ ] Mitigation 조치가 1개 이상 구체적으로 명시됨
- [ ] Detection Trigger — 실패를 언제 인지할 수 있는지 명시됨
- [ ] BRM 리스크 레지스터 기존 항목과 중복/충돌 없음 (또는 충돌 시 명시)

### 6.2 처리 기준

| 결과 | 조건 | 다음 단계 |
| --- | --- | --- |
| **통과** | 체크리스트 전 항목 충족 | `pre_mortem_review_note` 통과 → `pre_mortem_approve` 기록 가능 |
| **반려** | 누락 항목 존재 | 반려 사유 명시 → 작성 팀에 회송 → 재제출 후 재검토 |
| **조건부 통과** | 경미한 누락 (1항목) + 리스크 낮음 | 누락 항목 즉시 보완 조건으로 통과 |

BRM은 Pre-Mortem을 단독으로 작성하거나 내용을 수정하지 않는다. 검토와 품질 판정만 수행한다.

---

## 7. Kill Criteria 모니터링

`docs/governance/KILL_CRITERIA.md`에 정의된 중단/전환 트리거를 주간 단위로 점검한다.

### 7.1 모니터링 항목 (Kill Criteria 연동)

- 90일 이상 매출 0 지속
- 60일 이상 weekly issue 미발행
- 부대표 content review 3회 연속 실패
- 누적 법적 리스크 미해소 상태에서 외부 발행 강행
- 보안 취약점 미수정 상태에서 CEO Slack 채널 지속 운영

### 7.2 트리거 감지 시 프로세스

```
1. ESC-KILL-1 risk_escalation_note 즉시 발행
2. CEO 모바일 카드 전송 (Slack #exec-president-decisions)
3. Business Operations Agent 동시 통보
4. 해당 파이프라인 실행 보류 권고 (CEO 결정 전까지)
5. BRM이 단독으로 운영 중단 결정을 내리지 않는다
   → 결정은 반드시 대표가 내린다
```

---

## 8. 타 팀과의 협업 인터페이스

### 8.1 BRM이 받는 입력

| 팀 | 출력 | 수신 주기 |
| --- | --- | --- |
| Legal Counsel | `legal_review_note`, `regulatory_risk_memo`, `legal_review_block` | 이벤트 발생 시 즉시 + 주간 |
| Red Team | `red_team_clear` / `red_team_block` | 이벤트 발생 시 즉시 + 주간 |
| Business Operations | `goal_health_brief`, `forecast_memo`, `anomaly_note` | 주간 (또는 이상 감지 즉시) |
| Pre-Mortem (작성 팀) | `pre_mortem_memo` | 이벤트 발생 시 |
| 시스템 | LLM API 비용, subscriber 수, 파이프라인 오류 로그 | 상시 |

### 8.2 BRM이 발행하는 출력

| 출력 | 수신 팀 | 발행 조건 |
| --- | --- | --- |
| `risk_register` 업데이트 | 전팀 참조 가능 | 주간 정례 |
| `risk_brief` | CEO | 주간 정례 |
| `risk_escalation_note` | CEO + 해당 팀 | 임계값 초과 즉시 |
| `pre_mortem_review_note` | Pre-Mortem 작성 팀, CEO | Pre-Mortem 제출 즉시 |

### 8.3 팀별 경계 명확화

| 팀 | BRM에 위임하는 것 | BRM이 개입하지 않는 것 |
| --- | --- | --- |
| Legal Counsel | 미결 legal_review_block의 전사 영향 추적 | 법률 해석, disclaimer 작성 |
| Red Team | red_team_block의 잔존 리스크 레지스터 등록 | cross-LLM 검증 수행 |
| Business Operations | KPI 이상 징후의 전략 리스크 등록 | goal_model_spec 변수 관리 |
| QA Team | 사실 오류 미수정의 평판 리스크 등록 | factual claim 검증 |
| Pre-Mortem 작성 팀 | Pre-Mortem 품질 검토 | Pre-Mortem 내용 작성/수정 |

---

## 9. 산출물 템플릿

### 9.1 risk_brief (CEO 모바일 카드)

```markdown
# Risk Brief — YYYY-MM-DD

**상위 리스크 (등급 순)**

| # | ID | 유형 | 설명 | 확률 | 영향 | 상태 |
|---|----|----|------|------|------|------|
| 1 | TECH-001 | 기술 | ... | medium | high | mitigating |
| 2 | STR-001 | 전략 | ... | medium | high | open |
| ... | | | | | | |

**이번 주 변경사항**
- 신규: [ID] — 설명
- 해소: [ID] — 해소 방법
- 상태 변경: [ID] open → mitigating

**CEO 확인 필요 항목**
- [있는 경우만] accepted 상태 리스크 재승인 요청: [ID]

**다음 주 모니터링 포인트**
- [주목해야 할 항목 1~2개]
```

### 9.2 risk_escalation_note

```markdown
# Risk Escalation — YYYY-MM-DD HH:MM KST

**트리거**: ESC-<유형>-<N> — <임계값 설명>
**리스크 ID**: <ID>
**현재 수치**: <실제 값> (임계값: <기준값>)
**영향**: <즉각적 영향 설명>
**권고 조치**: <즉시 취할 수 있는 행동>
**결정 권한**: 대표(CEO)

통보 팀: <Legal Counsel / Red Team / Business Operations / QA Team 중 해당>
```

### 9.3 pre_mortem_review_note

```markdown
# Pre-Mortem Review Note — YYYY-MM-DD

**대상 결정**: <의사결정 제목>
**제출 팀**: <작성 팀>
**검토 결과**: 통과 / 반려 / 조건부 통과

**체크리스트 결과**
- [x] 최악 시나리오 3개 이상
- [x] 발생 확률 명시
- [ ] 회복 가능성 표기 — ❌ 누락
...

**반려 사유** (반려 시)
- 누락 항목: <항목명>
- 수정 요청: <구체적 내용>

**BRM 리스크 레지스터 연동**
- 신규 등록: [ID] — Pre-Mortem 시나리오 중 open 항목
```

---

## 10. 프로세스 요약

```
[상시 모니터링]
시스템 지표 수집 → 임계값 초과 감지 → risk_escalation_note 즉시 발행

[주간 정례 (월요일 09:00 KST)]
1. 각 팀 출력 수신 (Legal / Red Team / BizOps / Pre-Mortem)
2. RISK_REGISTER.md 업데이트
3. 임계값 점검 → 초과 항목 즉시 escalation
4. risk_brief 작성 → CEO 모바일 카드 발행
5. pre_mortem_review_note 작성 (신규 Pre-Mortem 있을 경우)

[이벤트 기반 즉시 대응]
- legal_review_block 수신 → LEG 리스크 등록 + CEO 알림
- red_team_block 수신 → TECH 리스크 등록
- Kill Criteria 트리거 감지 → 즉시 CEO + Business Operations 동시 통보
```

---

## 11. Non-Negotiables

- BRM은 리스크 정보를 제공하며, 운영 중단·재개 결정은 대표가 내린다.
- 임계값(§4) 초과 시 주간 cadence를 기다리지 않고 즉시 `risk_escalation_note`를 발행한다.
- `accepted` 리스크는 매주 `risk_brief`에 포함해 대표가 인지하도록 한다.
- 리스크 레지스터를 갱신하지 않은 상태에서 이전 주 데이터로 `risk_brief`를 작성하지 않는다.
- Pre-Mortem 내용을 BRM이 단독 수정하지 않는다. 반려 후 재제출이 원칙이다.
- `KILL_CRITERIA.md` 트리거 감지 시 BRM이 단독으로 운영을 중단하지 않는다.
- Legal Counsel / Red Team / QA의 판정을 BRM 단독 판단으로 역전하지 않는다.

---

*이 문서는 BRM Team의 주간 운영 표준이다. 리스크 레지스터 실제 데이터는 `docs/governance/RISK_REGISTER.md`에 유지한다.*
