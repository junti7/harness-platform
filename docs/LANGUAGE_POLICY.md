# Language Policy
# Version: 1.0
# Date: 2026-05-10
# Owner: Product Planning + QA Agent

---

## 1. Strategic Question

대표 질문:

> "리포트 제공 언어는 한국어/영어 정도로 하는 것이 좋을지 아니면 다국어를 더 추가하는 것이 좋을지"

답:

**Phase 1은 한국어 단일 + 선택적 영어 (paid memo only). 다국어 확장은 Phase 1 검증 후에만.**

이 문서는 그 결정의 근거와 단계별 진입 조건을 정의한다.

---

## 2. Core Principle

> **하나의 언어에서 paid 검증되지 않은 콘텐츠를 여러 언어로 동시 launch하면, 약한 콘텐츠를 *여러 언어로* 갖게 될 뿐이다.**

이 원칙의 근거:

- LLM 번역 품질은 "이해 가능"이지 "현지 독자가 신뢰할 만한 자연스러움"은 아니다.
- QA burden은 언어당 N배. 본 사이즈(2명+LLM)에서 다국어 동시 운영은 QA collapse 위험.
- subscription platform의 운영 (가격, 결제, 환불, 약관)도 언어별로 다르다.
- brand voice / tone은 언어마다 재정의 필요.
- 한 언어에서 paid 1명조차 없는 상태에서 다국어 확장은 *vanity expansion*이다.

---

## 3. Phase 1 Default

### 3.1 Active Languages

| Language | Status | Use |
| --- | --- | --- |
| 한국어 | **Primary** | weekly issue, marketing copy, paid memo, 모든 외부 발신 default |
| English | **Secondary, on-demand** | inbound 영문 paid memo 의뢰가 있을 때만 작성. 정기 영문 발행은 *없음* |

### 3.2 Why Korean First

- 대표/부대표 native fluency → QA 가능
- 한국 Physical AI/AGI 한국어 분석 콘텐츠 *공급이 부족*함 → moat 가능
- 한국 결제 인프라 (Maily, Stibee, Toss 등) 단순
- 법률 (한국 자본시장법, PIPA 등) 적용 명확
- 부대표가 한국어 자연스러움 review 가능

### 3.3 Why English Only On-Demand

- 영문 paid memo 시장은 큼 (Stratechery, SemiAnalysis 등)
- 그러나 정기 영문 issue를 한국어와 동시 발행하면 *둘 다 약해짐*
- Phase 1에서는 inbound 영문 lead 발생 시에만 *single memo* 단위로 작성
- 정기 영문 발행 여부는 Phase 2 검토 사안

### 3.4 Forbidden in Phase 1

- 정기 영문 newsletter 발행
- 한국어 issue를 즉시 영문으로 자동 번역해 동시 발행
- Japanese, Chinese, Spanish, German 등 추가 언어로 발신
- Korean issue를 영문 SNS post로 그대로 자동 번역해 발신 (인용/요약은 가능, 발행 단위 번역 금지)

---

## 4. Quality Bar by Language

| Language | Quality bar | Required reviewer |
| --- | --- | --- |
| 한국어 | Native publishable | 부대표 + QA Agent |
| English | Native-level fluency in technical content | QA Agent (Claude + Gemini cross-check) + 가능한 경우 native English speaker review |
| Other | Phase 1에서 사용 안 함 | N/A |

영문 paid memo 발행 시 *반드시* QA cross-LLM verification (§7).

---

## 5. Phase 2 Trigger Conditions

다음 조건이 *모두* 충족되면 다국어 확장을 검토한다.

조건 (AND):

- 한국어 paid subscriber 50명 이상, OR 한국어 paid 매출 월 ₩500K 이상
- 한국어 weekly issue 12회 이상 안정 발행
- 영문 inbound paid memo 5건 이상 처리 경험
- QA pipeline + Legal review pipeline 안정 운영
- 부대표 OJT module 4 이상 통과 (semiconductor/compute 기초 완료)

위 5조건 충족 *전*까지 다국어 확장 금지.

---

## 6. Phase 2 Language Candidates

Phase 2 진입 시 추가 검토 우선순위.

### Tier 1 (가장 적합)

**1. 영어 (정기 발행)**

- 가장 큰 market, 익숙한 인프라 (Substack/Stripe)
- Korean issue의 영문 변형 가능 (하지만 자동번역 X, 별도 작성)
- 법적 risk: US securities (§5.2 LEGAL_REVIEW_PLAYBOOK), GDPR

### Tier 2 (가능하지만 신중)

**2. 일본어**

- 일본은 Physical AI / 로봇 강국, paid newsletter 시장도 형성됨
- 한국과 기술 관심 영역 유사 → Korean 콘텐츠의 변형 가능성
- 단, Japanese native fluency 인력 없음 → native reviewer 외주 필요
- 법률: 일본 특정상거래법 (refund 명시 의무)
- Phase 2에서도 *후순위*

### Tier 3 (높은 risk, deprioritize)

**3. 중국어 (간체/번체)**

- TAM 큼, 그러나 시장 접근성 낮음 (Great Firewall, 결제, 콘텐츠 검열 risk)
- Phase 1/2에서는 *진입 금지*

**4. 독일어 / 스페인어 / 프랑스어**

- robotics 관심 시장 존재하나 한국팀의 native fluency 없음
- 비용 대비 효과 낮음 → Phase 3 이후 검토

---

## 7. Translation Workflow (다국어 확장 시)

다국어 발행이 활성화되면 *반드시* 아래 workflow를 따른다.

### 7.1 절대 금지

- LLM 자동번역만으로 발행
- 한국어 → 영어 그대로 직역 (cultural localization 없이)
- native reviewer 없이 paid 콘텐츠 발행

### 7.2 권장 workflow

```
Korean issue (master)
    ↓
LLM A 번역 draft (Claude or GPT)
    ↓
LLM B independent review (Gemini)
    - factual accuracy
    - tone fit
    - cultural localization
    ↓
QA Agent
    - schema, links, format
    - terminology consistency
    ↓
(가능 시) human native reviewer
    ↓
Legal Counsel re-check (광고/규제 표현이 해당국 법에 맞는지)
    ↓
publish 별도 channel
```

### 7.3 동시 발행 vs 시차 발행

권장: *시차 발행*. master 언어 발행 후 1~3일 후 추가 언어 발행.

- 첫 reader 피드백을 master 언어에서 받고 수정 가능
- urgency 차이 (한국 시장 vs 글로벌 시장)
- QA 부담 분산

---

## 8. Multi-Language QA Checklist

QA Agent가 다국어 콘텐츠 발행 전 확인.

| 항목 | 한국어 | 영어 | (Phase 2) 일본어 |
| --- | --- | --- | --- |
| 문법/맞춤법 | 부대표 review | LLM cross-check | native reviewer |
| 기술용어 일관성 | terminology DB 참조 | terminology DB 참조 | terminology DB 참조 |
| 회사/제품명 표기 | 한글/영문 표기 정책 | 영문 정식명칭 | 카타카나 표기 정책 |
| 단위/통화 | ₩, %  | $, % | 円, % |
| 날짜 형식 | YYYY-MM-DD | YYYY-MM-DD | YYYY年MM月DD日 |
| disclaimer | §7.1 한국어 | §7.4 영문 | 일본어 disclaimer (별도 작성) |
| 환불 약관 | 한국 소비자보호법 | 7-day refund | 일본 특정상거래법 |
| 링크 정상 동작 | 모든 언어 | 모든 언어 | 모든 언어 |
| 결제 페이지 일치 | platform별 별도 | platform별 별도 | platform별 별도 |

---

## 9. Risks of Premature Multilingual Expansion

흔한 실패 패턴:

1. **약한 콘텐츠를 여러 언어로**: 한국어에서 검증 안 된 신호를 영어로 동시 발행 → 두 시장 모두 신뢰 잃음
2. **QA collapse**: 언어당 review 시간 부담 N배 → 발행 주기 깨짐 → reader 이탈
3. **Brand voice 분열**: 같은 회사인데 언어별 tone 다름 → 정체성 혼란
4. **법률 risk 곱셈**: 각 언어/시장의 별도 법률 risk → 외부 변호사 비용 폭증
5. **결제 인프라 분산**: 언어별 platform/통화/환불 정책 → 운영 복잡성
6. **Customer support 한국어만 가능**: 영문 paid 고객의 환불/문의를 한국어로 답변 → 신뢰 하락

---

## 10. Decision Rule

| 상황 | 권장 |
| --- | --- |
| Phase 1 (현재) | 한국어 + 영어 on-demand. 다른 언어 *금지*. |
| Phase 2 진입 조건 충족 | 영문 정기 발행 *검토 가능*. 일본어는 *별도 case*. |
| Phase 2 진입 조건 미충족 상태에서 다국어 요청 | 거절. 검토 조건 만족 후 재요청. |
| 일회성 다국어 inbound 의뢰 (paid memo) | case-by-case. native reviewer 비용은 paid memo 가격에 반영. |
| LLM 자동번역으로 SNS post 작성 | 인용/요약 수준은 OK. 발행 단위 번역 금지. |

---

## 11. Quick Reference

| Question | Default Answer |
| --- | --- |
| 정기 영문 newsletter 시작 가능? | Phase 2 조건 충족 후 |
| 한국어 issue를 자동번역해서 영문으로 동시 발행? | No |
| inbound 영문 paid memo 가능? | Yes (cross-LLM QA + Legal 통과 시) |
| Japanese 시장 매력적이라 시작 가능? | Phase 2에서도 후순위. native reviewer 확보 후 |
| 중국어 진입? | Phase 1/2 금지 |
| 다국어 SNS post 자동 generate? | 짧은 발췌/요약은 OK, 발행 단위 자동 번역 금지 |
| 부대표가 영문 review 가능? | 한국어 review가 primary. 영문은 cross-LLM + (필요 시) 외주 native reviewer로 보완 |
