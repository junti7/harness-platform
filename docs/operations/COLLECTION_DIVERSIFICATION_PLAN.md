# Collection Diversification Plan — 수집 채널 다양화 극대화 방안

- 작성일: 2026-06-09
- 작성: Codex (CEO 지시 "수집을 훨씬 더 다양한 채널로 극대화")
- 상태: DRAFT — 실행 전 `legal_review_approve` + `red_team_clear` + Pre-Mortem 필요 (소스 추가 = 데이터 수집 정책 변경, CLAUDE.md §4/§5)
- 관련: `configs/sources/physical_ai.json`, `configs/sources/edu_consulting.json`, `scripts/run_edu_deep_research.py`, `adapters/content/collector.py`, `docs/handoffs/collection_scope_handoff_2026-06-03.md`

---

## 0. 현황 진단 (사실 기반)

일일 파이프라인(`com.harness.pipeline`, 10:00 KST → `run_pipeline.py`)은 **`adapters.content.collector.collect()` 하나만** 호출한다. 이 수집기는 **RSS fallback + data.go.kr open_api만** 처리한다.

| 도메인 | config 소스 | 실가동 | 미가동(사장) |
|---|---|---|---|
| physical_ai | 25 (enabled 13) | arXiv×3, IEEE/MIT/TechCrunch, Boston Dynamics, google_news rss_search×5 | reddit·hackernews·youtube·maily·brunch·naver_blog·naver_cafe·x·threads·instagram·discord·forum (12) — **수집기에 처리 분기 없음** |
| edu_consulting | 89 + youtube 10 + api 2 | rss·arxiv·scholar (health-recovery 경로) | **openalex·eric·pubmed·hackernews·reddit·naver·youtube — 콜렉터 구현됨, 스케줄 호출 없음** |

추가 사실:
- edu 일일 수집은 `run_pipeline.py`에 없음. `edu_daily.sh`(naver community + tier3)와 `collection_health_check.py` 복구 경로(`--sources rss,arxiv,scholar`)에만 의존.
- `com.harness.2026-ai-seamless-gather`(youtube 24h) = **disabled**.
- `run_edu_deep_research.py`는 이미 10개 콜렉터 보유: `rss, scholar, arxiv, openalex, eric, pubmed, hackernews, reddit, naver, youtube` (기본값은 `rss,scholar,arxiv` 3개만).

**결론: 다양화의 1차 동력은 신규 개발이 아니라 "이미 구현된 콜렉터를 스케줄에 연결"하는 것이다.**

### 제약 (반드시 동반 처리)
1. **병목은 수집이 아니라 정제.** gemini-2.5-flash 10k RPD 하드캡. 원시 수집만 늘리면 429 백로그만 증가. → 채널별 **일일 수집 상한** + Tier2 dedup 강화 + 도메인 공정 분배가 전제.
2. **거버넌스 게이트.** 소스 추가 = 데이터 수집 정책 변경 → `legal_review_approve`(저작권/ToS/PIPA) + `red_team_clear` + Pre-Mortem 선행. RSS/공식 API = 저위험, 소셜/스크래핑 = 고위험으로 분리.

---

## 1. Wave 1 — 코드 0줄, 즉시 가동 (저위험)

이미 구현·검증된 콜렉터를 켜는 것뿐. 신규 ToS 리스크 거의 없음(공식 API/공개 RSS).

| 액션 | 방법 | 효과 |
|---|---|---|
| edu 전 콜렉터 일일 가동 | `run_edu_deep_research.py --sources rss,scholar,arxiv,openalex,eric,pubmed,hackernews,reddit,naver,youtube` 를 일일 launchd로 등록 | 사장된 edu 콜렉터 7종 부활 |
| edu 수집을 일일 파이프라인에 편입 | `run_pipeline.py`가 physical_ai 직후 edu deep-research 호출 | edu가 ad-hoc/복구 경로 의존 탈피 |
| youtube seamless-gather 재가동 | `com.harness.2026-ai-seamless-gather.plist.disabled` → load (쿼터 예산 내) | 영상 전사 채널 복원 |
| 채널별 일일 상한 도입 | 각 콜렉터에 `--max-per-source` / env cap | 정제 백로그 폭주 방지 |

검증: 가동 후 `raw_signals`에서 source별 7일 신규 건수 > 0 확인. 0이면 해당 콜렉터 죽은 것(아래 Wave 2 진단).

---

## 2. Wave 2 — 소규모 코드, physical_ai 콜렉터 확장 (저~중위험)

physical_ai 수집기는 RSS+data.go.kr만 안다. edu에 이미 있는 `collect_reddit / collect_hackernews / collect_youtube / collect_openalex` 등을 **physical_ai 도메인으로 재사용**해 12개 사장 config를 실제 가동.

| 액션 | 방법 |
|---|---|
| 공용 deep-research 러너 | edu 콜렉터들을 도메인 파라미터화해 physical_ai 키워드/서브레딧/채널로 재호출 |
| physical_ai 학술 확장 | OpenReview·Papers with Code·HuggingFace papers·bioRxiv(로보틱스) API 추가 |
| 죽은 RSS 정리 | 전 RSS liveness 감사 → 응답 0 피드 교체(IEEE/MIT/arXiv 최근 적재 0 여부 점검) |
| dedup 강화 | 교차 채널 중복(같은 논문이 arXiv+HN+reddit) 정규화 dedup → 정제 부하 절감 |

---

## 3. Wave 3 — 신규 채널 다양성 극대화 (위험도별 분리)

### 3a. 저위험 (공식 API / 공개 RSS — legal 간소 검토)
- **학술**: OpenReview, CORE, Papers with Code, HuggingFace Daily Papers, bioRxiv/SSRN, OpenAlex(전 분야 확장)
- **산업 1차 소스**: 기업 블로그 RSS — NVIDIA, Google DeepMind, Tesla AI, Figure, Unitree, Agility, Physical Intelligence, Skild; GitHub releases/trending(주요 로보틱스·LLM repo); HuggingFace models/datasets trending
- **뉴스 버티컬 확장**: Google News 쿼리 추가(humanoid, embodied AI, on-device AI, 로봇 파운데이션 모델); 한국 테크미디어 RSS(전자신문, AI타임스, ZDNet Korea, 디지털데일리)
- **정책/정부**: 교육부, KEDI, OECD Education, UNESCO, data.go.kr 교육 데이터셋, NIA, KISTEP

### 3b. 중위험 (rate-limit/ToS 주의 — API 키 + 상한)
- Reddit 서브레딧 확장(r/MachineLearning, r/robotics, r/LocalLLaMA, r/Korea 교육), Hacker News(Algolia API), Lobsters, Product Hunt, App Store/Google Play 리뷰(경쟁 교육앱)
- YouTube Data API 채널/검색 확장(쿼터 관리)

### 3c. 고위험 (legal_review_approve 필수 — 스크래핑/소셜/개인정보)
- X(Twitter)·Threads·Instagram — API 비용/ToS, 개인정보
- Naver 맘카페 공개영역 — 이미 `pending_legal_approval`(저작권/ToS/PIPA)
- Discord 공개 서버, 브런치/티스토리/디시 스크래핑
- 학부모 설문 패널 — PIPA 동의 메커니즘 선행

---

## 4. 실행 순서 & 게이트

1. **Wave 1 먼저** (코드 0, 저위험) → 즉시 다양성 2배 이상, ROI 최고.
2. Wave 1 가동 후 **정제 처리량 모니터링** — 백로그 증가율이 정제율 초과하면 채널 상한 하향(수집 ≤ 정제 capacity 원칙).
3. Wave 2/3a는 **묶어서 1회 `legal_review_approve` + `red_team_clear` + Pre-Mortem** 상신.
4. Wave 3c는 **개별 legal gate**, 통과 전 BLOCK.

## 5. 성공 지표
- 활성 소스(7일 신규>0) 수: 현재 ~9 → Wave1 후 목표 ~20, Wave3 후 ~40+
- cost per useful signal 유지/개선(다양성이 노이즈만 늘리면 실패)
- 도메인 균형: physical_ai vs edu 적재 비율 편중 해소
- 정제 백로그: 수집 확대 후에도 일일 정제율 ≥ 일일 수집율 유지
