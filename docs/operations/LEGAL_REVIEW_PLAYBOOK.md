# LEGAL REVIEW PLAYBOOK
**Version:** 1.0 | **Owner:** Legal Counsel Function | **Gate:** `legal_review_approve`

---

## 1. 목적

외부 발행, 유료 제안, 데이터 수집 정책 변경, 자본 집행 전에 법률 리스크를 사전 검토한다.
Legal Counsel review가 누락된 외부 발행/유료 제안/광고 카피를 발송하지 않는다 (CLAUDE.md §6 Never).

## 2. 적용 대상

다음 중 하나라도 해당하면 `legal_review_approve`가 prerequisite이다:

- `report_publish_approve` (외부 발행 / 유료 리포트)
- `monetization_experiment_approve` (paid 실험 / 구독 모델 변경)
- `investment_thesis_approve` (투자 thesis 외부 공유)
- `capital_action_approve` (실제 비용 집행)
- 외부 광고/마케팅 카피 최초 발행
- web scraping / RSS 수집 정책 변경
- 해외 판매 개시

## 3. 검토 항목

### 3-1. 표시광고법 / 광고법

- [ ] 투자 수익 암시 문구 없음
- [ ] 과장/허위 표현 없음
- [ ] "AI가 분석한" 등 기계 판단 명시 여부

### 3-2. 자본시장법 (투자자문 유사 행위)

- [ ] 투자 권유 또는 특정 종목 매수/매도 권유 없음
- [ ] 리포트가 투자 참고용임을 명시 (disclaimer 포함)

### 3-3. 저작권법

- [ ] 인용된 원문이 공정이용 범위 내
- [ ] 이미지/차트 출처 표기 또는 자체 제작 확인
- [ ] RSS/스크래핑 대상 사이트 이용약관 검토

### 3-4. 개인정보보호법 (PIPA) / GDPR (해외)

- [ ] 독자 이메일 수집 근거 명시 (구독 동의)
- [ ] 해지/데이터 삭제 요청 처리 절차 존재
- [ ] 해외 수신자 대상 시 GDPR 적용 여부 검토

### 3-5. 약관규제법 / 환불 정책

- [ ] 구독 취소/환불 조건 명시
- [ ] 불공정 약관 조항 없음

## 4. 프로세스

```
1. Legal Counsel Function(또는 Codex 초안)이 위 체크리스트 검토
2. 고위험 사안은 "외부 변호사 자문 필요" 명시 후 대표 에스컬레이션
3. 검토 통과 시 legal_review_approve 기록:
   python scripts/openclaw_codex_bridge.py record-decision \
     <target_type> <target_id> approved legal_review_approve \
     --reason "Legal review pass: 표시광고법/저작권/PIPA 검토 완료"
4. legal_review_approve 없이 high-impact gate 불가
```

## 5. Disclaimer 템플릿

유료 리포트 / 뉴스레터 하단 필수 포함:

```
본 콘텐츠는 정보 제공 목적으로만 작성되었으며, 투자 권유 또는 투자 자문이 아닙니다.
투자 결정은 독자의 판단과 책임 하에 이루어져야 합니다.
Harness는 본 콘텐츠로 인한 투자 손실에 대해 책임을 지지 않습니다.
```

---

*Legal Counsel은 변호사 활동을 대체하지 않는다. 외부 발행 전 고위험 사안은 반드시 외부 변호사 자문을 받는다.*
