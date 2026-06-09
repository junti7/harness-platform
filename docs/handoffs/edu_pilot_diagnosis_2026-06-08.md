# Edu Pilot Diagnosis — 2026-06-08

## Scope

대상:
- Mac Mini Harness OS의 `부모 AI 자가점검 (1호 파일럿)`
- 독립 앱 `edu-pilot-app.html`
- Naver 카페/블로그/지식iN 기반 답변 품질 향상 로직

이번 진단은 세 가지를 같이 봤다.
1. 코드 구조
2. 실제 운영 DB의 수집/정제 상태
3. live API를 직접 치는 고객 시뮬레이션 baseline

## 현재 구현 요약

### 제품 구조
- 독립 앱: `harness-os/frontend/public/edu-pilot-app.html`
- 내부 테스트 화면: `harness-os/frontend/src/pages/EduPilotPage.tsx`
- 공개 진입 API:
  - `/api/public/edu/bootstrap`
  - `/api/public/edu/diagnose`
  - `/api/public/edu/curriculum`
  - `/api/public/edu/magic-link/consume`

### 답변 생성 방식
- `harness-os/backend/main.py`의 `_run_edu_diagnose`, `_run_edu_curriculum`
- Gemini prompt-driven 자유 대화 방식
- rule-based 질문 트리 없음
- case persistence / magic link resume 있음

### RAG 근거 계층
- evidence bank: `data/edu_research/evidence_bank.json`
- embedding index: `data/edu_research/evidence_index.json`
- 생성 경로:
  - `scripts/refresh_edu_evidence_bank.py`
  - `scripts/build_edu_evidence_index.py`

### Naver 수집 경로
- `scripts/collect_naver_community.py`
- 공식 Naver Search API 사용
- 수집 대상:
  - 카페글
  - 지식iN
  - 블로그

## 운영 데이터 기준 사실

`harness_prod`에서 확인한 현재 edu_consulting 수집량:

- raw_signals: `30,455`
- top raw source
  - `Naver_블로그`: `11,308`
  - `Naver_카페글`: `10,272`
  - `Naver_지식iN`: `8,426`

filtered_signals도 거의 같은 분포다.
- 즉, Naver 쪽은 Tier 2에서 강하게 탈락하지 않고 대부분 살아남고 있다.

refined_outputs 기준:
- `Naver_카페글`: `6,117`
- `Naver_지식iN`: `3,518`
- `Naver_블로그`: `179`

즉, 운영량 기준으로는 Naver가 edu 파이프라인의 주력 source다.

## 핵심 진단

### 1. "Naver 데이터를 많이 모은다"와 "답변이 자연스럽다"는 아직 연결되지 않았다

운영량은 충분히 많다. 문제는 품질 변환이다.

실제 refined sample을 보면:
- 맘카페의 살아 있는 말투라기보다
- SEO형 일반 가이드 문장
- 학원/마케팅 냄새가 나는 generic 조언
으로 평탄화되는 경우가 많다.

즉, 현재 구조는 `커뮤니티의 현실감`을 살리기보다 `무난한 조언문`으로 다시 써 버린다.

### 2. evidence bank가 너무 얇고 source 현실을 제대로 반영하지 못한다

현재 `evidence_bank.json` 항목 수는 매우 작고, 눈에 띄는 Naver parent voice가 거의 없다.

문제:
- 운영 refined corpus는 Naver 중심
- 하지만 상담 응답에 실제로 녹는 evidence bank는 소수 anchor + 일부 최신 항목 중심
- 결과적으로 “맘카페/블로그 데이터로 더 자연스러워졌다”는 체감이 약하다

### 3. evidence index가 오염돼 있다

`evidence_index.json`을 보면 irrelevant YouTube 조각이 많이 섞여 있다.

문제:
- retrieval candidate pool이 지저분하다
- Naver/교육/부모 문맥보다 잡음이 retrieval에 섞일 가능성이 높다
- prompt 자체는 그럴듯해도, 근거층이 오염되면 결과가 generic해진다

### 4. salutation 내부 코드가 답변에 새는 버그가 있다

실제 live transcript에서 확인:
- `네, father.`

이건 고객 입장에서 즉시 이질감이 생기는 버그다.

원인 후보:
- `preferred_salutation` 내부 enum이 prompt 또는 후처리 경로를 통해 자연어로 치환되지 않고 그대로 노출

### 5. worker / job seeker 시나리오는 현재 사실상 깨져 있다

부모 전형 시나리오는 일부 버틴다.
반면:
- `worker_female_job_seeker`
- `worker_male_office_worker_lagging`

두 시나리오는 live run에서 `ReadTimeout`으로 실패했다.

즉:
- 부모용 제품으로는 어느 정도 굴러가지만
- 직장인/취준생 확장까지는 현재 안정적이지 않다

### 6. next_steps 단계형 응답은 latency 리스크가 크다

고등학생 진로 시나리오에서:
- 기본 대화와 free_start는 응답
- `next_steps`는 timeout

즉, 후반부 심화 단계가 오히려 끊긴다.
이건 전환 UX에 직접 악영향이다.

## Live Simulation Baseline

시뮬레이터:
- `scripts/run_edu_pilot_simulations.py`
- config: `configs/edu_pilot_simulations.json`

대표 baseline 결과:

| Scenario | Score | 상태 | 핵심 불만 |
| --- | ---: | --- | --- |
| 중학생 아들을 둔 아버지 · 숙제 정답 의존 | 94 | 응답 성공 | 답변 자체는 비교적 양호하나 실제 transcript에서 `네, father.` 버그 확인 |
| 고등학생 보호자 · 전공/진로 불안 | 91 | 부분 성공 | 권위 표현 과다, `next_steps` timeout |
| 초등학생 딸 · 스마트폰/AI 혼합 의존 | 72 | 응답 성공 | 자료가 녹아든 느낌 약함, 상담 템플릿 말투가 보임 |
| 20대 여성 취준생 · AI 취업 불안 | 0 | 실패 | scenario 자체 `ReadTimeout` |
| 30대 남성 사무직 · AI 뒤처짐 불안 | 0 | 실패 | scenario 자체 `ReadTimeout` |

## P0 수정 후 상태

이번 턴에서 실제 수정한 것:
- 내부 호칭 enum을 prompt에 직접 넣지 않고 자연어 힌트로 변환
- worker / curriculum 경로의 history, retrieval k, token budget 축소
- 운영용 시뮬레이션이 public rate-limit에 걸리지 않도록 internal mode 추가
- diagnose / curriculum 런타임 이벤트를 `runtime/edu_pilot_runtime_events.jsonl`에 남기도록 추가
- evidence bank / index에 `source_kind`(`community_voice`, `research_policy`, `media_case`) 개념 추가
- retrieval에서 `community_voice + research_policy`를 섞어 고르도록 밸런싱 추가
- evidence layer에서 명백한 엔터테인먼트성 YouTube noise를 제외하는 quality gate 추가

수정 후 재검증 결과:

| Scenario | Score | 변화 |
| --- | ---: | --- |
| 중학생 아들을 둔 아버지 · 숙제 정답 의존 | 73 | `네, father.` 누출은 사라짐. 대신 fallback 문장 비중이 높아짐 |
| 고등학생 보호자 · 전공/진로 불안 | 68 | `next_steps` timeout은 사라짐. 대신 마지막 응답이 generic fallback으로 내려옴 |
| 20대 여성 취준생 · AI 취업 불안 | 71 | 기존 `ReadTimeout` 해소 |
| 30대 남성 사무직 · AI 뒤처짐 불안 | 71 | 기존 `ReadTimeout` 해소 |

즉:
- **안정성은 개선**
- **자연스러운 근거 기반 답변 품질은 아직 부족**

현재 가장 큰 병목은:
- timeout 대신 `fallback`이 자주 나오면서
- 답변이 안전하지만 일반론으로 짧게 수렴하는 점이다.

## 이번 2차 보강 후 추가 진단

원격에서 evidence bank / index를 다시 빌드하고, 내부 시뮬레이션을 재실행했다.

- average score: `72.83`
- min: `68`
- max: `81`
- 공통 complaint:
  - `연구·커뮤니티·현장 자료가 녹아든 느낌이 약하다`

추가로 확인된 사실:
1. `runtime/edu_pilot_runtime_events.jsonl` 기준 worker 경로의 fallback 직접 원인은 현재 `429 RESOURCE_EXHAUSTED`다.
   - 즉 일부 품질 저하는 retrieval뿐 아니라 **Gemini quota exhaustion**이 직접 원인이다.
2. 기존 evidence index에 `source_kind`가 비어 있는 legacy item이 많아서, 밸런싱 로직이 초기에 거의 효과를 못 냈다.
3. 이를 막기 위해 backend에서 `source_kind`를 lazy inference 하도록 보강했다.
   - 다음 시뮬레이션은 quota가 회복된 뒤 다시 보는 게 맞다.
4. 현재 worker 이벤트를 보면 여전히 `general_reference`가 다수다.
   - 즉 실제 corpus에 `community_voice / research_policy` 메타가 충분히 누적되도록
     bank/index 전체 재정비가 더 필요하다.

## 고객 입장에서 체감되는 불만

### A. "내 상황을 읽는다"보다 "상담 템플릿을 돌린다"는 느낌

특히 parent high-school / elementary screen cases에서 반복되는 문제:
- `이맘때`
- `열에 아홉`
- `많은 보호자분들이`
- `이럴 때일수록`

이런 표현이 한두 번은 괜찮지만 누적되면 상담가가 아니라 scripted bot처럼 보인다.

### B. 커뮤니티 자료를 먹였다는 느낌이 안 난다

현재 답변은 “연구·교육부·학부모 고민” 같은 일반 문장으로 흘러간다.

하지만 사용자가 기대하는 건 이런 것이다.
- 맘카페에서 실제로 나오는 불안
- 부모가 쓰는 표현
- 블로그 후기에서 드러나는 시행착오

이 층이 지금 답변에 강하게 드러나지 않는다.

### C. 심화 단계로 갈수록 느려진다

`next_steps` timeout은 특히 위험하다.
- 무료 대화는 되는데
- 정작 다음 단계로 가려는 순간 끊긴다

이건 전환 UX 관점에서 가장 나쁜 지점 중 하나다.

### D. 확장 세그먼트가 준비 안 된 상태로 열려 있다

직장인/취준생은 원래 timeout으로 무너졌고, P0 수정 후에는 응답은 돌아온다.
하지만 현재는 fallback 비중이 높아 `괜찮은 상담`보다는 `안전한 기본 응답`에 가깝다.

즉:
- prompt
- retrieval
- latency
- possibly evidence scope

중 최소 하나가 worker segment에서 무너지고 있다.

## 우선순위 개선 포인트

### P0
1. `preferred_salutation` enum leak 제거
   - `father/mother/neutral/name`이 절대 응답 본문에 그대로 나오면 안 된다.
   - 현재는 해결된 것으로 보이지만 regression scenario는 유지해야 한다.

2. worker / job seeker timeout 원인 분해
   - diagnose prompt 길이
   - retrieved evidence 크기
   - curriculum prompt 크기
   - segment-specific retrieval noise

3. `next_steps` latency 축소
   - evidence 개수 축소
   - history trimming
   - 단계별 별도 prompt 경량화

### P1
4. Naver source precision 강화
   - raw query 축소가 아니라
   - `source_detail`, title, snippet 기준 early precision gate 추가
   - 학원 광고/SEO성 블로그/무관 커뮤니티 배제

5. evidence bank를 "parent voice bank"와 "research bank"로 이원화
   - parent voice: 맘카페/지식iN/블로그의 살아 있는 말
   - research bank: 연구/정책/교육부
   - 현재는 이 둘이 하나로 뭉개져서 generic해진다

6. evidence index source quota 도입
   - noisy YouTube over-representation 제한
   - Naver cafe / kin / blog 상한/하한 관리

7. Gemini quota exhaustion 대응
   - worker 경로 fallback의 주원인이 지금은 `429 RESOURCE_EXHAUSTED`다.
   - provider fallback, cheaper model, queueing 중 하나를 넣지 않으면 품질 개선 효과가 가려진다.

### P2
8. worker/job_seeker를 당장 살릴지, parent-only로 scope를 줄일지 결정
   - 지금처럼 반쯤 열어두면 UX만 손상된다

9. 시뮬레이션을 daily regression으로 편입
   - 최소 4개 시나리오 고정
   - 개선 전/후 점수 delta 추적

## 재사용 가능한 정규 시뮬레이션 프로세스

구현 완료:
- script: `scripts/run_edu_pilot_simulations.py`
- config: `configs/edu_pilot_simulations.json`
- tests: `tests/test_edu_pilot_simulations.py`

기본 실행:
```bash
PYTHONPATH=. .venv/bin/python scripts/run_edu_pilot_simulations.py --base-url http://100.97.175.44:8000
```

단일 시나리오:
```bash
PYTHONPATH=. .venv/bin/python scripts/run_edu_pilot_simulations.py --scenario parent_neutral_highschool_career_major --base-url http://100.97.175.44:8000
```

산출물:
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_<timestamp>.json`
- `docs/reviews/edu_pilot_simulations/edu_pilot_simulations_<timestamp>.md`
- `latest.json`
- `latest.md`

현재 시뮬레이터가 자동으로 잡는 것:
- 성별/호칭 추정 오류
- 내부 enum leak
- 일반론 반복
- 자료 grounding 약함
- actionability 약함
- offer timing
- scenario/runtime timeout

## 결론

현재 구현은:
- `부모 전형 케이스 일부`는 usable
- `맘카페/블로그 데이터가 자연스러운 상담 품질로 직접 이어진다`고 보기는 어려움
- `직장인/취준생 확장`은 현재 기준으로 불안정

즉, 강점은:
- persistence
- magic link
- 기본 상담 흐름

약점은:
- retrieval quality
- Naver precision
- voice authenticity
- latency
- worker segment stability
