# Legal Review — The Robot Report RSS 소스 활성화

- 일자: 2026-06-11 | Gate: `legal_review_approve` | Owner: Legal Counsel Function (Claude)
- 트리거: **web scraping / RSS 수집 정책 변경 (source 활성화)** — LEGAL_REVIEW_PLAYBOOK §2
- 대상: `configs/sources/physical_ai.json`의 `The_Robot_Report`
  - URL: `https://www.therobotreport.com/feed/`
  - source_type: rss / collection_mode: rss_pull / stale_minutes: 1440 (일 1회)
  - 변경: `enabled: false` (STAGED) → `enabled: true`
- 결론: **legal_review_approve (조건부)**

## 1. 사실관계

The Robot Report는 WordPress 기반 로보틱스 산업 뉴스 매체의 **공개 RSS 피드**다(HTTP 200,
유효 RSS 2.0, lastBuildDate 신선, 15개 항목, copyright 태그 없음). 피드에는
`content:encoded`(본문 전문)가 포함된다.

Harness collector(`adapters/content/collector.py`)의 RSS 경로는 **모든 RSS 소스**에 대해
동일하게 동작한다: 제목·링크·summary를 `raw_data`로, `deep_fetch_content(url)` 결과를
`full_content`로 내부 `raw_signals` 테이블에 적재한다. 용도는 **내부 투자 의사결정(B2I)
evidence + Tier 2/3 분석**이며, **외부 발행·재배포·유료 제공 없음**. `CAPITAL_ACTIONS_ENABLED=false`.

본 소스는 기존 승인·가동 중인 RSS 소스들(google_news_* 등)과 **동일한 수집 메커니즘·동일한
내부 사용 posture**다(선례 존재). 차이는 검색 피드가 아니라 단일 매체 피드라는 점뿐이다.

## 2. 체크리스트 검토

### 3-1 표시광고법 / 광고법
- [x] 투자 수익 암시 문구 없음 — 내부 evidence 수집, 광고/카피 아님 → **해당 없음(통과)**

### 3-2 자본시장법 (투자자문 유사 행위)
- [x] 투자 권유/특정 종목 매수·매도 권유 없음 — 내부 유니버스 구성용.
      `CAPITAL_ACTIONS_ENABLED=false`, 외부 자문 제공 없음 → **통과**

### 3-3 저작권법
- [x] 인용/저장 범위: 제목·summary·링크 + 본문(full_content)을 **내부 raw_signals에 한해** 적재.
      외부 복제·재배포·유료 제공 없음 → 내부 분석 목적의 제한적 이용. 기존 승인 RSS 소스와 동일.
- [x] 이미지/차트 미수집 (텍스트만)
- [x] 이용약관: 공개 RSS 피드, 일 1회 폴링(stale_minutes 1440)으로 과도 크롤링 아님.
      피드의 `sy:updatePeriod`=hourly이나 본 시스템은 일 1회로 보수적 폴링.
- **조건(중요):** 본 매체는 full-text 피드이므로, 저장된 본문을 **외부 발행/유료 제공/재배포 시
      반드시 별도 `report_publish_approve` + 저작권 재검토(인용 범위 축소 또는 라이선스 확인) 필수.**
      내부 evidence·요약·신호 추출 용도를 벗어난 본문 원문 노출 금지.

### 3-4 개인정보보호법 (PIPA) / GDPR
- [x] 개인(자연인) 개인정보 수집 없음 — 기업·기술 뉴스. 독자 이메일 등 무관 → **통과**

### 3-5 약관규제법 / 환불 정책
- [x] 구독/결제/환불 요소 없음 → **해당 없음**

## 3. 잔여 리스크 / 조건

1. **내부 사용 한정.** full-text 본문의 외부 발행·재배포는 본 승인 범위 밖 — 별도 게이트(`report_publish_approve` + 저작권 재검토).
2. 폴링 주기를 일 1회(stale_minutes 1440) 이상으로 공격적으로 올리지 않는다(ToS 부담 회피).
3. 향후 본 evidence를 외부 투자 콘텐츠로 가공·발행 시 표시광고법/자본시장법 disclaimer + 저작권 재검토.

고위험 외부 변호사 자문 필요 사안 **없음** (기존 승인 RSS 선례와 동일 범주, full-text 조건만 추가).

## 4. 판정

**legal_review_approve** — 위 3개 조건 준수 전제. red_team_clear(2026-06-11)와 함께
소스 활성화(`enabled:true`)의 선행 게이트 충족.
