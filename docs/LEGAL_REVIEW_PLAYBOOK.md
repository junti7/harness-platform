# Legal Review Playbook
# Version: 1.0
# Date: 2026-05-10
# Owner: Legal Counsel Agent

---

## 1. Purpose

이 문서는 Harness가 외부에 발행하거나 결제를 요청하는 모든 산출물의 *법률 사전검토* 절차다.

Legal Counsel Agent는 변호사 자격으로 활동하지 않는다. 이 playbook은 회사 내부의 *위험 차단 1차 게이트*이며, 고위험 사안은 외부 변호사 자문을 권고한다.

`legal_review_approve` 또는 `legal_review_block` 결과를 모든 high-impact 결정에 첨부한다.

---

## 2. When to Invoke

다음 trigger 중 하나라도 발생하면 Legal review를 *반드시* 수행한다.

| Trigger | Owner |
| --- | --- |
| weekly issue / paid memo 외부 발행 | Editor → Legal Counsel |
| paid offer 또는 결제 페이지 카피 변경 | Sales → Legal Counsel |
| 광고/마케팅 캠페인 카피 외부 발행 | Marketing Strategy → Legal Counsel |
| 새 source 추가 또는 scraping 범위 확장 | Evidence Agent → Legal Counsel |
| 개인정보 수집/처리 범위 변경 | Engineering → Legal Counsel |
| 환불/취소/구독 약관 변경 | Product Planning → Legal Counsel |
| 회사/제품 비교 분석 또는 "투자/예측" 표현 포함 | Editor → Legal Counsel |
| 해외(US/EU/Japan/China) 결제 활성화 | Sales → Legal Counsel |
| 대표 또는 부대표의 외부 인터뷰/소셜 발신 | President Office → Legal Counsel |

미발생 trigger도 직감적으로 risk가 있다고 판단되면 Editor가 자발적으로 invoke 가능하다.

---

## 3. Jurisdictions

Phase 1 default 대상국: **대한민국**.

추가 적용 대상:

- 결제 활성화 국가 (Stripe/Paddle 등에서 enable한 국가)
- 외부 발행 plat의 본사 소재지 (Substack=미국, Maily/Stibee=한국)
- 독자 거주국 (geo-targeting marketing 시)

Phase 1 정책: Stripe/Paddle 같은 글로벌 결제는 default 비활성, 한국 결제(Maily, Stibee, Toss 등) 우선.

---

## 4. Korean Law Checklist

### 4.1 자본시장법 (유사 투자자문 행위 금지)

확인 항목:

- 특정 종목 매수/매도 권유 표현 *없음*
- "오를 것이다", "기대수익률", "추천 종목" 등 단정적 투자 표현 *없음*
- 회사/주식 분석 시 "정보 제공 목적이며 투자 자문 아님" disclaimer 포함
- paid 콘텐츠일수록 더 엄격 — 유사 투자자문업 등록 의무 발생 가능성 검토
- 스타트업/비상장 회사 "투자 가치"는 더욱 신중

Block 사유:

- 매매 시점 권유
- 수익률 보장
- 자문업 미등록 상태에서 정기 유료 종목 추천

### 4.2 표시광고법 (과장/허위 광고 금지)

확인 항목:

- "최고", "유일", "1위" 등 절대적 표현은 객관적 근거 필수
- "AI가 자동으로 분석" 표현의 정확성 (실제로 인간 편집 비중을 명시)
- 무료 trial 종료 조건의 명확성
- 환불 가능성에 대한 사실 일치
- 비교 광고 시 정확한 출처와 시점 명시

### 4.3 약관규제법 (불공정 약관 제한)

확인 항목:

- 환불/취소 조항이 한국 소비자 보호 기준을 충족
- 일방적 약관 변경 조항의 합법 범위
- 면책 조항이 과도하지 않음
- 사용자 데이터/권리에 대한 균형

권장 baseline:

- 7일 무조건 환불 가능 (디지털 콘텐츠 개봉 전)
- 약관 변경 시 30일 사전 공지
- 분쟁 해결 관할 명시 (서울중앙지법 또는 본사 소재지)

### 4.4 개인정보보호법 (PIPA)

확인 항목:

- 수집 항목 minimum 원칙
- 동의 받은 목적 외 활용 금지
- 처리 방침 공개
- 제3자 제공 시 별도 동의
- 개인정보 보유 기간 명시
- 안전한 보관 (암호화, 접근통제)
- 만 14세 미만 미가입 또는 법정대리인 동의

paid subscriber 데이터:

- 결제 정보는 PG사가 보유, 회사는 최소 메타데이터만 보관
- email은 marketing 동의 별도 분리
- 탈퇴 시 즉시 익명화 또는 삭제

### 4.5 저작권법 / DB권 보호

확인 항목:

- RSS/scraping 대상 source의 ToS 준수
- robots.txt 존중
- 원문 인용 시 출처 명시 + 분량 제한 (보통 발췌 수준)
- 번역 발행 시 원저작자 표시 + 변형 정도 검토
- AI 요약을 "원문 그대로 재배포"로 오인되지 않게 변형

Risk가 높은 source:

- 유료 미디어 (The Information, Bloomberg, FT) — 무단 인용 금지
- 학술 논문 — 초록까지는 일반적으로 허용, 본문은 라이선스 확인
- 기업 IR/SEC — 공개 자료지만 분석 inferring 시 출처 명확화

### 4.6 부정경쟁방지법

확인 항목:

- 회사명/상표/제품명을 비방 또는 오인 유도하지 않음
- 경쟁사 비교 시 사실 기반 + 비교 시점 명시
- "경쟁사 제품 사용자도 우리 제품을 더 선호" 등 검증 불가능한 표현 금지

---

## 5. International Law Checklist

### 5.1 GDPR (EU 거주자 결제 시)

- explicit consent (opt-in, pre-checked 금지)
- DPO 또는 EU representative 필요성 검토
- right to access / erasure / portability 보장
- 72시간 내 breach 통지 프로세스
- cross-border data transfer 합법 근거 (SCCs 등)

### 5.2 US Securities Risk (영문 paid memo 시)

- "investment advice" 표현 회피
- "not investment advice" disclaimer 명시
- subscribers의 거주지/시민권 trigger 시 reg D, reg S 검토
- 비상장 회사 분석 시 SEC Rule 506 등 일반적 우려는 적지만 신중

### 5.3 일본/대만/중화권 (Phase 2 검토 시)

- 일본 특정상거래법 (특정 commercial transaction law) — 환불 명시
- 중화권은 개별 risk 매우 높음 — Phase 2에서도 후순위

---

## 6. Risk Pattern Library

다음 패턴이 발견되면 *자동 block* 또는 *외부 변호사 자문*.

| Pattern | Severity | Action |
| --- | --- | --- |
| "X 주식이 오를 것" / "지금 사세요" | Critical | 자동 block. 표현 제거 후 재검토 |
| "수익 보장" / "100% 정확" | Critical | 자동 block |
| 경쟁사 직접 비방 | High | block, 사실 기반 + 비교시점 명시로 재작성 |
| 무료 trial 자동 결제 미공지 | High | block, 명시 후 재검토 |
| 개인정보를 marketing copy에 평문 노출 | Critical | 자동 block |
| 스크래핑 source의 ToS 위반 | High | 외부 변호사 자문 또는 source 제외 |
| 미공개 정보 인용 의심 (insider info) | Critical | 자동 block, 출처 재확인 |
| 유료 콘텐츠를 무단 재배포 | Critical | 자동 block |
| 의료/세금/법률 자문성 표현 | High | disclaimer 강제 또는 block |

---

## 7. Disclaimer Templates

### 7.1 일반 disclaimer (모든 issue 하단)

> 본 콘텐츠는 정보 제공 목적이며, 투자, 세무, 법률, 의료 자문이 아닙니다. 결정에 대한 책임은 독자에게 있습니다.

### 7.2 회사/주식 분석 시

> 본 글은 공개된 자료를 기반으로 한 분석이며, 특정 종목 매수/매도를 권유하지 않습니다. 본 글의 발행자는 유사 투자자문업 등록을 하지 않았으며, 투자 자문을 제공하지 않습니다.

### 7.3 paid memo 표지

> 본 보고서는 [발행일] 기준으로 작성된 정보 제공 자료이며, 투자 자문이 아닙니다. 데이터 정확성은 보증되지 않습니다. 본 보고서를 바탕으로 한 모든 결정은 독자의 책임 하에 이루어져야 합니다.

### 7.4 환불 정책 (영문 paid 시)

> Refund within 7 days from purchase, provided the digital content has not been substantially consumed. Refund requests via [contact]. Korean law (소비자보호법) governs Korean residents.

---

## 8. Cross-LLM Verification Process

Legal review는 *서로 다른 신뢰도 높은 LLM 최소 2개* 독립 검토.

권장 페어:

- Claude (1차 reasoning) + Gemini (2차 long-context 약관/법령 검토)
- 또는 Claude + GPT reasoning (US/EU 사안)

절차:

1. 산출물(issue/memo/copy/약관) 원문을 LLM A에 *§4 §5 체크리스트*와 함께 전달
2. LLM A의 risk note 작성
3. 동일 산출물을 LLM B에 *LLM A의 결과를 보지 않은 상태로* 독립 검토
4. 두 결과 비교
5. 동일 결론이면 `legal_review_approve` 또는 `legal_review_block` 기록
6. 결론 충돌 시 third LLM 또는 인간(대표) 결정
7. high-risk 또는 충돌 미해결 시 외부 변호사 자문 권고

audit trail 필수 항목:

- 검토 LLM 이름과 모델 버전
- prompt path
- 두 검토 결과 path (Notion 저장)
- 최종 결정자
- decision timestamp

---

## 9. Output Template

```markdown
# Legal Review Note

- Date:
- Artifact: (issue/memo/copy/약관/source/policy)
- Artifact path:
- Reviewer LLM A:
- Reviewer LLM B:
- Jurisdictions checked: [KR, US, EU, ...]

## Findings

### Critical risks
- (block 사유, 해당 시)

### High risks
- (수정 필요, 해당 시)

### Medium/Low risks
- (참고/disclaimer 보완)

## Required disclaimers
- (적용할 disclaimer 인용)

## Required edits
- 1.
- 2.

## Decision
- [ ] legal_review_approve
- [ ] legal_review_block (사유: )
- [ ] external_counsel_required (사유: )

## Audit trail
- LLM A output: notion://...
- LLM B output: notion://...
- Cross-review timestamp:
```

---

## 10. External Counsel Escalation

다음은 *반드시* 외부 변호사 자문을 받는다.

- 소송 위협 또는 cease-and-desist 수신
- 광고 표현이 자본시장법/표시광고법 위반 가능성 의심
- 해외 결제 도입 시 첫 GDPR/세금 구조
- 데이터 파트너십 또는 기업 라이선스 계약
- 회사 설립 후 첫 약관/개인정보 처리방침 공식화
- 인수/투자 제안 수신
- 공동저작권 분쟁

Cost 처리: `capital_action_approve` + 사전 견적.

---

## 11. Quick Reference

| Question | Default Answer |
| --- | --- |
| paid memo 발행 시 disclaimer 필수? | Yes (§7.3) |
| 비상장 회사 분석 가능? | Yes, 단 추천/매수 표현 금지 (§4.1) |
| 외국 미디어 원문 번역 발행 가능? | 보통 No, 인용 + 출처 명시 가능 (§4.5) |
| 무료 구독자 email로 광고 발송 가능? | marketing 동의 받은 경우만 (§4.4) |
| 환불 거부 가능? | 한국법 7일 보호 외에는 약관에 따름 (§4.3) |
| trial 후 자동 결제 가능? | 명시 + 사전 알림 시 가능 (§4.2) |
| 부대표가 외부 인터뷰 시 사전 검토? | Yes (§2 trigger) |
