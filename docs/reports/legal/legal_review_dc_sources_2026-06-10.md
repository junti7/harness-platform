# Legal Review — 데이터센터 공급망 RSS 소스 3종 추가

- 일자: 2026-06-10 | Gate: `legal_review_approve` | Owner: Legal Counsel Function (Claude)
- 트리거: **web scraping / RSS 수집 정책 변경 (source 추가)** — LEGAL_REVIEW_PLAYBOOK §2
- 대상: `configs/sources/physical_ai.json`의 신규 3종
  - `google_news_mlcc_power_delivery`
  - `google_news_datacenter_connectors_optics`
  - `google_news_cpu_gpu_interconnect`
- 결론: **legal_review_approve (조건부)**

## 1. 사실관계

3종 모두 **Google News RSS 검색 피드**(`news.google.com/rss/search?q=...`)다. 수집물은
기사 **제목 + 짧은 스니펫(summary) + 원문 링크**이며, 용도는 **내부 투자 의사결정(B2I) evidence**다.
외부 발행·재배포·유료 제공 없음. 수집 주기는 `stale_minutes: 1440`(일 1회). 동일 메커니즘의
`google_news_*` 소스 5종이 이미 승인·가동 중이며, 본 3종은 **검색어만 다른 동종 소스**다(선례 존재).

## 2. 체크리스트 검토

### 3-1 표시광고법 / 광고법
- [x] 투자 수익 암시 문구 없음 — 내부 evidence 수집일 뿐, 광고/카피 아님 → **해당 없음(통과)**

### 3-2 자본시장법 (투자자문 유사 행위)
- [x] 투자 권유/특정 종목 매수·매도 권유 없음 — 내부 유니버스 구성용. `CAPITAL_ACTIONS_ENABLED=false`,
      외부 자문 제공 없음 → **통과**

### 3-3 저작권법
- [x] 인용 범위: **제목 + 단문 스니펫 + 링크만** 저장, 본문 전체 복제·외부 재배포 없음 → 내부 참고
      목적의 제한적 이용으로 공정이용 범위 내
- [x] 이미지/차트 미수집 (텍스트 메타데이터만)
- [x] 이용약관: Google News RSS는 공개 피드. 일 1회 폴링으로 과도 크롤링 아님. 기존 승인된
      동종 5종과 동일 posture
- 조건: 본 스니펫을 **외부 발행/유료 제공 시 별도 `report_publish_approve` + 저작권 재검토 필수**

### 3-4 개인정보보호법 (PIPA) / GDPR
- [x] 개인(자연인) 개인정보 수집 없음 — 기업·기술 뉴스 메타데이터. 독자 이메일 등 무관 → **통과**

### 3-5 약관규제법 / 환불 정책
- [x] 구독/결제/환불 요소 없음 → **해당 없음**

## 3. 잔여 리스크 / 조건

1. **내부 사용 한정.** 수집 스니펫의 외부 발행·재배포는 본 승인 범위 밖 — 별도 게이트.
2. 폴링 주기를 일 1회 이상으로 공격적으로 올리지 않는다(ToS 부담 회피).
3. 향후 본 evidence를 외부 투자 콘텐츠로 가공·발행 시 표시광고법/자본시장법 disclaimer 재검토.

고위험 외부 변호사 자문 필요 사안 **없음** (기존 승인 선례와 동일 범주).

## 4. 판정

**legal_review_approve** — 위 3개 조건 준수 전제. red_team_clear(2026-06-10)와 함께
소스 활성화(`enabled:true`)의 선행 게이트 충족.
