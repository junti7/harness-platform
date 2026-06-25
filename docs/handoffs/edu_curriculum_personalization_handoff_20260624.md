# Handoff — edu 개인화 커리큘럼 & 훈련 플로우 연결 (③)

- 작성: 2026-06-24
- 작성자: Claude (Opus 4.8) 세션
- 대상 독자: 이어서 작업할 LLM/엔지니어
- 현재 HEAD: `cb1cd76` (origin/main 동일, MBP 작업트리 clean)

---

## 0. 지금 당장 해야 할 일 (TASK ③)

**개인화 커리큘럼을 실제 "새 훈련(day0 세션)" 학습 플로우에 주입**한다.

현재 상태:
- ✅ `맞춤 커리큘럼` **미리보기 화면**(CurriculumScreen)은 개인화·최신성·구체성까지 완성됨.
- ❌ **새 훈련 시작 → TrainingScreen(day0 세션)** 은 아직 정적 v0 콘텐츠 그대로. 커리큘럼이 여기엔 안 들어감.

CEO 피드백(2026-06-24): "새로 만든 커리큘럼이 **학습 UX에 고스란히 적용**되어야 하고, **미세하게 최신 정보를 찰떡같이 안다**는 감흥 포인트가 있어야 한다. 지금 훈련 플로우는 감흥 0, 상업성 0점."

목표: 새 훈련을 시작/재개하면 day0 화면이 **그 케이스의 intake 속성으로 개인화된 커리큘럼**으로 열리도록 한다.
- 개인화된 오프닝(예: "○○님 상황(학부모·ChatGPT·왕초보)에 맞춰, 오늘 들어온 '우리 아이 숙제 AI' 흐름부터 시작합니다")
- 같은 세그먼트의 **실제 고민**과 **최근(N일 전) 관련 자료**를 day0 안에 노출
- (선택) day0 단계/체크리스트 순서를 개인화 가중치 순으로 재배치
- (선택) day0 콘텐츠에 사용자 LLM 기준 **최신 도구 사실**(perishable overlay) 끼워넣기

---

## 1. 핵심 아키텍처 (이미 구현·배포됨)

### 1-1. 데이터 파이프라인
- **테이블** `edu_curriculum_evidence` (PostgreSQL `harness_prod`)
  - 컬럼: `content_hash`(PK), `refined_id`, `source`, `title`, `klass`(evergreen|perishable),
    `buckets`(jsonb), `model_tags`(jsonb), `item_created_at`, `ingested_at`, `score`,
    `segment`(parent|worker|NULL), `collect_query`
  - Mac Mini(prod)·MBP(dev) 모두 **582행** 적재됨(동일 시드).
- **CLI** `scripts/build_edu_curriculum.py`
  - `ingest`: 정제 SoT(`refined_outputs ⋈ filtered_signals`, domain=edu_consulting) 증분을
    분류·upsert. 워터마크는 `refined_outputs.id`(단조). segment/collect_query 는 `raw_signals`
    LEFT JOIN 으로 carry. 신규 모델 감지 시 exit 10.
  - `build`: 2층 커리큘럼 산출(`runtime/edu_curriculum.json`/`.md`). 척추(evergreen 합의빈도)
    + 오버레이(perishable 최근 30일 freshness decay).
  - `personalize --llm --level --motivation --env --job`: 요청시점 재편 CLI(프로토타입).
  - `scripts/edu_daily.sh` 5단계로 편입(daily ingest + 월요일 build). cross-LLM **red_team_clear** 완료.

### 1-2. 개인화 공유 로직 — **여기가 ③의 재료**
**`core/edu_curriculum.py`** (CLI·백엔드 공용 단일 출처):
- `personalize(rows, *, llm, level, motivation, env, job, now=None) -> dict` — **순수 함수**.
  파이프라인 무재실행, 미리 적재된 풀을 in-memory 재편(밀리초).
  반환 키:
  - `attrs`, `segment`, `base_pool`
  - `order`: `[{topic, weight}]` (개인화 학습 순서)
  - `overlay`: `[{model, freshness}]` (사용자 LLM 기준 최신 신호)
  - `top_concerns`: `[{concern, count}]` (같은 세그먼트 **실제 고민** = collect_query 빈도)
  - `highlights`: `[{title, days_ago, models, concern}]` (동기 버킷 매칭 **최근 관련글**)
  - `fresh_note`: `{pool_total, recent_30d, newest_days_ago}` (최신성)
- `load_evidence_rows() -> rows` (execute_query 로 테이블 전체 로드)
- 매핑 상수: `LEVEL_WEIGHTS`, `MOTIVATION_WEIGHTS`, `ENV_WEIGHTS`, `JOB_TO_SEGMENT`,
  **`DEVICE_TO_ENV`**(iphone/android→mobile, mac/windows→pc), **`EXPERIENCE_TO_LEVEL`**(beginner/intermediate/advanced),
  `LLM_ALIASES`(챗gpt↔chatgpt 동의어).
  → **이 매핑들이 intake 속성 → personalize 인자 변환에 그대로 쓰인다.**

### 1-3. 백엔드 엔드포인트 (이미 있음)
- `POST /api/edu/vp-training/curriculum` (`harness-os/backend/main.py` 약 9870행)
  - 모델 `EduVpTrainingCurriculumRequest`(main.py 약 6049행): email, llm, level, motivation, env, job
  - secret tier(`Depends(_require_secret)`) + email 있으면 `_edu_vp_assert_access`
  - `from core.edu_curriculum import personalize, load_evidence_rows` → 결과 반환(테이블 없으면 available:false 폴백)

### 1-4. 프론트엔드 (edu-app, dev 전용)
- `harness-os/edu-app/` (Vite+React, dev 포트 5174, proxy `/api`→`127.0.0.1:8000`)
- `src/components/CurriculumScreen.tsx` — 맞춤 커리큘럼 미리보기(완성). 선택 localStorage 저장,
  최신성 배지/실제 고민 칩/최근 자료 카드/학습 순서/overlay 렌더.
- `src/lib/vpTraining.ts` — `fetchPersonalizedCurriculum(email, attrs)` + 타입
  (`PersonalizedCurriculum`: order/overlay/top_concerns/highlights/fresh_note).
- `src/lib/api.ts` — `VP_TRAINING.curriculum` 등 엔드포인트 상수.
- `src/App.tsx` — View 상태머신: `auth|cases|training|curriculum`.
- `src/components/CaseSelectScreen.tsx` — 케이스 목록 + long-press 삭제 + "맞춤 커리큘럼 미리보기" 버튼.
- `src/components/TrainingScreen.tsx` — **③에서 손댈 화면**. `/session`→`training_state`(day0/day1)
  를 받아 단계 흐름을 렌더. 현재 day0 정적 콘텐츠.

---

## 2. 훈련 플로우(day0) 생성 구조 — ③에서 수정할 지점

`harness-os/backend/main.py`:
- `edu_vp_training_intake` (약 9750행): 새 훈련 시작 = 케이스 생성. intake 속성 저장.
- `_edu_vp_build_day0(intake)` (**7752행**): day0 콘텐츠 dict 생성.
  intake 에서 읽는 값: `preferred_llm`, `current_device`, `desktop_os`, `biggest_friction`, `learning_goal`.
  반환: title, learning_why, learning_outcome, checklist, schedule_blocks, sample_materials,
  tutorial_steps, recommended_learning, pass_fail_rubric 등.
- `_edu_vp_build_day1(intake)` (7809행): day1 — 이미 `_retrieve_evidence_bundle(query, "parent", k=4)`로
  근거 카드를 끌어옴(참고 패턴).
- `_edu_vp_refresh_state(state)` (7408행): flow_outline 등 파생값 갱신.
- `_edu_vp_load_state`(7366) / `_edu_vp_store_state`(7385) / `_edu_vp_normalize_state_keys`(7210).
- `_edu_vp_latest_case_payload(email, case_id)` (7946행): customer+case 페이로드(여기서 `segment` 접근 가능).
- `edu_vp_training_session` GET (약 9823행): `/session` 응답에서 `training_state` 반환.
  ← **여기에 개인화 블록을 주입하는 게 가장 간단.**

### intake/케이스가 보관한 개인화 속성
- intake 기본값: `preferred_llm='claude'`, `current_device='iphone'`, `desktop_os='mac'`,
  `ai_experience='beginner'` (main.py 약 5985–5988).
- `customer.segment` = `parent|worker` (가입 시 'worker' 기본; `_edu_vp_latest_case_payload`에서 cu.segment 조회).
- **motivation 은 명시 필드가 없음** → `learning_goal`/`biggest_friction` 텍스트에서 추론하거나
  기본값(parent→`child_study`, worker→`work`)으로 매핑 권장.

---

## 3. 권장 구현안 (③)

### 3-A. 백엔드: /session 응답에 개인화 커리큘럼 주입 (최소 침습, 권장)
`edu_vp_training_session`(GET /session, 약 9823행)에서 `training_state` 반환 직전:
1. 케이스/customer 에서 속성 수집: `preferred_llm`, `ai_experience`, `current_device`, `customer.segment`.
2. `core.edu_curriculum` 매핑으로 personalize 인자 변환:
   - `llm = preferred_llm`
   - `level = EXPERIENCE_TO_LEVEL.get(ai_experience, '')`
   - `env  = DEVICE_TO_ENV.get(current_device, '')`
   - `job  = segment`  (JOB_TO_SEGMENT 는 'parent'/'worker' 그대로 받음)
   - `motivation` = segment 기반 기본(parent→child_study, worker→work) 또는 learning_goal 추론
3. `personalize(load_evidence_rows(), llm=, level=, motivation=, env=, job=)` 호출.
4. 결과를 `training_state["personalized_curriculum"] = {...}` 로 첨부(없거나 비면 생략).
   - 실패/빈 풀은 graceful 무시(기존 동작 보존).
5. **주의**: `load_evidence_rows()` 매 요청 호출은 582행이라 부담 적지만, 트래픽 늘면 캐시(TTL) 고려.

대안(3-B): `_edu_vp_build_day0` 안에서 personalized 결과로 checklist/schedule 순서를 재배치하고
sample_materials 에 highlights 를 끼워넣기 → 더 깊은 통합이지만 day0 생성 시점에만 반영(재개 시 갱신 안 됨).
**3-A(세션 시점 주입)가 신선도 유지에 유리** — 권장.

### 3-C. 프론트엔드: TrainingScreen 상단에 개인화 오프닝 섹션
`src/components/TrainingScreen.tsx` 에서 `training_state.personalized_curriculum` 가 있으면 day0 상단에:
- 오프닝 문장: "○○님(역할·LLM·수준)에 맞춰 구성했어요"
- `fresh_note` 배지(오늘/N일 전 반영)
- `top_concerns` 칩 + `highlights` 카드 1–2개 ("최근 들어온, 내 상황과 맞는 자료")
- (선택) `order` 상위 토픽을 day0 단계 라벨에 매핑
- `src/lib/vpTraining.ts` 의 `TrainingState` 타입에 `personalized_curriculum?: PersonalizedCurriculum` 추가.
- CurriculumScreen 의 렌더 컴포넌트를 재사용 가능하게 분리하면 중복 최소화.

---

## 4. 빌드·배포·검증 (반드시 준수)

### 규약 (CLAUDE.md / 메모리)
- **commit → push → origin/main** 만 SoT. Mac Mini 수동수정·scp **금지**.
- 배포는 **`scripts/deploy_to_macmini.sh <경로...>`** 로만. `harness-os/backend/*`·`core/*` 변경 시
  스크립트가 백엔드 launchd reload 자동 수행(파이썬 모듈 캐시 때문에 **백엔드 재시작 필수**).
- edu-app 은 **Mac Mini 배포 대상 아님**(dev 전용). 커밋·푸시만.
- Mac Mini SSH: alias `macmini`, 사용자 `juntaepark`(점 없음). `ssh macmini`.
- secret/토큰을 로그·코드에 출력 금지. edu-app `.env`(gitignored)의 `VITE_HARNESS_SECRET` 사용.
- **Red Team 은 CEO(junti7) 명시 주문 시에만**. 자동/정례 red-team 금지.
- 작업 종료 시 **MBP·Mac Mini 양쪽 git status 청결** 확인. runtime 산출물은 gitignored.

### 로컬 dev 검증 루프
```bash
# 백엔드(파이썬) 변경 후 모듈 캐시 갱신:
launchctl kickstart -k gui/$(id -u)/com.harness.harness-os-backend
# 엔드포인트 확인:
SECRET=$(grep '^VITE_HARNESS_SECRET=' harness-os/edu-app/.env | cut -d= -f2-)
curl -s -X POST http://127.0.0.1:8000/api/edu/vp-training/curriculum \
  -H "Content-Type: application/json" -H "X-Harness-Secret: $SECRET" \
  -d '{"llm":"chatgpt","level":"beginner","motivation":"child_study","env":"mobile","job":"학부모"}'
# edu-app dev (이미 떠 있을 수 있음 — :5174):
cd harness-os/edu-app && npm run dev   # proxy /api → 127.0.0.1:8000
npm run build && npm run lint          # 커밋 전 둘 다 green 필수
```
- edu-app 의 `react-hooks/set-state-in-effect` 린트룰 주의: effect 동기 본문에서 setState 금지.
  async IIFE 안에서만 호출(`void (async () => { setLoading(true); ... })()`). 기존 패턴 따를 것.

### prod 배포 (백엔드 변경 시)
```bash
git add <files> && git commit && git push origin main
scripts/deploy_to_macmini.sh harness-os/backend/main.py core/edu_curriculum.py
# 스크립트가 diff=0 검증 + 백엔드 reload 수행. 출력의 ✅ 확인.
```

### DB 시드(필요 시 — MBP dev DB가 비었을 때)
- evidence 582행은 이미 양쪽에 적재됨. 만약 MBP dev 가 초기화되면:
  - `PYTHONPATH=. .venv/bin/python scripts/build_edu_curriculum.py ingest` (MBP refined 데이터로 적재되나
    MBP 정제 내용이 how-to 분류 통과 4건뿐이라 빈약 →)
  - Mac Mini 덤프 시드 절차는 이전 세션 scratchpad(`dump_evidence.py`/`load_evidence.py`) 참고.

---

## 5. 이번 세션 커밋 이력 (origin/main)
- `c6da36d` edu 커리큘럼 freshness 파이프라인(2층) — **red_team_clear**
- `9eb5655` edu-app v0 화면 통합 + 훈련 세션 레이어 + 케이스 삭제
- `4815193` chore: data/harness.db gitignore + IBKR handoff 문서
- `867bfc7` segment/query carry + personalize CLI 프로토타입
- `a994542` personalize 엔드포인트 + 공유 모듈(core/edu_curriculum.py)
- `335e6f1` edu-app 맞춤 커리큘럼 화면(라이브 선택기)
- `459a1c6` edu-app long-press 삭제 버그 수정(이동 임계값)
- `1ddf903` 개인화 응답에 구체 '감흥' 레이어(top_concerns/highlights/fresh_note)
- `cb1cd76` edu-app 커리큘럼 화면: 선택 localStorage 저장 + 감흥 섹션  ← **HEAD**

## 6. 알려진 MINOR (비차단)
- ingest 신규모델 트리거(전체 model_tags)와 build 의 version_change_trigger 표시(perishable만)
  모집단 불일치 → false-build 1회만 유발, 데이터 무해.
- 예시 프롬프트(refined body 따옴표 추출)는 노이즈 커서 미채택. 필요 시 정제 후 highlights 에 추가 가능.
- 성별 개인화: 데이터에 없음(segment=parent|worker). 추가 수집 필요 → 현 단계 skip.
- MBP dev DB 의 edu_cases/turns/snapshots 는 이전에 **전부 비움**(테스트 클린슬레이트). 새 훈련부터 쌓임.

## 7. 빠른 오리엔테이션 명령
```bash
# 개인화 출력 한눈에:
PYTHONPATH=. .venv/bin/python scripts/build_edu_curriculum.py personalize \
  --job 학부모 --llm chatgpt --level beginner --motivation child_study --env mobile
# day0 생성 코드:
sed -n '7752,7807p' harness-os/backend/main.py
# /session 엔드포인트:
sed -n '9823,9868p' harness-os/backend/main.py
```
