# 전세계 데이터 수집 채널 전수 목록
## "지구상에 존재하는 모든 채널"

> 작성: 2026-05-25 | correlation_id: edu-consulting-20260524
> 목적: AI 교육 컨설팅 DEEP RESEARCH를 위한 전방위 데이터 소스 전수 리스트
> 수집 대상: AI 교육 불안·의존·직장인 AI 압박·학부모 고민·교육 트렌드
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
| ✅📊 Becker Friedman Institute | bfi.uchicago.edu | Working Papers RSS | BFI WP 2025-144 출처 |
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
