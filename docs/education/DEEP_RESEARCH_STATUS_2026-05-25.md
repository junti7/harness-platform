# 교육 DEEP RESEARCH 수집 상태 보고
> correlation_id: edu-consulting-20260524 | AR-026 | 2026-05-25

---

## 1. 레지스트리 현황

| 항목 | 이전 | 현재 |
|---|---|---|
| 전체 소스 수 | 21개 | **73개** |
| 버전 | v0.2 | **v0.3** |
| 참조 기준 | — | DATA_GATHERING_UNIVERSE.md |

---

## 2. 실제 수집 결과 (2026-05-25)

| 소스 | 건수 | 파일 | 상태 |
|---|---|---|---|
| RSS (14개 채널) | 70건 | `rss_collected.json` | ✅ |
| ERIC API | 20건 | `eric_collected.json` | ✅ |
| OpenAlex API | 35건 | `openalex_edu_focused.json` | ✅ |
| Hacker News | 29건 | `hackernews_collected.json` | ✅ |
| Google Play 리뷰 (콴다) | 10건 | `gplay_reviews.json` | ✅ |
| **합계** | **164건** | — | — |

수집 디렉토리: `data/edu_research/2026-05-25/`

---

## 3. 실패 소스 원인 진단 및 극복 방안

### 3-A. RSS URL 무효화 (404 / HTML 반환)

| 소스 | 원인 | 극복 방안 |
|---|---|---|
| EdWeek | RSS URL 변경 (404) | edweek.org 사이트에서 최신 RSS URL 수동 확인 |
| Edutopia | RSS 엔드포인트 HTML 반환 (RSS 단종 의심) | Edutopia Newsletter 구독 + 수동 스크래핑 |
| Anthropic Blog | `/news/rss.xml` 404 | Anthropic 공식 Twitter/LinkedIn 모니터링으로 대체 |
| Brookings | 200이지만 HTML 반환 | `brookings.edu/feed/` 재확인 후 대체 채널로 전환 |
| WEF | XML mismatched tag | WEF API(`https://www.weforum.org/api/v1/`) 직접 사용 검토 |
| 연합뉴스 | Connection reset (IP 차단) | 연합뉴스 Open API 신청(`yonhapnewstv.co.kr`) |
| 조선일보 | 404 | 조선일보 RSS 재발굴 (`chosun.com/rss/chosun_rss.xml`) |

> **단기 극복**: NewsAPI.org 무료 tier(100req/일)로 이 사이트들의 기사 헤드라인 수집 가능
> URL: `newsapi.org/v2/everything?q=AI+education&language=ko` (API 키 필요)

### 3-B. Semantic Scholar 429 Rate Limit

- **원인**: API 키 없이 호출 시 1req/s 미만 제한. 이전 테스트에서 이미 소진.
- **상태**: `SEMANTIC_SCHOLAR_API_KEY`가 `.env`에 없거나 만료됨
- **극복 방안**: `.env`에 키 추가
  ```
  SEMANTIC_SCHOLAR_API_KEY=your_key_here
  ```
  키 발급: https://api.semanticscholar.org/  
  무료 등록 완료 시 100req/s로 상향됨

### 3-C. Reddit API 미설정

- **원인**: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` 미등록
- **극복 방안**:
  1. https://www.reddit.com/prefs/apps 접속
  2. "script" 타입 앱 생성 (무료)
  3. `.env`에 추가:
     ```
     REDDIT_CLIENT_ID=your_id
     REDDIT_CLIENT_SECRET=your_secret
     REDDIT_USER_AGENT=harness-edu-research/0.1
     ```
  4. praw 이미 설치됨 → 즉시 수집 가능

### 3-D. arXiv API Timeout

- **원인**: `http://` → `https://` 리다이렉트 + DNS/네트워크 지연
- **극복 방안**: URL을 `https://export.arxiv.org/api/query`로 고정 (이미 `run_edu_deep_research.py` 수정)
- **대안**: `https://rss.arxiv.org/rss/cs.CY` RSS가 평일에 실시간 논문 제공 (주말=0건 정상)

### 3-E. Product Hunt API 미설정

- **원인**: `PRODUCT_HUNT_TOKEN` 미등록
- **극복 방안**: https://api.producthunt.com 에서 OAuth 토큰 발급

### 3-F. Google Play — Khan Academy, EBS 리뷰 0건

- **원인**: `google-play-scraper`가 한국 App ID로 ko/kr 조합에서 일부 앱 인식 불가
- **극복 방안**: 
  - App ID 재확인 (EBS는 `kr.co.ebs.portalapp` 등 여러 앱 분산)
  - `lang='en', country='kr'`로 재시도

---

## 4. RSS 작동 소스 목록 (14개)

✅ EdSurge, MIT Tech Review, TechCrunch Education, AI타임스, Coursera Blog,  
✅ Khan Academy Blog, VentureBeat AI, Ethan Mollick(OneUsefulThing), 한겨레,  
✅ eLearning Industry, The 74 Million, Chalkbeat, Import AI, Rest of World

---

## 5. 다음 수집 확장 우선순위

| 우선순위 | 작업 | 필요 조건 |
|---|---|---|
| HIGH | Semantic Scholar 키 추가 + 쿼리 실행 | `.env` 키 추가 |
| HIGH | Reddit 키 발급 + 5개 서브레딧 수집 | reddit.com 앱 등록 |
| HIGH | arXiv API 실제 실행 (평일 시도) | 없음 (스크립트 준비됨) |
| MEDIUM | 연합뉴스 Open API 신청 | API 키 신청 |
| MEDIUM | NewsAPI.org 등록 → 한국 미디어 RSS 대체 | API 키 신청 (무료) |
| LOW | YouTube yt-dlp 수집 (Mac Mini) | Mac Mini SSH |
| FUTURE | X API (유료 $100/월) | CEO 비용 승인 필요 |

---

## 6. AR-026 완료 기준 체크

- [x] `edu_consulting.json` 레지스트리 전면 보완 (73개)
- [x] DATA_GATHERING_UNIVERSE.md 기준 소스 전수 반영
- [x] 실제 수집 실행 및 결과 확인 (164건)
- [x] 실패 소스 원인 분석 + 극복 방안 문서화
- [ ] Semantic Scholar API 키 연결 + 수집
- [ ] Reddit API 키 연결 + 수집
- [ ] arXiv 평일 실제 수집 확인
- [ ] YouTube yt-dlp 수집 실행

> **현재 상태**: `in_progress` — 핵심 소스(Semantic Scholar, Reddit) 키 설정 후 완료 가능
