# QA PLAYBOOK
**Version:** 1.0 | **Owner:** Chief of Staff (Codex) | **Gate:** `qa_clear`

---

## 1. 목적

모든 고객-facing 산출물은 발행 직전 `qa_clear`를 통과해야 한다 (CLAUDE.md §5 Must).
QA 없이 고객-facing 산출물을 발행하지 않는다 (CLAUDE.md §6 Never).

## 2. 적용 대상

- Free newsletter issue
- Paid memo / research report
- Marketing copy (제목, 본문, SNS 카피)
- Paid landing page
- 다국어 번역본

`report_publish_approve` 기록 전 `qa_clear`가 prerequisite으로 요구된다.

## 3. QA 체크리스트

### 3-1. Factual

- [ ] 핵심 수치 (가격, 날짜, 성능 수치) 원문 대비 검증
- [ ] 인용된 회사명/제품명 오탈자 없음
- [ ] `verified` / `company-self-report` / `speculative` 근거 자세 명시

### 3-2. Format

- [ ] 마크다운 헤더 계층 일관성
- [ ] 코드 블록 / 인용 정상 렌더링
- [ ] 불필요한 영문 key=value 나열 없음

### 3-3. Schema

- [ ] Notion 아카이브 필드 완전성 (source_url, published_at, tier, evidence_posture)
- [ ] Substack 발행 전 preview URL 정상 확인

### 3-4. Link

- [ ] 본문 내 모든 URL 접근 가능 확인
- [ ] 이미지/차트 broken link 없음

### 3-5. Terminology

- [ ] `대통령님` → `대표님` 수정
- [ ] Physical AI / AGI / robotics 용어 한글 표기 일관성
- [ ] 구독 관련 용어 (무료 구독자, paid subscriber 등) 일관성

### 3-6. 다국어 (해당 시)

- [ ] Cross-LLM fluency 검증 (Claude + Gemini 각각 검토)
- [ ] 직역 티 없이 자연스러운지 모국어 화자 관점 확인

## 4. 프로세스

```
1. QA Agent(또는 Codex)가 위 체크리스트 항목별로 검토 후 결과 기록
2. 모든 항목 통과 시 qa_clear 기록:
   python scripts/openclaw_codex_bridge.py record-decision \
     newsletter_issue <target_id> approved qa_clear \
     --reason "QA pass: factual/format/schema/link/terminology all clear"
3. 실패 항목 발견 시 수정 후 재검토
4. qa_clear 없이 report_publish_approve 불가
```

## 5. QA 실패 처리

- 실패 항목은 별도 QA 리포트 (`docs/reports/qa/`) 에 기록
- 수정 후 재검토 횟수(Retry Count)를 함께 명시
- 비서실장은 QA 결과가 불완전하면 승인하지 않는다 (CLAUDE.md §10)

---

*이 문서가 없으면 `qa_clear` gate를 통과한 산출물이 무엇인지 추적할 수 없다.*
