# AI 교육 컨설팅 — DEEP RESEARCH 방안 (전 세계 전수 조사 설계 v0.1)

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
