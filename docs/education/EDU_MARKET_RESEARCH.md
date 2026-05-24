# AI 교육 컨설팅 — 시장 조사 & 벤치마킹 (v0.1)

> 작성일: 2026-05-24 | 담당: 비서실장(Chief of Staff) 주도 + Multi-LLM 검증 예정
> correlation_id: edu-consulting-20260524
> 상태: **DRAFT v0.1 — 밑작업(groundwork) 1차. 추가 1차 조사(고객 인터뷰·결제의향 테스트) 전까지 의사결정 근거로 단독 사용 금지**

---

## 0. 근거 자세(Evidence Posture) 표기 규칙

CLAUDE.md §5 규약에 따라 모든 핵심 수치에 근거 자세를 표기합니다.

- `verified` — 정부 발표/공시/1차 출처 직접 확인
- `media` — 언론 보도 인용(2차 출처)
- `vendor-estimate` — 시장조사기관 추정치(출처별 편차 큼, 보수적 해석 필요)
- `speculative` — 추정·예측

---

## 1. 시장 규모 (Market Size)

### 1.1 글로벌 AI in Education 시장

| 항목 | 값 | 근거 자세 |
|---|---|---|
| 2025 시장 규모 | USD 5.2~8.3B (출처별 상이) | `vendor-estimate` |
| 2030 전망 | USD 32~41B | `vendor-estimate` |
| 2035 전망 | USD 70~137B | `vendor-estimate` |
| CAGR (2025-2030) | 31~43% | `vendor-estimate` |
| 최고 성장 세그먼트 | 기업 upskilling / 직무 교육 | `media` |

> **주의:** 시장조사기관별 추정치가 1.6배까지 차이남(=불확실성 큼). 절대 금액보다 "고성장·기업 upskilling 중심"이라는 방향성만 신뢰할 것.
> 참고 거래: Accenture가 Udacity를 약 USD 1B에 인수(기업용 AI 자격·교육 수요 방증). `media`

### 1.2 글로벌 사교육(Private Tutoring) 시장 (인접 시장)

| 항목 | 값 | 근거 자세 |
|---|---|---|
| 2025 | USD 131B | `vendor-estimate` |
| 2030 | USD 209B | `vendor-estimate` |
| CAGR | 9.9% | `vendor-estimate` |

→ AI 교육은 "사교육 + AI"의 교집합으로 진입 가능. 사교육 시장 자체가 거대하고 한국은 특히 과열.

### 1.3 한국 시장 신호

| 신호 | 내용 | 근거 자세 |
|---|---|---|
| 생성형 AI 사용 저변 | 국민 44.5%가 생성형 AI 경험(전년比 +11.2%p), 과기정통부 2025 인터넷이용실태조사 | `verified`(정부조사·언론인용) |
| 정부 성인 교육 | 교육부+국가평생교육진흥원 2026 '인공지능·디지털 30+ 집중캠프'(4주 단기) + '묶음강좌'(온라인) | `verified`(moe.go.kr) |
| 중장년(50+) 민간 시장 | 50대+ 대상 AI 교육 시장 성장, 큐리어스·패스트캠퍼스 맞춤 강의 개설 | `media` |
| 교사 연수 | 생성형 AI 시대 문해력 함양 교사 연수 확대(B2G 수요 존재) | `verified`(정책) |

**해석:** 한국은 (a) 생성형 AI 사용 저변이 빠르게 넓어지나, (b) "쓸 줄 안다"와 "잘 쓴다" 사이 간극이 큼 → 컨설팅 수요의 토대. 다만 성인·재직자·중장년 세그먼트는 이미 정부+대형 플랫폼이 진입.

---

## 2. 경쟁사 벤치마킹 — 어떻게 돈을 버는가

### 2.1 한국 에듀테크 주요 플레이어

| 기업 | 매출/실적 | 수익 모델 | 타겟 | 근거 자세 |
|---|---|---|---|---|
| **엘리스그룹** | 매출 246억(2022) → 395억(2025) | B2B SaaS(LXP) + 코딩/AI 강의 + AI 클라우드·GPU 인프라 | 기업·기관·대학 | `media` |
| **코드잇** | 2025 1Q 매출 64억, 영업익 15억(YoY 매출 +67%), IPO 준비 | B2C(온라인 멤버십 구독 + 부트캠프) + B2B 기업교육, GURU AI 학습 파트너 | 개인 + 기업 | `media` |
| **패스트캠퍼스**(데이원컴퍼니) | 2025 기업교육 AI 매출 비중 51.4%, 출강 400건 중 AI 56.7% | B2C 강의 판매 + B2B 기업 출강(AX 교육) | 직장인 + 기업 | `media` |
| **클래스101** | 6,400+ 클래스 | 월 구독(무제한 수강), 평생교육이용권 연계 | 일반 성인. **19세 미만은 부모 동반해도 구매 불가** | `company` |
| **인프런** | — | 코스 판매(라이프타임) | 개발자·비전공자 | `company` |

**패턴 요약:**
1. **B2B/B2G가 캐시카우** — 기업 출강·기관 계약이 매출의 절반 이상. 단가 높고 안정적이나 영업 인력·레퍼런스 필요.
2. **B2C는 구독 + 부트캠프** — 멤버십 구독이 retention/LTV 견인, 부트캠프가 객단가 견인.
3. **AI 학습 파트너 기능**(코드잇 GURU AI 등)이 차별화 무기로 부상 → Harness의 multi-LLM 역량과 직접 연결되는 지점.
4. **대형 플레이어는 "도구 사용법/직무 전환"에 집중** → "AI에 종속되지 않는 학습법"이라는 각도는 비어 있음(2.3 참조).

### 2.2 학부모·자녀 타겟 상품 (직접 경쟁)

| 사례 | 포지셔닝 | 시사점 | 근거 자세 |
|---|---|---|---|
| MissyShop "공부만 잘하는 아이는 AI로 대체됩니다" 커리큘럼 | "챗GPT 시대, 내 아이를 대체불가 미래형 인재로" | **부모 FOMO를 정확히 겨냥한 상품이 이미 존재** → 수요는 검증됨. 다만 패키지형 콘텐츠 판매에 가깝고, 지속 자문(retainer)·반(反)의존 학습법은 미충족 | `marketplace` |

→ **부모 세그먼트는 수요가 입증되었으나, 지속형 자문 + 반의존 학습이라는 빈틈이 존재.**

### 2.3 글로벌 벤치마크 (부모/가족/AI 리터러시)

| 서비스 | 모델 | 가격 | 시사점 | 근거 자세 |
|---|---|---|---|---|
| **Khanmigo**(Khan Academy) | AI 튜터 + **Parent Dashboard**(자녀 계정 추가, 상호작용 이력, 조정 알림 20개 도구) | **$4/월** (18세+, 미국 한정) | 부모가 "감독·관여"할 수 있는 구조가 결제 유인. 가격은 매우 저렴(규모 게임) | `company` |
| **AI Literacy Academy** | **Cohort 기반**(기수제), 라이브+1년 녹화 접근 | (유료, 기수제) | 동기부여·완주율 높은 cohort 모델. 소규모·고관여 적합 | `company` |
| **Common Sense + Day of AI / OpenAI / UNICRI** | 부모·청소년용 AI 리터러시 **무료 toolkit** | 무료 | 무료 자료가 이미 풍부 → 단순 "AI 소개"는 차별화 불가. **판단·전략·맞춤화**에서 유료 가치 발생 | `nonprofit/company` |

### 2.4 가격대 벤치마크 (가격 책정 근거)

| 형태 | 글로벌 가격대 | 근거 자세 |
|---|---|---|
| 라이브 1:1 튜터링 | $30~150/시간 | `media` |
| self-paced 코스 | $99~399 | `media` |
| 월 구독 | $150~400/월 (튜터링), $4/월(Khanmigo 같은 규모형) | `media` |
| 핵심 인사이트 | **구독 모델이 pay-per-session보다 retention·LTV 우수** | `media` |

---

## 3. 차별화 가설의 근거 — "AI 의존" 문제 (Harness의 무기)

대표님이 제기한 "AI 의존 → 주도적 학습 약화" 문제는 **연구로 뒷받침되는 실재 위험**이며, 경쟁사가 점유하지 못한 포지셔닝입니다.

| 연구/현상 | 핵심 수치 | 근거 자세 |
|---|---|---|
| 영국 연구(650+명, 17세+): AI 의존도 ↔ 비판적 사고 | 상관계수 **-0.68** (의존↑ = 비판력↓) | `media`(학술지 인용) |
| 인지적 오프로딩(cognitive offloading)이 매개 변수 | 상관 **+0.72** | `media` |
| 연령대 차이 | 17-25세는 의존↑·비판력↓ / **46세+는 의존↓·비판력↑** | `media` |
| ChatGPT 학습 실험 | 단기 정답률 89%이나 기억력·자기주도 문제해결력 퇴화 | `media` |
| '인지 부채(cognitive debt)' 경고 | "편하지만 멍해진다" | `media` |
| 10대 AI 과의존 | 외로움·사회성 퇴화 "AI 패닉" 확산 | `media` |

**전략적 함의:**
- 시장의 99% 상품은 "AI를 **더 많이/빨리** 쓰는 법"을 판다.
- Harness는 "AI를 **종속 없이, 잠재력 증폭기로** 쓰는 법"을 팔 수 있다 — 연구로 정당화되고, 부모의 진짜 불안("우리 애가 AI 때문에 바보 되는 거 아닌가")을 직접 건드림.
- 이는 단순 도구 강의로 복제 불가능한 **판단·설계 영역** → 유료 가치의 원천.

---

## 4. 기존 Harness 자산과의 연결 (Synergy)

| Harness 자산 | 교육 컨설팅 활용 |
|---|---|
| Multi-LLM 콘텐츠 엔진(Tier 1~4) | 연령별·과목별 "비의존 AI 활용 가이드" 고순도 콘텐츠 대량 생산 |
| 주간 발행 파이프라인(뉴스레터) | "부모용 AI 교육 weekly brief" 구독 상품으로 재활용 |
| 부대표(VP)의 강점(EQ·학부모 생활권 감각·독자 공감) | **부모 세그먼트 콘텐츠 검토·고객 공감의 최적 인력** |
| 기존 PILOT 문서 자산 | `docs/PILOT_PARENT_CUSTOMER_ANIMATION_HS_SERVICE_SIMULATION.md` — 불안한 부모가 단발 보고서보다 **지속형 advisory retainer**에 결제 의향이 높다는 내부 가설 이미 존재 |

> **내부 선례 인용:** PILOT_PARENT 문서는 "부모 고객은 결제 가능성이 오히려 더 높다(문제의 고통이 크고, 실패 비용이 크고, 반복적으로 불안하다)"고 기록. 본 사업은 그 가설의 자연스러운 확장.

---

## 5. 미해결 정보 격차 (다음 1차 조사 필요)

본 v0.1은 2차 자료(데스크 리서치) 기반입니다. **결제 의사결정 전 반드시 메워야 할 격차:**

1. **결제 의향(WTP) 1차 검증** — 익명 학부모 5~10명 인터뷰: 실제 지불 의향 금액·형태(구독 vs 단발).
2. **직접 경쟁사 정밀 분석** — MissyShop류·클래스101 부모 대상 강의의 실제 커리큘럼·가격·후기.
3. **법률 스캔** — 미성년 자녀 데이터(개인정보보호법/PIPA), 교육 서비스 표시·광고(표시광고법), 효과 과장 표현 리스크. (Legal Counsel)
4. **CAC/채널** — 학부모 도달 채널(맘카페·인스타·유튜브) 획득 비용 가설.
5. **공급 역량** — 1:1/소그룹 자문의 인력 병목 vs 콘텐츠·구독의 확장성 트레이드오프.

---

## 6. 출처 (Sources)

- [교육부 — 성인 AI·디지털 교육](https://www.moe.go.kr/boardCnts/viewRenew.do?boardID=294&boardSeq=105371&lev=0&searchType=null&statusYN=W&page=1&s=moe&m=020402&opType=N)
- [AskEdTech — 중·장년 겨냥 AI 교육 시장 커진다](https://askedtech.com/knowledge-archive/68334b7b01a552bdf83a4dc2)
- [과기정통부 2025 인터넷이용실태조사(44.5% 생성형 AI 경험)](https://dazabi.com/insurance_magazine/article.php?id=11786)
- [코드잇 1분기 매출 64억·67% 성장 — 플래텀](https://platum.kr/archives/258973)
- [패스트캠퍼스 기업교육 AI 매출 51.4% — 플래텀](https://platum.kr/archives/282854)
- [엘리스그룹 기업정보(매출 추이) — THE VC](https://thevc.kr/elicegroup)
- [영 학술지: 젊은 층 AI 과의존·비판적 사고 손상 — 뉴시스](https://www.newsis.com/view/NISX20250117_0003036023)
- ['인지 부채' 경고 — 벤처스퀘어](https://www.venturesquare.net/1021051)
- [AI 중독 10대 사회성 퇴화 "AI 패닉" — 전자신문](https://www.etnews.com/20251022000440)
- [AI in Education Market(2030 전망) — Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/ai-in-education-market)
- [AI in Education Market(2035 전망) — SNS Insider/GlobeNewswire](https://www.globenewswire.com/news-release/2026/05/22/3300198/0/en/AI-in-Education-Market-Size-to-Grow-70-55-Billion-by-2035-SNS-Insider.html)
- [Khanmigo for parents](https://www.khanmigo.ai/parents)
- [AI Literacy Academy(cohort)](https://ailiteracyacademy.org/)
- [OpenAI — AI literacy resources for teens and parents](https://openai.com/index/ai-literacy-resources-for-teens-and-parents/)
- [Common Sense — Parents Need AI Literacy Lessons Too(toolkit) — EdWeek](https://www.edweek.org/technology/parents-need-ai-literacy-lessons-too-a-new-toolkit-aims-to-help/2025/11)
- [Tutoring Pricing Guide 2026 — Mentomind](https://mentomind.ai/tutoring-pricing-guide-2026/)
- [MissyShop — "공부만 잘하는 아이는 AI로 대체됩니다" 커리큘럼](https://www.kmarket365.com/m/prod_detail.asp?prod_code=casiop2921)

---

> 생성: 2026-05-24 | correlation_id: edu-consulting-20260524
> 다음 갱신: 1차 조사(WTP 인터뷰) 결과 반영 시 v0.2
