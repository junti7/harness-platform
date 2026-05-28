# 교육 컨설팅 — 데이터 수집 운영 · DEEP RESEARCH 계획 · 파이프라인 아키텍처

> 통합: DATA_GATHERING_UNIVERSE.md + DEEP_RESEARCH_PLAN.md + EDU_RESEARCH_UNIVERSE.md + EDU_PIPELINE_ARCHITECTURE.md
> correlation_id: edu-consulting-20260524 | 최종 갱신: 2026-05-25

---

<!-- 출처: DATA_GATHERING_UNIVERSE.md -->
## 전세계 데이터 수집 채널 전수 목록
## "지구상에 존재하는 모든 채널"

> 작성: 2026-05-25 | correlation_id: edu-consulting-20260524
> 목적: AI 교육 컨설팅 DEEP RESEARCH를 위한 전방위 데이터 소스 전수 리스트
> 수집 대상: **[1순위] 부모(엄마) 본인의 AX 불안·이해 니즈** · AI 교육 불안·의존·직장인 AI 압박·학부모 고민·교육 트렌드
> CEO 방향 (2026-05-25): 교육 1차 대상 = 부모 본인. 자녀 교육은 부모 AX 이해 완료 후 2단계.
> Legal 상태: ⚠️ 채널별 상이. 수집 전 AR-027 Legal 스캔 기준 재확인 필수.

---

## 범례

| 기호 | 의미 |
|---|---|
| ✅ | 즉시 수집 가능 (RSS·공개 API·허용 ToS) |
| ⚠️ | 조건부 가능 (로그인 필요·rate limit·ToS 확인 필요) |
| 🔴 | 고위험 (크롤링 금지 명시·법적 리스크·차단 가능성) |
| 🔬 | 학술 전용 (arXiv·논문 API 등) |
| 📰 | 뉴스·미디어 |
| 💬 | 커뮤니티·SNS |
| 📊 | 정부·기관·보고서 |
| 🎬 | 영상·음성 |
| 💼 | 직장인·채용·커리어 |

---

## TIER 1: 즉시 수집 가능 (✅ 법적 리스크 낮음)

### 1-A. 학술 논문 데이터베이스

| 소스 | URL | 수집 방법 | 한국어 커버 | 비고 |
|---|---|---|---|---|
| ✅🔬 arXiv | arxiv.org | API (무료) | 제한적 | 이미 69개 수집 완료 |
| ✅🔬 Semantic Scholar | api.semanticscholar.org | API (무료 500req/일) | 양호 | API Key 등록 완료 |
| ✅🔬 ERIC | eric.ed.gov | API (무료) | 영어 중심 | 미국 교육 연구 특화 |
| ✅🔬 PubMed / PubMed Central | pubmed.ncbi.nlm.nih.gov | API (무료) | 제한적 | 교육 심리학 포함 |
| ✅🔬 SSRN | ssrn.com | 공개 페이지 | 제한적 | 사회과학 preprint |
| ✅🔬 Google Scholar | scholar.google.com | 🔴 크롤링 금지 | — | API 없음, scraping 위험 |
| ✅🔬 ResearchGate | researchgate.net | ⚠️ 회원 전용 일부 | 제한적 | 로그인 필요 |
| ✅🔬 RISS (한국교육학술정보원) | riss.kr | API 신청 가능 | ✅ 한국 | 국내 석박사 논문 |
| ✅🔬 KISS (한국학술정보) | kiss.kstudy.com | ⚠️ 구독 필요 | ✅ 한국 | 유료 |
| ✅🔬 DBpia | dbpia.co.kr | ⚠️ 구독 필요 | ✅ 한국 | 유료 |
| ✅🔬 NDSL (국가과학기술정보센터) | ndsl.kr | ✅ API 제공 | ✅ 한국 | 무료 API |
| ✅🔬 OpenAlex | openalex.org | API (무료) | 글로벌 | arXiv 대체 권장 |
| ✅🔬 BASE (Bielefeld Academic) | base-search.net | API 제공 | 글로벌 | 오픈액세스 특화 |

---

### 1-B. 정부·기관 보고서 (RSS·공개 다운로드)

| 소스 | URL | 수집 방법 | 비고 |
|---|---|---|---|
| ✅📊 교육부 | moe.go.kr | 보도자료 RSS / 페이지 스크래핑 | 사교육비조사·AI교육 정책 |
| ✅📊 한국교육개발원 (KEDI) | kedi.re.kr | 보고서 PDF 다운로드 | 교육 통계·정책 분석 |
| ✅📊 한국직업능력연구원 (KRIVET) | krivet.re.kr | 보고서 RSS | 직업·교육 연구 |
| ✅📊 한국지능정보사회진흥원 (NIA) | nia.or.kr | 보고서 RSS | 디지털 정보격차·AI |
| ✅📊 한국개발연구원 (KDI) | kdi.re.kr | 보고서 RSS·API | 교육 경제학 |
| ✅📊 통계청 | kostat.go.kr | KOSIS API (무료) | 교육·인구 통계 |
| ✅📊 KERIS | keris.or.kr | 보고서 다운로드 | AI 교육 기술 연구 |
| ✅📊 OECD iLibrary | oecd-ilibrary.org | ⚠️ 일부 무료 | PISA·교육 At a Glance |
| ✅📊 UNESCO Institute for Statistics | uis.unesco.org | API (무료) | 글로벌 교육 지표 |
| ✅📊 World Bank Open Data | data.worldbank.org | API (무료) | 교육 개발 데이터 |
| ✅📊 Brookings Institution | brookings.edu | RSS | AI·교육 정책 보고서 |
| ✅📊 RAND Corporation | rand.org | RSS | 교육 연구 |
| ✅📊 Urban Institute Education | urban.org | RSS | 미국 교육 정책 |
| ✅📊 Becker Friedman Institute | bfi.uchicago.edu | Working Papers RSS | 경제·교육 연구. **[RED TEAM NOTE: BFI WP 2025-144은 허위 인용 삭제됨. 채널 자체는 유효한 소스이므로 유지]** |
| ✅📊 McKinsey Global Institute | mckinsey.com | RSS·보고서 | AI 노동 시장 영향 |
| ✅📊 PwC Research | pwc.com | 보고서 PDF | Global Workforce Survey |
| ✅📊 Mercer | mercer.com | 보고서 PDF | Global Talent Trends |
| ✅📊 Deloitte Insights | deloitte.com | RSS | 교육·노동 시장 |
| ✅📊 World Economic Forum | weforum.org | RSS·API | 미래 직업 보고서 |
| ✅📊 IMF | imf.org | RSS·데이터 포털 | AI 경제 영향 |
| ✅📊 ADP Research | adpri.org | 보고서 PDF | People at Work |

---

### 1-C. 뉴스 및 미디어 RSS

#### 한국 교육·경제 뉴스

| 소스 | RSS URL 예시 | 카테고리 |
|---|---|---|
| ✅📰 조선일보 교육 | chosun.com/rss | 교육 |
| ✅📰 동아일보 교육 | donga.com/rss | 교육 |
| ✅📰 중앙일보 교육 | joins.com/rss | 교육 |
| ✅📰 한겨레 교육 | hani.co.kr/rss | 교육 |
| ✅📰 경향신문 교육 | khan.co.kr/rss | 교육 |
| ✅📰 매일경제 | mk.co.kr/rss | 경제·AI |
| ✅📰 한국경제 | hankyung.com/rss | 경제·교육 |
| ✅📰 에듀동아 | edu.donga.com | 교육 전문 |
| ✅📰 에듀프레스 | edupress.kr | 교육 전문 |
| ✅📰 베이비뉴스 | ibabynews.com | 육아·교육 |
| ✅📰 뉴시스 교육 | newsis.com/rss | 교육 |
| ✅📰 연합뉴스 교육 | yna.co.kr/rss | 교육 |
| ✅📰 AI타임스 | aitimes.com | AI 전문 |
| ✅📰 ZDNet Korea | zdnet.co.kr | IT·AI |
| ✅📰 ITWorld Korea | itworld.co.kr | IT·AI |

#### 글로벌 교육·AI 미디어

| 소스 | RSS/피드 | 카테고리 |
|---|---|---|
| ✅📰 EdSurge | edsurge.com/rss | EdTech 전문 |
| ✅📰 Education Week (EdWeek) | edweek.org/rss | K-12 교육 |
| ✅📰 The 74 Million | the74million.org | 미국 교육 |
| ✅📰 Chalkbeat | chalkbeat.org | 교육 뉴스 |
| ✅📰 Times Higher Education | timeshighereducation.com | 고등교육 |
| ✅📰 Inside Higher Ed | insidehighered.com | 고등교육 |
| ✅📰 EdTech Digest | edtechdigest.com/rss | EdTech |
| ✅📰 eLearning Industry | elearningindustry.com | eLearning |
| ✅📰 TechCrunch Education | techcrunch.com/tag/education | Tech·교육 |
| ✅📰 Wired Education | wired.com/tag/education | AI·교육 |
| ✅📰 MIT Technology Review | technologyreview.com | AI·교육 |
| ✅📰 The Verge AI | theverge.com/ai | AI 전반 |
| ✅📰 VentureBeat AI | venturebeat.com | AI 비즈니스 |
| ✅📰 Rest of World | restofworld.org | 비서구 AI·기술 |
| ✅📰 Korea Times Education | koreatimes.co.kr | 영문 한국 교육 |
| ✅📰 Korea Herald | koreaherald.com | 영문 한국 |

---

### 1-D. 유튜브 채널 (yt-dlp 수집)

#### 한국어 채널

| 채널 | 내용 | 수집 우선순위 |
|---|---|---|
| ✅🎬 이투스 교육 | 입시·AI 교육 | HIGH |
| ✅🎬 메가스터디 공식 | 입시·AI 트렌드 | HIGH |
| ✅🎬 EBS 공식 | 교육 정책·AI | HIGH |
| ✅🎬 생각하는 황소 | 교육 철학·AI | MEDIUM |
| ✅🎬 너도나도 AI | AI 활용 교육 | HIGH |
| ✅🎬 코딩애플 | AI·코딩 교육 | MEDIUM |
| ✅🎬 생활코딩 | AI 입문 | MEDIUM |
| ✅🎬 혼공TV | 자기주도학습 | MEDIUM |
| ✅🎬 교육부TV | 교육 정책 공식 | HIGH |
| ✅🎬 인공지능 신문 | AI 뉴스 | HIGH |
| ✅🎬 이슈있슈 | AI 사회 이슈 | MEDIUM |
| ✅🎬 하우투AI | AI 실무 | MEDIUM |
| ✅🎬 맘스쿨 | 학부모 교육 | HIGH |
| ✅🎬 여러가지lab | AI 리터러시 | HIGH |
| ✅🎬 삼프로TV | 경제·직장 AI | MEDIUM |

#### 수집 방법: 영상 댓글 + 자막 + 설명란

```bash
# 영상 자막 추출 (yt-dlp)
yt-dlp --write-auto-sub --sub-lang ko --skip-download <channel_url>

# 댓글 추출
yt-dlp --write-comments <video_url>
```

#### 글로벌 채널

| 채널 | 내용 | 수집 우선순위 |
|---|---|---|
| ✅🎬 Khan Academy | AI·교육 연구 | HIGH |
| ✅🎬 Edutopia | K-12 교육 트렌드 | HIGH |
| ✅🎬 TED Education | 교육 혁신 | MEDIUM |
| ✅🎬 Common Sense Education | 디지털 리터러시 | HIGH |
| ✅🎬 AI Explained | AI 연구 해설 | MEDIUM |
| ✅🎬 Two Minute Papers | AI 논문 리뷰 | LOW |
| ✅🎬 Harvard Extension School | 고등교육·AI | MEDIUM |
| ✅🎬 World Economic Forum | 미래 교육 | MEDIUM |

---

## TIER 2: 조건부 수집 (⚠️ 기술·법률 조건 필요)

### 2-A. 한국 포털 커뮤니티

| 소스 | 수집 방법 | 관련 세그먼트 | Legal 리스크 |
|---|---|---|---|
| ⚠️💬 네이버 카페 — 맘스홀릭베이비 | Playwright 크롤링 | 학부모 | ⚠️ ToS 확인 필요 |
| ⚠️💬 네이버 카페 — 임신출산육아대백과 | Playwright 크롤링 | 학부모 | ⚠️ ToS 확인 필요 |
| ⚠️💬 네이버 카페 — 아이를사랑하는모임(아사모) | Playwright 크롤링 | 학부모 | ⚠️ ToS 확인 필요 |
| ⚠️💬 네이버 카페 — 교육/입시 관련 카페들 | Playwright 크롤링 | 학부모·학생 | ⚠️ 네이버 ToS 제한 |
| ⚠️💬 네이버 블로그 | Naver Search API | 전 세그먼트 | ✅ API 허용 |
| ⚠️💬 네이버 지식iN | Naver Search API | 전 세그먼트 | ✅ API 허용 |
| ⚠️💬 카카오 다음 카페 | Playwright | 학부모·직장인 | ⚠️ ToS 확인 |
| ⚠️💬 82cook.com | Playwright | 여성·학부모 | ⚠️ 크롤링 정책 불명확 |
| ⚠️💬 클리앙 | Playwright | Tech 직장인 | ⚠️ robots.txt 확인 |
| ⚠️💬 루리웹 | Playwright | 직장인·청년 | ⚠️ |
| ⚠️💬 디시인사이드 (AI 갤러리 등) | Playwright | 청년 | 🔴 공격적 크롤링 차단 |
| ⚠️💬 인스티즈 | Playwright | 여성·학부모 | ⚠️ |
| ⚠️💬 더쿠 (theqoo) | Playwright | 여성 | ⚠️ |
| ⚠️💬 오늘의유머 | Playwright | 직장인 일반 | ⚠️ |
| ⚠️💬 보배드림 | Playwright | 직장인 일반 | ⚠️ |
| ⚠️💬 인프런 커뮤니티 | Playwright | 직장인 개발자 | ⚠️ |
| ⚠️💬 패스트캠퍼스 커뮤니티 | Playwright | 직장인 | ⚠️ |

---

### 2-B. 소셜 미디어

#### X (Twitter)

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️🐦 X API v2 | 유료 ($100/월 Basic) | 키워드 검색, 타임라인 수집 |
| 🔴 Nitter 미러 | API 없음 | 법적·기술적 불안정 |
| 검색 키워드 | AI 교육, AI 의존, 사교육비, 직장인 AI, ChatGPT 자녀 등 | — |

**주요 계정 모니터링:**
- 교육부 공식 (@MOE_Korea)
- AI 교육 연구자 계정들
- 한국 에듀테크 스타트업 계정들
- 교육 기자 계정들

#### Instagram

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️📸 Instagram Graph API | 비즈니스 계정 필요 | 공개 게시물만 |
| ⚠️ 해시태그 모니터링 | #AI교육 #사교육 #자녀교육 #직장인AI | API 제한 엄격 |
| 🔴 비공식 scraping | Instagram 금지 | 법적 리스크 높음 |

**모니터링 해시태그:**
```
#AI교육 #AI의존 #자녀AI #사교육 #입시 #ChatGPT자녀
#직장인AI #AI불안 #교육불안 #학부모고민 #ai리터러시
#AIlearning #AiEducation #ArtificialIntelligence #ParentingAI
#EdTech #AIinEducation #21stCenturySkills
```

#### Threads

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️ Threads API | Meta 비즈니스 API (2024 공개) | 제한적, 베타 |
| 🔴 크롤링 | Meta ToS 위반 | 금지 |

#### Facebook

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️📘 Graph API | 페이지 공개 게시물 가능 | 그룹은 제한적 |
| ⚠️ 공개 그룹 모니터링 | AI Education, Korean Parenting 등 | 수동 모니터링 |

**관련 Facebook 그룹:**
- AI Education (영어권)
- Korean Parents Network (해외 한인 학부모)
- 해외 한인 교육 그룹들

#### TikTok

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️🎵 TikTok Research API | 학술 연구용 신청 가능 | 승인 필요 |
| 🔴 크롤링 | TikTok ToS 위반 | |
| **모니터링 키워드** | #AI교육 #ChatGPT #AI공부 #사교육 #자녀교육 | 수동 모니터링 가능 |

#### LinkedIn

| 방법 | 접근 | 비고 |
|---|---|---|
| ⚠️💼 LinkedIn API | 제한적 (기업 페이지 공개 게시물) | 인증 필요 |
| ✅ 공개 게시물 키워드 | AI in Education, 직장인 AI 역량, Korean AI 등 | 수동+RSS |
| **모니터링 대상** | AI 교육 컨설턴트, EdTech 임원, 한국 HR 담당자 | |

#### Reddit

| 서브레딧 | 관련성 | 수집 방법 |
|---|---|---|
| ✅ r/Korea | 한국 AI·교육 이슈 | Pushshift API or Reddit API |
| ✅ r/ChatGPT | AI 사용 패턴 | Reddit API |
| ✅ r/Parenting | 자녀 AI 고민 | Reddit API |
| ✅ r/AIAssistants | AI 의존 논의 | Reddit API |
| ✅ r/Teachers | 교사 AI 관련 | Reddit API |
| ✅ r/EdTech | 교육 기술 | Reddit API |
| ✅ r/ArtificialIntelligence | AI 일반 | Reddit API |
| ✅ r/MachineLearning | 기술적, 낮은 우선순위 | Reddit API |
| ✅ r/learnprogramming | 학습자 AI 의존 | Reddit API |
| ✅ r/asianparents | 아시아 학부모 교육 | Reddit API |
| ✅ r/KoreanParents | 한국 학부모 (소규모) | Reddit API |
| ✅ r/labor | 직장 AI 불안 | Reddit API |
| ✅ r/jobs | 취업·AI 대체 | Reddit API |
| **수집 방법** | Reddit API v2 (무료 100req/분) | |

---

### 2-C. 직장인 커뮤니티

| 소스 | 내용 | 수집 방법 |
|---|---|---|
| ⚠️💼 Blind (블라인드) | 직장인 익명 AI·업무 고민 | 🔴 공식 API 없음. 크롤링=ToS 위반. 수동 관찰 필요 |
| ⚠️💼 잡코리아 | 직업·AI 관련 컨텐츠 | ⚠️ robots.txt 확인 |
| ⚠️💼 사람인 | 커리어·AI 기사 | RSS 일부 존재 |
| ⚠️💼 캐치 | Z세대 취업 AI | ⚠️ |
| ✅💼 LinkedIn Learning 블로그 | 직장인 AI 학습 | RSS |
| ✅💼 Coursera Blog | AI 교육 트렌드 | RSS |

---

### 2-D. Discord 서버

| 서버 | 관련성 | 접근 방법 |
|---|---|---|
| ⚠️ AI Education Discord 서버들 | AI 교육 커뮤니티 | 수동 참여·관찰 |
| ⚠️ 한국 AI 커뮤니티 Discord | 직장인·개발자 | 수동 참여 |
| ⚠️ ChatGPT 관련 Discord 서버 | AI 사용자 | 수동 참여 |
| 🔴 자동 수집 | Discord ToS 금지 | 봇 무단 사용 금지 |
| **수집 방법** | 공개 서버 수동 참여 → 인사이트 메모화 | |

---

### 2-E. 오픈 채팅·커뮤니티 (한국)

| 소스 | 내용 | 수집 방법 |
|---|---|---|
| 🔴 카카오톡 오픈채팅 | 학부모·직장인 실시간 고민 | 프라이버시 이슈. 자동 수집 불가. 수동 참여+관찰만 |
| ⚠️ 네이버 밴드 | 학부모 모임 | 비공개 그룹 접근 제한 |
| ⚠️ 네이버 카페 공개 게시글 | 학부모 AI 고민 | Naver API 활용 가능 |

---

## TIER 3: 특화 수집 채널

### 3-A. 팟캐스트 (텍스트 변환 후 분석)

| 소스 | 내용 | 수집 방법 |
|---|---|---|
| ✅🎙 팟빵 (한국 최대 팟캐스트) | 교육·AI·직장인 팟캐스트 | RSS 수집 + Whisper STT |
| ✅🎙 Spotify Podcasts | 한국어 교육 팟캐스트 | Spotify API |
| ✅🎙 Apple Podcasts | 글로벌 AI Education 팟캐스트 | RSS |
| ✅🎙 The EdSurge Podcast | EdTech 트렌드 | RSS |
| ✅🎙 Curious Minds in AI | AI 교육 | RSS |
| ✅🎙 Future of Education | 교육 미래학 | RSS |

---

### 3-B. 교육 플랫폼 공개 데이터

| 소스 | 수집 가능 데이터 | 방법 |
|---|---|---|
| ✅ Khan Academy Blog | AI 교육 정책 | RSS |
| ✅ Coursera Blog | AI 직업 트렌드 | RSS |
| ✅ edX Blog | AI 고등교육 | RSS |
| ✅ Duolingo Research | 학습 데이터 연구 | 공개 보고서 |
| ✅ Google for Education | AI 교육 도구 | RSS·블로그 |
| ✅ Microsoft Education | AI in Education | RSS·블로그 |
| ✅ AWS Educate | 클라우드 교육 | 블로그 |
| ⚠️ 메가스터디 공개 컨텐츠 | 국내 입시 트렌드 | robots.txt 확인 필요 |
| ⚠️ 대성마이맥 | 입시 컨텐츠 | robots.txt 확인 |
| ✅ EBS 공식 블로그 | 공교육 AI 정책 | RSS |
| ✅ 천재교육 블로그 | 교과서 AI | RSS |

---

### 3-C. AI 회사 공식 채널 (교육 관련 포스팅)

| 소스 | 관련 컨텐츠 | 수집 방법 |
|---|---|---|
| ✅ Anthropic Blog | Claude AI 교육 활용 | RSS |
| ✅ OpenAI Blog | GPT 교육 정책 | RSS |
| ✅ Google DeepMind | AI 연구·교육 | RSS |
| ✅ Microsoft AI Blog | Copilot 교육 | RSS |
| ✅ Meta AI Blog | AI 접근성·교육 | RSS |
| ✅ Samsung AI (뉴스룸) | Gauss·Enterprise AI | RSS |
| ✅ LG AI Research | 한국 AI | RSS |
| ✅ KT AI | 한국 AI·교육 | RSS |

---

### 3-D. 학교·학원·교사 커뮤니티

| 소스 | 내용 | 수집 방법 |
|---|---|---|
| ✅ ISTE (국제교육기술학회) | 교사 AI 활용 | RSS·컨퍼런스 자료 |
| ✅ Teachers Pay Teachers | 교사 AI 자료 | 공개 카탈로그 |
| ✅ Edutopia | 교사 AI 실전 | RSS |
| ✅ 인디스쿨 (한국 교사 커뮤니티) | 국내 교사 AI 적용 | ⚠️ robots.txt 확인 |
| ✅ 교육나눔 카페 | 교사 수업 자료 | ⚠️ 네이버 카페 정책 |
| ✅ 전국교직원노동조합 (전교조) 성명 | 교육 정책 입장 | 공개 보도자료 |
| ✅ 한국교원단체총연합회 | 교육 정책 | 보도자료 |

---

### 3-E. 앱스토어 리뷰 (AI 교육 앱)

| 소스 | 수집 대상 | 방법 |
|---|---|---|
| ✅ Google Play 리뷰 | AI 과외·학습 앱 리뷰 | Google Play API |
| ✅ Apple App Store 리뷰 | AI 교육 앱 리뷰 | iTunes Search API |
| 대상 앱 예시 | Khan Academy, Duolingo, EBS, 콴다, 매쓰플랫, 아이스크림 등 | |
| **가치** | 실제 사용자(학생·학부모) 불만·기대 직접 청취 | HIGH |

---

### 3-F. 컨퍼런스·이벤트 자료

| 이벤트 | 내용 | 자료 수집 |
|---|---|---|
| ✅ SXSW EDU | AI 교육 혁신 | 유튜브 + 공개 발표자료 |
| ✅ ISTE Conference | 교사 AI 적용 | 유튜브 + 공개 자료 |
| ✅ ASU+GSV Summit | EdTech 투자·트렌드 | 유튜브 |
| ✅ EdTech Korea | 한국 에듀테크 | 유튜브 |
| ✅ KES (한국전자전) AI 교육 세션 | 국내 AI 교육 | 유튜브 |
| ✅ 교육부 주최 AI 교육 포럼 | 정책 방향 | 유튜브·보도자료 |

---

### 3-G. Substack·뉴스레터

| 소스 | 내용 | 수집 |
|---|---|---|
| ✅ The Rundown AI | AI 뉴스 daily | 이메일 구독·RSS |
| ✅ The Neuron | AI 교육·비즈니스 | RSS |
| ✅ AI in Education Substack | 교육 AI 연구자들 | RSS |
| ✅ Ethan Mollick (Wharton) One Useful Thing | AI 교육 실험 | Substack RSS |
| ✅ Stratechery | AI 전략 | RSS (일부 유료) |
| ✅ Import AI (Jack Clark) | AI 연구 주간 | RSS |
| ✅ 한국 AI 뉴스레터들 | 국내 동향 | 이메일 구독 |

---

### 3-H. Product Hunt·GitHub

| 소스 | 내용 | 수집 |
|---|---|---|
| ✅ Product Hunt — AI Education | 신규 AI 교육 도구 | API (무료) |
| ✅ GitHub Topics: ai-education | AI 교육 오픈소스 | GitHub API |
| ✅ GitHub Discussions | 개발자 AI 교육 논의 | GitHub API |
| ✅ Hacker News | Show HN: AI 교육 도구 | Algolia API (무료) |

---

## TIER 4: 전문 데이터 구매·파트너십 (Phase 2+)

| 소스 | 내용 | 비용 |
|---|---|---|
| 💰 한국갤럽 | 교육·AI 인식 조사 | 구매 또는 보고서 |
| 💰 엠브레인 | 소비자 패널 조사 | 맞춤 조사 의뢰 |
| 💰 Kantar | 글로벌 AI 소비자 인식 | 보고서 구매 |
| 💰 나우앤서베이 최신판 | 한국 직장인 AI 현황 | 구매 |
| 💰 Gartner Education | EdTech 시장 분석 | 보고서 구매 |
| 💰 HolonIQ | 글로벌 EdTech 시장 | 보고서 구매 |

---

## 수집 우선순위 매트릭스

```
높은 가치 + 낮은 리스크 (즉시 착수):
  arXiv, Semantic Scholar, OpenAlex, ERIC
  교육부·KEDI·KRIVET·NIA·KDI 공식 보고서
  RSS 뉴스 (에듀동아·에듀프레스·THE·EdSurge·Edweek)
  Reddit (r/Parenting, r/ChatGPT, r/Korea)
  YouTube (yt-dlp 자막+댓글)
  앱스토어 리뷰
  Hacker News, Product Hunt
  각종 Substack·뉴스레터

높은 가치 + 중간 리스크 (Legal 검토 후):
  네이버 블로그·지식iN (Naver API)
  X/Twitter (API 비용 투자 후)
  LinkedIn 공개 게시물
  인프런·패스트캠퍼스 커뮤니티

높은 가치 + 높은 리스크 (신중 접근):
  네이버 카페 (맘카페 등) → 수동 관찰·서비스 계정 운영 검토
  Blind → 수동 모니터링만
  카카오 오픈채팅 → 직접 참여·관찰 (자동 수집 금지)
  Instagram → API로 공개 해시태그만
```

---

## 수집 기술 스택 요약

| 기술 | 용도 | 현재 상태 |
|---|---|---|
| arXiv API | 논문 수집 | ✅ 운영 중 |
| Semantic Scholar API | 논문 수집 | ✅ API Key 등록 완료 |
| yt-dlp | YouTube 수집 | MBP ✅ / Mac Mini ⚠️ 미설치 |
| Whisper | STT 변환 | ⚠️ 미설치 |
| Playwright | 동적 페이지 크롤링 | ⚠️ Legal 검토 후 채널별 판단 |
| feedparser (RSS) | RSS 수집 | ⚠️ 설치 필요 |
| Reddit API (PRAW) | Reddit 수집 | ⚠️ API Key 필요 |
| Naver Search API | 네이버 블로그·지식iN | ⚠️ API Key 필요 |
| Google Play API | 앱 리뷰 수집 | ⚠️ |
| Algolia API | HN 수집 | ✅ 무료 |

---

## 다음 실행 단계 (AR-033 red_team_clear 이후)

1. **Phase 1 즉시 확장 (이번 주):**
   - RSS feedparser 설치 → 20개 뉴스 소스 등록
   - Reddit API 키 발급 → PRAW로 5개 서브레딧 수집
   - Hacker News Algolia API 연동
   - 앱스토어 리뷰 수집 스크립트 (콴다·Khan Academy 등)

2. **Phase 1.5 (2주 차):**
   - yt-dlp Mac Mini 설치 → YouTube 댓글·자막 수집
   - Naver Search API 키 발급 → 블로그·지식iN 수집
   - Semantic Scholar 쿼리 확장 (현재 0건 문제 해결)

3. **Phase 2 (한 달 후, Legal 확인 후):**
   - X API ($100/월) 구독 결정
   - 네이버 카페 접근 방식 결정 (API vs 서비스 계정)
   - Instagram Graph API 연동

---

*생성: 2026-05-25 | Jarvis | AR-035 | correlation_id: edu-consulting-20260524*
*Legal 주의: 각 채널별 ToS·robots.txt·저작권 정책은 AR-027 Legal 스캔 기준으로 판단. 이 문서는 채널 목록이며 수집 허가가 아님.*


---

<!-- 출처: DEEP_RESEARCH_PLAN.md -->
## AI 교육 컨설팅 — DEEP RESEARCH 방안 (전 세계 전수 조사 설계 v0.1)

> 작성일: 2026-05-24 | 발의: 대표(President/CEO) | 설계: 비서실장(Chief of Staff)
> correlation_id: edu-consulting-20260524
> 상태: **방안(METHOD) 설계 — CEO 승인 후 수집 착수. 본 문서는 "무엇을, 어떻게, 어디까지, 얼마에" 훑을지의 청사진**
> 연계: `EDU_CONSULTING_MASTER_PLAN.md`(§5 정보격차), `EDU_MARKET_RESEARCH.md`(데스크 1차)
> 기존 인프라: `adapters/content/collector.py`(RSS+스크래핑+dedup), `configs/sources/*.json`(소스 레지스트리), `yt-dlp`(설치됨)

---

## 0. 설계 철학 — "빠짐없이"를 어떻게 보장하는가

전 세계 모든 글을 물리적으로 다 읽는 것은 불가능합니다. 대신 **누락을 구조적으로 막는 4가지 장치**로 "전수에 수렴(converge to exhaustive)"합니다.

1. **택소노미 커버리지(Taxonomy Coverage):** 주제·채널·언어·지역을 격자(grid)로 정의하고, 모든 칸을 최소 1회 이상 훑는다. 빈 칸 = 누락 → 추적·경보.
2. **스노우볼(Snowball / 인용 추적):** 핵심 논문·영상·기사에서 인용·참조·연관 채널을 따라가 가지치기. seed → 2-hop 확장.
3. **포화 판정(Saturation):** 새 수집분의 **신규 신호 비율(novelty rate)이 < 5%로 3회 연속** 떨어지면 해당 하위주제는 "포화=충분히 훑음"으로 판정. (정성연구의 theoretical saturation 차용)
4. **중복 제거(Dedup) + 랭킹:** `content_hash` 중복 차단 + Tier 2 로컬 모델 분류/스코어링으로 대량 수집을 사람이 볼 수 있는 양으로 압축.

> 핵심: **수집은 광범위하게(recall 최대화) → 필터는 공격적으로(precision 확보).** "다 모으되, 다 안 읽는다. 모은 것 중 신호만 본다."

---

## 1. 연구 질문 분해 (수집의 나침반)

수집은 질문에 종속됩니다. MASTER_PLAN §5 격차를 답할 수 있는 데이터로 역설계.

| # | 연구 질문 | 답을 줄 데이터 채널 |
|---|---|---|
| RQ1 | 부모/학생/성인은 AI를 실제로 어떻게 쓰고, 무엇에 불안한가? | YouTube 댓글·커뮤니티·앱리뷰·설문 |
| RQ2 | "AI 의존 → 학습력 저하"는 학술적으로 어디까지 입증됐나? | 논문(arXiv/ERIC/SSRN/PubMed/KCI) |
| RQ3 | 전 세계 누가 AI 교육/리터러시를 팔고, 어떻게 돈을 버는가? | 경쟁사 사이트·앱·시장리포트·공시 |
| RQ4 | 한국 학부모의 결제의향·채널·통증은? | 맘카페·블로그·유튜브·국내 에듀테크 |
| RQ5 | 효과적인 "반의존 AI 학습법"의 근거 있는 방법론은? | 교육학 논문·우수사례·교사 커뮤니티 |
| RQ6 | 규제·법률 지형(미성년 데이터·표시광고·해외)은? | 정부·법령·규제기관 RSS |

---

## 2. 소스 택소노미 — 전 세계 격자 (채널 × 언어 × 지역)

> 각 칸은 `configs/sources/edu_consulting.json` 레지스트리에 등록되어 추적된다. (§6 커버리지 매트릭스)

### 2.1 학술 논문 (RQ2, RQ5) — 최고 신뢰
| 소스 | 접근 | 키워드 |
|---|---|---|
| arXiv (cs.CY 컴퓨터와 사회, cs.HC HCI, cs.AI) | RSS(기존 패턴) | AI literacy, cognitive offloading, LLM education |
| ERIC (미국 교육자료 DB) | RSS/API | AI in K-12, generative AI learning |
| SSRN / Semantic Scholar API | API(무료 키) | AI dependence learning outcomes |
| PubMed | E-utilities API | cognitive offloading, metacognition, brain |
| KCI / RISS / DBpia (한국 학술) | 웹/playwright | 생성형 AI 학습, 디지털 리터러시, 자기주도학습 |
| OECD / UNESCO AI in Education | WebFetch + PDF | policy, framework |

### 2.2 YouTube (RQ1, RQ3, RQ4, RQ5) — yt-dlp 전수 크롤
| 대상 | 추출물 |
|---|---|
| 국내외 AI 교육 강연·컨퍼런스(ISTE, SXSW EDU, 테드) | 자막(자동/수동) + 메타데이터 |
| 학부모 대상 교육 유튜버(국내 맘튜버·교육 채널) | 자막 + **댓글(여론·통증)** |
| 사교육·입시·코딩교육 채널 | 자막 + 조회/좋아요(수요 강도) |
| 경쟁사 공식 채널(엘리스/코드잇/패캠/Khan 등) | 마케팅 메시지·커리큘럼 단서 |
| AI 의존/디지털 디톡스 관련 영상 | 반대 담론·우려 여론 |

### 2.3 웹·뉴스·미디어 (RQ3, RQ6)
| 소스 | 접근 |
|---|---|
| Edtech 미디어: EdSurge, EdWeek, TechCrunch EDU, 플래텀, AskEdTech, 베타뉴스 | RSS |
| 경쟁사 사이트(가격·커리큘럼·후기): 엘리스/코드잇/패캠/클래스101/인프런/MissyShop류/Khanmigo/AI Literacy Academy | playwright + httpx |
| 정부/기관: 교육부, 과기정통부, KERIS, 한국교육개발원, 통계청 | RSS/웹 |
| 글로벌 정책: OECD, UNESCO, EU AI Act 교육 조항, US Dept of Ed | WebFetch |

### 2.4 커뮤니티·여론 (RQ1, RQ4) — ⚠️ 법률 게이트(§8) 선통과 필수
| 소스 | 가치 | 주의 |
|---|---|---|
| 네이버 맘카페·블로그 | 한국 학부모 실제 통증·불안·결제 언어 | 로그인/저작권 — 공개영역·인용한도 준수 |
| Reddit (r/teachers, r/Professors, r/ChatGPT, r/Parenting) | 글로벌 교사·부모 여론 | 공개 API |
| 디시·블라인드·커뮤니티 | 솔직한 사교육 여론 | 공개영역만 |
| 앱스토어 리뷰(콴다·클로바노트·Khan·뤼이드 등) | 사용자 불만·니즈 마이닝 | 공개 리뷰 |

### 2.5 시장·산업 (RQ3)
| 소스 | 접근 |
|---|---|
| 시장조사기관 무료 요약(Mordor/Grandview/Precedence/SNS Insider) | WebFetch(요약만, 유료 본문 제외) |
| 컨설팅 무료 리포트(McKinsey/BCG/딜로이트 AI·교육) | WebFetch + PDF |
| 에듀테크 기업 공시/투자(THE VC, 크런치베이스, 전자공시) | 웹 |
| 특허(교육 AI): KIPRIS, Google Patents | API/웹 |

### 2.6 팟캐스트·오디오 (RQ1, RQ3)
교육·AI 팟캐스트 → yt-dlp/whisper 전사 → 텍스트화 후 동일 파이프라인.

---

## 3. 수집 도구 스택 (모든 tool 동원)

| 도구 | 역할 | 상태 | 비고 |
|---|---|---|---|
| **yt-dlp** | YouTube/팟캐스트 자막·메타·댓글 추출 | ✅ CLI 설치됨(`/opt/homebrew/bin/yt-dlp`) | py 모듈은 requirements 추가 필요 |
| **feedparser** | RSS 전 채널 | ✅ 설치됨 | 기존 collector 재사용 |
| **playwright** | JS·로그인·동적 사이트 | ✅ 설치됨 | 경쟁사·KCI 등 |
| **httpx + BeautifulSoup** | 정적 페이지 본문 스크래핑 | ✅ 기존 `deep_fetch_content()` | 재사용 |
| **WebSearch / WebFetch** | 타깃 탐색·시드 발굴·요약 | ✅ (본 에이전트) | seed 확보 |
| **Semantic Scholar / arXiv / PubMed API** | 논문 메타·인용그래프(스노우볼) | 무료 키 | 인용 추적 |
| **YouTube Data API** | 채널·영상 디스커버리(yt-dlp 보완) | 무료 쿼터 | 검색·채널 목록 |
| **Whisper(로컬)** | 자막 없는 영상/팟캐스트 전사 | 추가 설치 | 비용↓ |
| **Ollama(로컬, Tier 2)** | 대량 dedup·분류·스코어·요약 | ✅ 기존 | **비용 절감 핵심** |
| **Claude / Gemini / GPT (Tier 3)** | 심층 합성·교차검증·반론 | ✅ 기존 | Gemini=장문 PDF/영상전사, Claude=합성, GPT=중재 |

---

## 4. 파이프라인 (기존 Tier 1~4 재사용)

```
[Tier 1 수집]  edu_consulting.json 레지스트리
   ├ RSS(feedparser) ┐
   ├ yt-dlp 자막/댓글 ┤→ raw_signals 테이블 (content_hash dedup) → full_content
   ├ playwright 스크랩 ┤   (기존 collector.py save_raw_signal 재사용)
   └ API(논문/리뷰)   ┘
        │
[Tier 2 로컬 필터]  Ollama/Gemma
   ├ 중복·노이즈 제거
   ├ 주제 분류(RQ1~6 태깅)
   ├ 신호 강도 스코어(0~1)
   └ 언어·지역·채널 메타 부착   →  상위 신호만 통과 (비용 게이트)
        │
[Tier 3 멀티LLM 심층분석]
   ├ Gemini: 장문 논문/영상전사/PDF 정독·교차검토
   ├ Claude: 합성·반론·전략 함의 추출
   └ GPT: 모델 충돌 중재·스코어 보정
        │
[Tier 4 산출물]
   ├ 주제별 deep-dive 리포트(RQ1~6)
   ├ 경쟁/벤치마킹 매트릭스 업데이트
   ├ 커버리지 매트릭스(§6) 갱신
   └ MASTER_PLAN v0.x 근거 반영 + 출처 자세 표기
```

> **CLI-first 원칙(CLAUDE.md):** 모든 수집은 재실행 가능한 command + input/output path를 남긴다. 새 진입 스크립트 후보: `scripts/run_edu_deep_research.py`(collector 패턴 차용).

---

## 5. 수집 명령 예시 (실행 가능 형태)

```bash
# (1) YouTube 채널 자막+메타+댓글 (다운로드 없이)
yt-dlp --skip-download --write-auto-sub --write-sub --sub-lang "ko,en" \
       --write-comments --write-info-json -o "data/edu_research/yt/%(id)s.%(ext)s" \
       "https://www.youtube.com/@<채널>/videos"

# (2) RSS 일괄 수집 (기존 collector 재사용 — edu 레지스트리 지정)
.venv/bin/python scripts/run_edu_deep_research.py --sources configs/sources/edu_consulting.json --tier 1

# (3) 논문 인용 스노우볼 (Semantic Scholar)
.venv/bin/python scripts/run_edu_deep_research.py --snowball "AI literacy cognitive offloading" --hops 2

# (4) Tier 2 로컬 필터 + Tier 3 합성
.venv/bin/python scripts/run_edu_deep_research.py --tier 2 --filter ollama
.venv/bin/python scripts/run_edu_deep_research.py --tier 3 --synthesize claude,gemini
```

> 스크립트는 G1에서 구현(현재 미구현). 명령 인터페이스는 본 설계가 계약.

---

## 6. 커버리지 매트릭스 — 누락 추적 장치

`configs/sources/edu_consulting.json` + `data/edu_research/coverage.jsonl`로 칸별 상태 추적.

| 채널 \ 언어·지역 | 한국 | 미국/영어권 | 기타(EU/일본/중국) |
|---|---|---|---|
| 학술 논문 | ☐ | ☐ | ☐ |
| YouTube | ☐ | ☐ | ☐ |
| 웹·뉴스 | ☐ | ☐ | ☐ |
| 커뮤니티·여론 | ☐ | ☐ | ☐ |
| 시장·산업 | ☐ | ☐ | ☐ |

각 칸: `미착수 → 수집중 → 포화(novelty<5%×3회) → 검토완료`. **빈 칸·미포화 칸은 주간 리서치 브리프에 경보.**

---

## 7. 비용 게이트 (대표님 "비용 들여서" 승인 반영)

| 비용 항목 | 통제 |
|---|---|
| Tier 3 프리미엄 LLM 호출 | `DAILY_COST_LIMIT_USD` 게이트 통과 필수(CLAUDE.md §5) |
| 대량 영상 전사(Whisper) | 로컬 우선(무료), 불가 시에만 API |
| Tier 2 필터 | 로컬 Ollama로 비용 0 수렴 |
| API 유료 쿼터 | 무료 티어 우선, 초과 시 단계 승인 |

> 제안 예산: **DEEP RESEARCH 단계 한도 = (대표님 지정 금액)**. 일 단위 소진율을 BRM 리스크 레지스터에 기록, 한도 80% 도달 시 경보.

---

## 8. 법률·윤리 게이트 (⚠️ 수집 착수 전 필수)

CLAUDE.md "데이터 수집 정책 변경(scraping 범위, source 추가)"은 **`legal_review_approve` 사전 조건** 대상입니다.

| 항목 | 점검 |
|---|---|
| robots.txt / 이용약관 | 사이트별 스크래핑 허용 범위 준수 |
| 저작권 | 본문 전재 금지, **인용·요약·출처표기** 원칙 |
| 로그인 영역(맘카페 등) | 비공개 영역 크롤 금지, 공개영역만 |
| 개인정보(댓글 작성자 등) | PII 비식별화, 집계만 사용 |
| YouTube ToS | 자막·메타 연구목적 인용, 재배포 금지 |

→ **G1 진입 전 `scripts/run_legal_review.py`로 수집 정책 Legal 스캔 → `legal_review_approve` 기록.**

---

## 9. 산출물 & cadence

| 산출물 | 주기 |
|---|---|
| `data/edu_research/raw/*` (수집 원본) | 수집 시 |
| 주제별 deep-dive 리포트(RQ1~6) | 포화 도달 시 |
| 경쟁/벤치마킹 매트릭스 갱신 | 주간 |
| 커버리지 매트릭스 갱신 | 주간 |
| MASTER_PLAN/MARKET_RESEARCH 근거 반영 | 마일스톤별 |

---

## 10. 실행 단계 (Phase)

| 단계 | 내용 | 산출물 | 게이트 |
|---|---|---|---|
| **D0 (현재)** | 본 방안 설계 v0.1 | 본 문서 + `edu_consulting.json` 시드 레지스트리 | CEO 승인 |
| **D1 셋업** | `scripts/run_edu_deep_research.py` 구현, yt-dlp 모듈 추가, Legal 스캔 | 수집기 + `legal_review_approve` | **Legal 필수** |
| **D2 1차 스윕** | 학술+경쟁사+정부(저위험 채널) 전수 | RQ2·RQ3·RQ6 리포트 | 비용 게이트 |
| **D3 여론 스윕** | YouTube+커뮤니티+앱리뷰(법률 통과 후) | RQ1·RQ4 리포트 | Legal 통과 후 |
| **D4 합성** | Tier 3 멀티LLM 심층분석 + 커버리지 포화 판정 | MASTER_PLAN v0.2 근거 | Red Team |
| **D5 의사결정** | Pre-Mortem + CEO go/no-go | 최종 근거 패키지 | Pre-Mortem |

> 대표님 지시("밑작업 60~70%")의 실체 = **D2~D4**. 이 단계에 가장 큰 공을 들인다.

---

## 11. 즉시 셋업 항목 (D1 — LLM_EXECUTABLE)

- [ ] `configs/sources/edu_consulting.json` 시드 레지스트리 작성(본 PR에 동봉)
- [ ] `requirements.txt`에 `yt-dlp` 모듈 추가(프로그램 호출용)
- [ ] `scripts/run_edu_deep_research.py` 스켈레톤(collector 패턴 차용)
- [ ] 수집 정책 Legal 스캔 → `legal_review_approve`
- [ ] DEEP RESEARCH 예산 한도 대표님 확정

---

## 12. AR 등록

| AR | 내용 | 유형 | 기한 |
|---|---|---|---|
| AR-024 | DEEP RESEARCH 방안 설계 v0.1 (본 문서) | LLM_EXECUTABLE | 당일 ✅ |
| AR-026 | `edu_consulting.json` 시드 레지스트리 + 수집기 스켈레톤 | LLM_EXECUTABLE | 당일 |
| AR-027 | 수집 정책 Legal 스캔 → `legal_review_approve` | LLM_EXECUTABLE | 당일 |
| (CEO) | DEEP RESEARCH 예산 한도 + 착수 승인 | HUMAN_REQUIRED | CEO |

---

> 생성: 2026-05-24 | 비서실장 | correlation_id: edu-consulting-20260524
> "다 모으되, 다 안 읽는다. 모은 것 중 신호만 본다. 누락은 격자로 추적한다."


---

<!-- 출처: EDU_RESEARCH_UNIVERSE.md -->
## AI 교육 사업 — Research Universe & 도출 결론 (시각 확장판 v0.1)

> 작성일: 2026-05-24 | 발의: 대표(President/CEO) | 설계: 비서실장(Chief of Staff)
> correlation_id: edu-consulting-20260524
> 위상: **DEEP_RESEARCH_PLAN.md의 상위 설계.** "대표님이 말한 채널(yt_dlp·RSS·논문)은 빙산의 일각" — 탐색 가능한 **신호 우주 전체**로 범위를 재정의하고, 그로부터 **결론을 도출**한다.
> 연계: `EDU_CONSULTING_MASTER_PLAN.md`, `EDU_MARKET_RESEARCH.md`, `DEEP_RESEARCH_PLAN.md`

---

## 0. 왜 이 문서가 필요한가

v0.1 DEEP_RESEARCH_PLAN은 "어떤 사이트를 긁을까"에 머물렀습니다. 그것은 빙산의 일각입니다.
이 문서는 질문을 바꿉니다:

> **"이 사업의 진실을 결정하는 모든 신호는 우주 어디에 존재하며, 그것을 누락 없이 포착하는 좌표계는 무엇인가?"**

---

## 1. 3가지 패러다임 전환

| 낡은 사고 (v0.1) | 확장된 사고 (본 문서) |
|---|---|
| 조사 = 끝나는 프로젝트 | 조사 = **끝나지 않는 상시 인텔리전스 엔진** |
| "긁어서 다 읽는다" | "다 모으되, **다중 방법 삼각측량 + 베이지안 신념 갱신**으로 결론에 수렴" |
| 대표님이 말한 채널 목록 | **신호 우주 온톨로지(6축 × 10클래스)** — 채널은 그 안의 한 좌표 |

---

## 2. 신호 우주 좌표계 — 누락을 수학적으로 막는 6축

모든 신호는 아래 6축의 좌표 하나로 위치가 정해진다. **6축의 곱집합(Cartesian product) 격자**를 만들면, 빈 칸 = 누락. 누락이 보이게 만드는 것이 "빠짐없이"의 본질이다.

- **A. WHO (대상 우주):** 영유아 부모 / 초·중·고 학부모 / 학생 본인(연령대별) / 대학생 / 사회초년생 / 재직자 / 중장년 / 시니어 / 교사·학원장 / 정책결정자
- **B. 동기·통증:** FOMO / 의존 공포("애가 멍청해진다") / 기회 욕망("내 아이 대체불가 인재로") / 비용 공포(사교육비) / 시간 빈곤 / 평가 불안(수능·입시 변화)
- **C. 신호 서식지(habitat):** §3의 10개 클래스
- **D. 포착 방법:** 수집(scrape/API) / 청취(social listening) / 거래신호(marketplace) / 1차생성(설문·인터뷰·pretotyping) / 합성(멀티LLM 추론)
- **E. 시간성:** 1회성 스냅샷 / **상시 레이더(continuous)**
- **F. 지역·언어:** 한국 / 영어권(미·영) / EU / 일본 / 중국 — (각국 교육 불안의 형태가 다름)

> 운영 규칙: 격자의 각 칸은 `미착수 → 수집중 → 포화 → 검토완료`로 추적. 미포화 칸은 주간 경보.

---

## 3. 확장된 신호 서식지 — 10개 클래스 (대표님 예시는 클래스 1·4의 일부였다)

### Class 1 — 학술·과학 프론티어 (왜 우리가 옳은가의 뿌리)
논문에서 멈추지 않는다. **학습과학(learning science) 이론 자체**가 "반의존 학습법"의 설계도다.
- 인용 그래프(Semantic Scholar/Connected Papers) — seed 논문에서 2-hop 스노우볼
- 연구비 DB(어디에 돈이 몰리나 = 분야의 미래)
- **학습과학 정전(正典):** 인지부하 이론(Cognitive Load), 메타인지(metacognition), 의도적 연습(deliberate practice), Bloom 2-sigma, 망각곡선, desirable difficulties → "AI를 쓰되 인지부하를 의도적으로 유지하는 설계"의 학문적 근거
- 학회: CHI, AERA, Learning@Scale, NeurIPS(교육 트랙), 인지과학회

### Class 2 — 행동·검색 데이터 (사람들이 실제로 무엇을 두려워하는가)
사람들이 검색창에 치는 것 = 가장 정직한 통증 고백.
- Google Trends / **Naver DataLab**(한국 학부모 검색 추이)
- 검색 자동완성·연관검색어 마이닝("우리 아이 AI..." 뒤에 뭐가 붙나)
- **Naver 지식iN / Quora / 오늘의집·맘Q** — 실제로 던지는 질문 전수

### Class 3 — 거래·시장 신호 (말이 아니라 돈이 움직인 증거)
설문의 "낼 의향 있다"보다 강한 데이터 = 이미 결제된 흔적.
- **탈잉·크몽·숨고·클래스101·인프런·라이프해킹스쿨** — AI/교육 강의의 실제 가격·수강생수·후기(revealed WTP)
- **와디즈·텀블벅** — AI 교육 상품 크라우드펀딩 달성률(수요 검증)
- 앱스토어 — 경쟁 앱(콴다·클로바노트·뤼이드·Khan) 순위·매출추정·리뷰 통증 마이닝
- **통계청 사교육비조사** — 한국 사교육 지출의 hard $ (객단가·시장규모 앵커)
- 저출산 인구통계 — 자녀 1인당 교육지출 상승 동학

### Class 4 — 소셜 청취 (대규모 여론·감정)
- X / TikTok / Instagram / Threads / YouTube(자막+댓글, yt-dlp)
- **네이버 맘카페 / 오픈카톡 학부모방 / 디시·더쿠·인스티즈**
- Reddit(r/teachers, r/Professors, r/Parenting, r/ChatGPT) / Discord 학습·AI 서버
- (⚠️ 비공개·로그인 영역 제외, 공개영역·집계만 — §6 법률)

### Class 5 — 경쟁 인텔리전스 (경쟁사의 머릿속)
- **채용공고**(원티드·잡코리아·LinkedIn) = 경쟁사가 지금 만드는 것
- **광고 라이브러리**(Meta Ad Library·Google Ads Transparency) = 어떤 메시지에 돈을 쓰나
- 웹트래픽 추정(SimilarWeb) / SEO 키워드 갭(어떤 검색어를 그들이 점유)
- 투자·M&A(THE VC·Crunchbase·전자공시) / 특허·상표(KIPRIS·Google Patents)
- Glassdoor·블라인드(내부 신호)

### Class 6 — 정책·규제 지평 (게임의 룰을 바꾸는 힘)
- 입시·수능·내신 제도 변화, **2022 개정 교육과정·AI 디지털교과서** (부모 행동의 최대 동인)
- EU AI Act 교육조항 / 미국 주별 법 / 중국·일본 교육정책
- 교육부·과기정통부·KERIS 로드맵

### Class 7 — 1차 생성 데이터 (긁는 게 아니라 만들어내는 진실)
가장 빠르고 강한 데이터는 우리가 직접 만든다.
- 익명 학부모 **설문 패널** / **전문가 인터뷰**(교사·입시컨설턴트·교육학 교수)
- **Pretotyping(가짜문 테스트):** 랜딩페이지 + 결제버튼 → 실제 클릭·결제의향 측정 = **8주 긁기보다 빠른 진짜 수요**
- A/B 메시지 테스트(어떤 통증 카피가 전환되나)

### Class 8 — 약신호·미래 (남보다 1년 먼저 보기)
- OpenAI·Anthropic·Google의 교육 관련 발언·연구
- 미래학·SF·EdTech 비전 리포트(OECD·UNESCO·WEF)

### Class 9 — 교차도메인 유추 (역사는 반복된다)
- 과거 기술충격이 만든 교육시장사: 계산기→수학교육 논쟁, 인터넷→코딩교육, 닷컴→IT자격증, 스마트폰→앱·미디어교육. **"불안이 만든 교육시장"의 패턴 학습**
- 인접 advisory 비즈니스: 건강 코칭·재무 자문 — "불안 + 지속 자문 + 구독" 모델의 검증된 경제학

### Class 10 — 멀티모달 (텍스트 밖의 신호)
- 영상·웨비나·팟캐스트 → Whisper 전사 → 동일 파이프라인
- 강연 슬라이드·인포그래픽(이미지) → Gemini 멀티모달 판독

---

## 4. 확장된 방법론 — "긁기"를 넘어서

| 방법 | 내용 |
|---|---|
| **멀티에이전트 리서치 스웜** | Harness 에이전트 조직을 활용해 클래스/축별 **병렬 에이전트**가 각자 수집·요약 → 합성층(Claude)이 통합. 1인 순차조사가 아니라 무리(swarm) 조사 |
| **삼각측량 규칙** | 모든 핵심 결론은 **서로 다른 3개 방법(D축)으로 교차확인**될 때만 "확정". 예: "부모는 낸다" = 거래신호(Class3) + 검색추이(Class2) + 설문(Class7) 동시 충족 |
| **베이지안 신념 보드** | 각 사업가설에 사전확률 부여 → 데이터마다 갱신 → 변동 < ε이면 포화. "얼마나 더 조사할까"를 수치로 판단 |
| **Build-to-learn / Pretotyping** | 분석보다 빠른 학습 = 시장에 가짜문을 세워 진짜 반응을 산다. 조사와 병행 |
| **상시 레이더(Continuous)** | 끝나는 조사가 아니라 영구 가동 파이프라인. Tier 1이 매일 도는 것처럼, "AI 교육 시장 레이더"도 매일 돈다 |

---

## 5. 도출된 결론 (CONCLUSIONS)

> 대표님이 요청한 "결론." 시각을 넓힌 끝에 도달한 6가지.

### 결론 1 — 조사 ≡ 제품 (가장 큰 발견)
이 DEEP RESEARCH 인프라(다중소스 수집 → 멀티LLM 합성 → 상시 갱신)는 **조사 도구이자 동시에 팔 수 있는 상품의 본체**다. "AI 교육 시장을 매일 훑어 한 줄 해석·추적신호·다음행동을 주는 인텔리전스" — 이것이 곧 부모·교사·교육사업자에게 파는 구독 상품이 될 수 있다. **조사에 쓴 돈이 곧 제품 개발비**다.

### 결론 2 — 기회의 본질은 "강의"가 아니라 "불안에 대한 상시 판단 엔진"
부모는 강의 1회가 아니라 **"지금 우리 아이에게 뭐가 맞고, 3개월 뒤 뭘 점검할지"**를 계속 원한다(PILOT_PARENT 가설과 일치). 단발 콘텐츠는 무료 toolkit과 경쟁해 진다. **지속형 advisory + 상시 인텔리전스**만이 유료 해자다.

### 결론 3 — 복제 불가능한 3중 해자
**학습과학(반의존 설계, Class1) × 한국 학부모 맥락(Class2~4) × 멀티LLM 상시 인텔리전스(Harness 엔진).** 셋 중 둘은 누구나 갖지만, **셋의 교집합**은 Harness만 갖는다. 차별화는 "AI 잘 쓰는 법"이 아니라 **"AI에 종속되지 않고 잠재력을 키우는, 과학적으로 설계된 한국형 가이드"**.

### 결론 4 — 가장 빠른 진실은 Pretotyping
전수 크롤(8주)을 기다리지 말 것. **랜딩페이지 가짜문 테스트(1주)**가 결제의향을 더 빨리 알려준다. 크롤(이해)과 pretotyping(검증)을 **병행**한다. 단, 외부 노출이므로 Legal·QA 게이트 선통과.

### 결론 5 — "빠짐없이"는 "다 읽기"가 아니라 "격자 + 포화 + 삼각측량"
물리적 전수독해는 불가능·불필요. 6축 격자로 **누락을 보이게** 하고, 포화판정으로 **언제 멈출지**를 정하고, 삼각측량으로 **무엇을 믿을지**를 정한다. 이것이 운영 가능한 "전수에 수렴".

### 결론 6 — 전략 정합성: 분산이 아니라 수렴점
이 조사 인프라는 Physical AI(기존 미션)·B2I 투자에도 **그대로 재사용되는 범용 자산**(다중소스 인텔리전스 엔진)이다. 따라서 교육 사업은 3개 방향을 흩뜨리는 게 아니라, **세 방향이 공유하는 공통 엔진을 강화**할 수 있다. → 단, "메인 격상 vs 인접 확장"은 여전히 CEO 결정 사항(MASTER_PLAN §10).

---

## 6. 거버넌스·비용·법률 (확장에 따른 추가 게이트)

| 영역 | 추가 고려(확장으로 새로 생김) |
|---|---|
| **법률** | 1차생성 데이터(설문·pretotyping 광고)는 **표시광고법·개인정보** 직접 대상 → Legal `legal_review_approve` 선통과. 소셜·맘카페는 공개영역·집계만 |
| **비용** | 상시 레이더 + 멀티에이전트 스웜 = 지속 비용. `DAILY_COST_LIMIT_USD` + DEEP RESEARCH 예산 한도(대표 확정) |
| **윤리** | 경쟁 인텔리전스(채용·광고 라이브러리)는 공개정보만. 비식별·합법 범위 |
| **품질** | 멀티에이전트 산출물도 cross-LLM Red Team + 출처 자세 표기 의무 |

---

## 7. 다음 액션 (AR)

| AR | 내용 | 유형 | 기한 |
|---|---|---|---|
| AR-025 | 본 확장 시각·결론 설계(본 문서) | LLM_EXECUTABLE | 당일 ✅ |
| AR-028 | 6축 격자 커버리지 매트릭스 + 베이지안 신념 보드 템플릿 작성 | LLM_EXECUTABLE | 당일 |
| AR-029 | Pretotyping(가짜문) 랜딩 설계안 + 측정지표 (Legal·QA 선결) | LLM_EXECUTABLE | 당일(설계), 발행은 게이트 후 |
| (CEO) | ① DEEP RESEARCH 예산 한도 ② "조사≡제품(결론1)" 채택 여부 ③ 교육 메인격상 여부 | HUMAN_REQUIRED | CEO |

---

> 생성: 2026-05-24 | 비서실장 | correlation_id: edu-consulting-20260524
> "채널을 세지 말고 좌표계를 세워라. 다 읽지 말고 누락을 보이게 하라. 조사가 곧 제품이다."


---

<!-- 출처: EDU_PIPELINE_ARCHITECTURE.md -->
## 파이프라인 도메인 분리 아키텍처 (Physical AI vs 교육 컨설팅)

> 작성: 2026-05-24 | AR-029 Red Team 조건 C 해소 | correlation_id: edu-consulting-20260524
> 목적: Physical AI(B2I 투자신호) 파이프라인과 교육 컨설팅 파이프라인의 충돌 없는 공존 설계

---

## 1. 문제 정의 (Claude Red Team 지적)

현재 Harness 파이프라인은 단일 수집기 구조다.
- **Physical AI 파이프라인**: arXiv 로보틱스·ETF·반도체 신호 → B2I 투자 인텔리전스
- **교육 컨설팅 파이프라인**: AI 교육 학술·미디어·유튜브 → 학부모 자문 콘텐츠

소스 도메인, 분석 목적, 출력 포맷이 완전히 다름. 혼재 시:
1. 투자 신호에 교육 콘텐츠가 섞여 노이즈 증가
2. 교육 분석에 로보틱스 논문이 들어가 품질 저하
3. LLM 비용 계산 불투명 (도메인별 분리 불가)

---

## 2. 분리 설계 원칙

### Domain Registry 분리 (이미 구현됨)

```
configs/sources/
├── edu_consulting.json     ← 교육 도메인 소스 (AR-028 완료)
└── physical_ai.json        ← Physical AI/ETF 소스 (기존)
```

두 JSON 파일은 `domain` 필드로 구분:
```json
// edu_consulting.json
{"_meta": {"domain": "edu_consulting", ...}}

// physical_ai.json  
{"_meta": {"domain": "physical_ai", ...}}
```

### 수집기 분리 (구현 예정)

```
scripts/
├── run_edu_deep_research.py    ← 교육 전용 수집기 (AR-026, Red Team clear 후)
└── run_physical_ai_pipeline.py ← 기존 Physical AI 파이프라인
```

두 스크립트는 서로 다른 `domain` 파라미터로 기동:
```bash
# 교육 도메인 실행
.venv/bin/python scripts/run_edu_deep_research.py \
  --sources configs/sources/edu_consulting.json \
  --domain edu_consulting --tier 1

# Physical AI 도메인 실행  
.venv/bin/python scripts/run_physical_ai_pipeline.py \
  --sources configs/sources/physical_ai.json \
  --domain physical_ai --tier 1
```

---

## 3. DB 스키마 분리 (제안)

기존 `signals` 테이블에 `domain` 컬럼을 추가해 도메인별 격리:

```sql
ALTER TABLE signals ADD COLUMN domain VARCHAR(50) DEFAULT 'physical_ai';
CREATE INDEX idx_signals_domain ON signals(domain);
```

쿼리 시 도메인 필터 강제:
```sql
-- 교육 도메인 신호만 조회
SELECT * FROM signals WHERE domain = 'edu_consulting' ORDER BY created_at DESC;

-- Physical AI 신호만 조회
SELECT * FROM signals WHERE domain = 'physical_ai' ORDER BY created_at DESC;
```

---

## 4. LLM 비용 계정 분리

각 파이프라인 실행 시 비용 태그 추가:
```python
# 교육 파이프라인 호출 시
response = anthropic.messages.create(
    ...,
    metadata={"domain": "edu_consulting", "correlation_id": "edu-consulting-20260524"}
)
```

월별 비용 리포트 시:
- `domain=edu_consulting` 비용 → 교육사업 예산 ($100/월)에서 차감
- `domain=physical_ai` 비용 → B2I 예산에서 차감 (별도 예산 필요 시 CEO 승인)

---

## 5. 뉴스레터 파이프라인 역할 재정의

CEO 결정(2026-05-24): 뉴스레터 외부 발행 중단 → **B2I 투자 정보 수집 Backend**

```
현재 아키텍처 (명확화):
┌─────────────────────────────────────────────────────┐
│ Physical AI 파이프라인 (domain: physical_ai)          │
│  Tier 1: arXiv/로보틱스/ETF RSS 수집                 │
│  Tier 2: Ollama 필터                                  │
│  Tier 3: Claude/Gemini 투자 신호 분석                 │
│  Tier 4: → [B2I 투자 인텔리전스 내부 보고]            │
│          → [뉴스레터 외부 발행 ❌ BLOCKED]            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 교육 컨설팅 파이프라인 (domain: edu_consulting)       │
│  Tier 1: 교육 RSS/YouTube/논문 수집                   │
│  Tier 2: Ollama 교육 관련성 필터                      │
│  Tier 3: Claude/Gemini 학부모 자문 콘텐츠 분석        │
│  Tier 4: → [부대표 검토 → 유료 구독 발행 ✅]          │
└─────────────────────────────────────────────────────┘
```

두 파이프라인은 **인프라(Mac Mini, .venv, Ollama)를 공유**하되 **소스·DB·LLM 비용 계정은 분리**.

---

## 6. 구현 순서 (Red Team clear 후)

1. `signals` 테이블에 `domain` 컬럼 추가 (스키마 마이그레이션)
2. `run_edu_deep_research.py` 스켈레톤 작성 (AR-026)
3. 기존 `collector.py`에 `--domain` 파라미터 추가
4. 비용 태그 메타데이터 표준화

---

> 리스크 C 해소: 두 파이프라인은 `configs/sources/` 레지스트리 분리, `domain` 파라미터 격리, DB 컬럼 필터로 충돌 없이 공존 가능. 인프라 재사용 효율은 유지하면서 도메인 혼선은 방지됨. 구현 선행 조건: AR-029 red_team_clear.

---

*생성: 2026-05-24 | Jarvis (Red Team 조건 C 해소) | AR-029 | correlation_id: edu-consulting-20260524*
