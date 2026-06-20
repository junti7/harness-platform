# VP AI 교육 프로그램 상세 개발 계획서

> 작성일: 2026-06-20  
> 상태: draft for internal build + red-team review  
> 범위: mac mini Harness OS 내부 `VP 대상 AI 교육 프로그램`을 외부 서비스와 동일한 완성도로 설계·구축하기 위한 제품/운영/데이터/평가 계획  
> 상위 기준: `AGENTS.md`, `CLAUDE.md`, `docs/education/EDU_CONSULTING_MASTER_PLAN.md`, `docs/education/EDU_UX_SERVICE_GUIDELINES.md`, `docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md`

---

## 0. 한 줄 정의

이 프로그램은 `부대표(VP) 본인의 AI 숙련을 먼저 끌어올린 뒤`, 그 과정에서 축적한 실제 막힘·이해 포인트·언어 전환 노하우를 구조화하여 **향후 외부 edu 서비스의 핵심 운영 자산으로 재사용**하는 내부 first-party 교육 제품이다.

---

## 1. 왜 지금 이 프로그램이 필요한가

현재 mac mini Harness OS에는 `부모 AI 진단 (1호 파일럿)` 메뉴가 있으나, 그대로는 아래 한계가 있다.

1. 대외 고객을 위한 제품 구조가 아직 거칠다.
2. 답변 품질, 디바이스 전환, 케이스 상태, 단계형 학습 설계가 충분히 정교하지 않다.
3. 우리 팀 내부에 `AI 초보자가 실제로 어디서 막히는지`에 대한 운영 데이터가 부족하다.
4. VP는 reader empathy와 시장 감각은 강하지만, AI 개념·도구·실습에 대한 체계적 도메인 학습 경로는 아직 제품화되어 있지 않다.

외부 서비스를 먼저 밀기보다, **VP를 첫 번째 실제 고객이자 훈련 대상**으로 삼아 같은 시스템 안에서 완성도를 올리는 것이 더 합리적이다.

이 접근의 장점:

- 외부 트래픽 없이도 고밀도 학습 로그를 축적할 수 있다.
- AI 초보자 관점의 friction을 반복적으로 드러낼 수 있다.
- 결과물을 바로 VP review / reader empathy 시스템과 연결할 수 있다.
- 외부 서비스에 들어갈 안내 문구, 과제 난이도, 디바이스 handoff, selected-LLM별 가이드 품질을 내부에서 먼저 검증할 수 있다.

---

## 2. VP 현재 위치와 설계 전제

`CLAUDE.md` 기준 VP는 다음 프로파일을 가진다.

강점:

- EQ
- 시장 촉
- 일반 독자 공감
- 한국어 자연스러움 판단
- 가족/교육/가정 운영 맥락의 현실 감각
- paid hesitation 감지

현재 보강이 필요한 영역:

- AI 기본 개념 체계화
- 도구별 차이 이해
- 실습 수행 자신감
- 결과 검토 기준
- 자녀/가정 맥락으로 옮겨 설명하는 능력
- 외부 고객 가이드 품질을 판단할 최소 실무 감각

이 계획은 VP를 `전문 개발자`로 만들려는 것이 아니다.
목표는 아래 상태다.

1. VP가 본인 상황에서 AI를 실제로 써본다.
2. 결과의 질을 대략 구분할 수 있다.
3. 초보 고객이 막히는 지점을 언어화할 수 있다.
4. 외부 고객용 가이드의 난이도와 공감도를 더 정확히 판단할 수 있다.
5. 내부 교육 로그를 외부 서비스 설계 자산으로 전환할 수 있다.

### 2.1 설명자료 언어 기준

이 프로그램의 설명자료는 `초등학생이 읽어도 이해할 수 있는 수준`으로 작성되어야 한다.

의미:

- 어려운 단어를 쓰지 않는다.
- 영어 용어를 그대로 던지지 않는다.
- 한 문장에 한 가지 뜻만 담는다.
- 추상 설명보다 눈에 보이는 예시를 먼저 준다.
- "왜 이걸 하는지"를 아주 짧게 설명한다.

금지:

- 설명 없는 영어 전문용어
- 교과서 문장
- 추상 개념만 길게 설명하는 문단
- "대충 이런 뜻"으로 넘기는 표현

권장:

- 짧은 문장
- 실제 화면/버튼/행동 기준 설명
- "지금 할 일 1개"
- "잘 되면 보일 것 1개"
- "막히면 확인할 것 1개"

### 2.2 감성 공감형 예시 기준

VP의 학습 욕구를 끌어올리려면, 설명이 맞는 말이기만 해서는 부족하다.
`내 얘기 같다`, `이건 당장 써먹고 싶다`, `이걸 알면 내 생활이 편해지겠다`는 감정이 먼저 살아나야 한다.

따라서 교육 자료의 예시는 아래 기준을 따른다.

- 가족/자녀/가정 운영 맥락에서 바로 공감되는 장면
- 회사/일상에서 "이거 나도 맨날 하는데" 싶은 장면
- 감정 저항이 큰 순간을 정확히 찌르는 장면
- 작은 성공이 바로 눈에 보이는 장면

예시 우선순위:

1. 자녀 숙제/학습 관리
2. 가족 일정/메시지/정리 부담
3. 일상 문서/메모/답장 작성 스트레스
4. "영어라서 무섭다", "틀릴까 봐 무섭다" 같은 감정 장벽

좋은 예시의 조건:

- 생활 장면이 눈앞에 그려진다.
- 왜 배우고 싶은지 바로 이해된다.
- 5~10분 안에 직접 해보고 싶은 마음이 든다.
- 설명보다 결과 상상이 먼저 된다.

---

## 3. 제품 목표

### 3.0 궁극 목표

이 프로그램의 궁극 목표는 VP가 장기적으로 `CEO의 AI handling 수준`에 최대한 근접하는 것이다.

여기서 말하는 AI handling 수준은 단순 사용 빈도가 아니라 아래를 포함한다.

- 새 도구를 빠르게 익히는 능력
- 적절한 툴을 상황별로 고르는 능력
- 원하는 결과가 안 나올 때 질문/맥락/형식을 바꿔 재시도하는 능력
- 결과물의 품질과 위험을 스스로 판별하는 능력
- 본인 숙련을 타인 교육/서비스 품질 판단으로 연결하는 능력

단, 이 목표는 `장기 북극성(north star)`으로 두고,
단기 운영은 단계형 숙련 사다리로 관리한다.

### 3.1 1차 목표

- VP가 6주 안에 `AI 초보 → guided independent user` 수준으로 이동
- 모바일 입구 + PC/Mac 실습 handoff를 실제로 끝까지 수행
- selected LLM 기준 실습 경로를 안정적으로 이수
- 각 주차별 막힘, 오해, 과부하, jargon friction을 구조화 저장

### 3.2 2차 목표

- 내부 교육 프로그램을 외부 서비스의 `부모 선수과정` 템플릿으로 재사용
- 답변 톤, 과제 난이도, 도구 설치 안내, follow-up cadence를 외부용으로 일반화
- 어떤 구간에서 human review가 필수인지 운영 기준 확보

### 3.2A Phase 1 범위 제한

Copilot 외부 검토 기준 `conditional_block` 해소를 위해,
초기 구현 범위는 의도적으로 좁힌다.

Phase 1에서 실제로 구현하고 검증할 범위:

1. `Week 0 intake`
2. `Week 1 practice`
3. `모바일 → PC/Mac handoff 1개 경로`
4. `primary LLM 1개 경로`

즉, Phase 1은 `모든 주차 완성`이 아니라
`가장 작은 실습형 사다리 1개를 끝까지 살아 있게 만드는 것`이 목표다.

나머지는 Phase 2+로 넘긴다.

### 3.3 비목표

- VP를 코딩 전문가로 훈련하는 것
- 단기간에 모든 LLM/앱을 다루게 하는 것
- 외부 고객 출시 전에 수익화 실험을 억지로 진행하는 것

### 3.4 숙련 사다리

#### Level 0. AI 초보

- 설치/로그인/첫 실행이 불안
- 결과를 읽고도 좋고 나쁨을 구분하기 어려움

#### Level 1. Guided independent

- 안내를 따라 한 가지 툴로 과제를 완수
- 기본적인 재질문과 수정 가능

#### Level 2. Practical operator

- 일상/업무/가정 상황에 맞게 AI를 반복 사용
- 결과 검토와 쉬운 한국어 재서술 가능

#### Level 3. Internal quality lead

- 외부 고객용 가이드의 난이도/허세/실전성을 안정적으로 지적 가능
- selected-LLM별 막힘과 friction을 구조적으로 설명 가능

#### Level 4. CEO-parity target

- 새로운 도구/업데이트에도 빠르게 적응
- 문제 정의, 실행, 검토, 재시도, 전달까지 독립 수행
- AI handling 관점에서 CEO와 유사한 운영 대화를 할 수 있음

현재 6주 프로그램의 직접 목표는 `Level 1→2`, stretch는 `Level 3`이다.
`Level 4`는 후속 심화 트랙까지 포함한 장기 목표로 둔다.

---

## 4. 제품 원칙

### 4.1 부모 우선 원칙

기존 edu 사업의 `부모 먼저, 자녀는 나중` 원칙을 그대로 따른다.
VP 프로그램도 `타인을 지도하기 전 본인이 먼저 체험하고 숙련한다`를 기본으로 한다.

### 4.2 교과서형 과제 금지

과제는 다음 형태를 금지한다.

- 맞는 말이지만 당장 실행이 어려운 조언
- 실습 결과물이 남지 않는 조언
- 고객의 현재 숙련도보다 두세 단계 앞서는 조언
- 영어 전문용어를 설명 없이 밀어넣는 조언

모든 과제는 `5~15분 안에 눈에 보이는 결과물`을 남겨야 한다.

### 4.2A 실습 우선 원칙

이 프로그램은 이론 중심 교육이 아니라 `실습 중심 숙련 프로그램`이어야 한다.

기본 비율:

- `10%` 개념 설명
- `20%` 시범 보기
- `70%` 직접 실행 + 수정 + 재시도

즉, 한 세션에서 설명이 길어지기 시작하면 설계 실패로 본다.

반드시 지켜야 할 기준:

- 매 세션마다 최소 1개의 실제 결과물이 남아야 한다.
- VP가 직접 클릭/입력/실행/수정한 흔적이 있어야 한다.
- "이해했다"는 자기 보고보다 "직접 해냈다"가 더 높은 평가 기준이다.
- 실습 없는 lesson은 완료로 처리하지 않는다.

### 4.3 selected-LLM 기준 가이드

실습은 VP가 선택한 도구를 기준으로 안내한다.

- ChatGPT를 골랐는데 Claude Desktop 기준 안내를 주지 않는다.
- Mac 기준 안내와 iPhone 기준 안내를 섞지 않는다.
- 도구 설치/로그인/첫 실행을 교육 바깥으로 밀어내지 않는다.

### 4.4 외부 서비스와 같은 완성도

이 프로그램은 단순 내부 메모가 아니라 외부 서비스와 같은 기준을 따른다.

- 케이스 중심 저장
- 단계별 평가
- mobile-first 진입
- PC/Mac handoff
- retrieval 근거 기반 가이드
- human review gate
- 운영 로그와 artifact 보존

### 4.5 Harness 미러 환경 원칙

VP의 궁극 목표가 `CEO의 AI handling 수준`에 근접하는 것이라면,
공개 앱 실습만으로는 부족하다.

따라서 교육 과정에는 `현재 Harness project에서 대표가 실제로 사용하는 작업 환경의 축약 미러`가 포함되어야 한다.

여기서 말하는 미러는 production 권한을 그대로 주는 것이 아니라, 다음을 재현하는 안전한 학습 환경이다.

- Mac 또는 PC에서의 실제 작업 흐름
- 여러 LLM 도구를 오가며 쓰는 흐름
- 문서/브라우저/파일/링크를 함께 다루는 흐름
- Harness OS를 열고 상태를 읽고 다음 행동을 정하는 흐름
- 결과물을 보고 수정 지시를 내리거나 직접 고치는 흐름

즉, VP는 `외부 고객용 가이드 사용자`이기도 해야 하지만,
동시에 `Harness 내부 operator의 축약판`도 경험해야 한다.

### 4.6 Harness RAG 적극 활용 원칙

이 프로그램의 교육 자료는 일반 인터넷 검색 결과나 범용 AI 상식 요약에 의존하지 않고,
가능한 한 `현재 Harness OS가 수집·정제·시뮬레이션으로 축적한 edu RAG 자료`를 적극 활용해야 한다.

우선 활용 대상:

- `data/edu_research/*`
- `data/edu_youtube_transcripts/*`
- `evidence_anchors.json`
- customer-facing simulation artifact
- grounded scorer / retrieval evaluator 산출물
- 운영 중 누적된 friction / reflection / case artifact

활용 목적:

1. VP가 최신 고객 고민과 실제 표현을 익히게 한다.
2. 설명자료가 현실과 동떨어진 교과서가 되지 않게 한다.
3. 반복적으로 등장하는 질문과 오해를 corpus 기반으로 반영한다.
4. 외부 서비스와 내부 교육이 같은 지식 자산 위에서 움직이게 한다.

중요:

- 교육 자료는 `RAG를 많이 쓴다`가 목표가 아니라 `실제 도움이 되는 grounded material`이 목표다.
- 근거가 약하거나 rights 경계가 불명확한 자료는 그대로 노출하지 않는다.
- customer-facing 경계가 필요한 자료는 안전 predicate를 통과한 subset만 사용한다.

---

## 5. 제품 정의

### 5.1 제품명 제안

내부명:

- `VP AI 숙련 프로그램`

고객-facing 유사 구조를 염두에 둔 표현:

- `AI 자가점검 + 6주 실습 가이드`

### 5.2 대상

- 1차: VP 본인
- 2차: 대표가 승인한 내부 shadow users
- 3차: 외부 부모 세그먼트 pilot

### 5.2A 두 개의 트랙

이 계획은 아래 두 트랙을 분리해서 운영한다.

#### Track A. Beginner Practice Track

- 목적: VP가 AI 초보자 관점에서 실제 사용을 익히는 것
- 범위: mobile entry, selected-LLM practice, PC/Mac handoff, 쉬운 한국어 자료, 감성 공감형 예시
- 외부 부모 서비스로 직접 재사용 가능한 핵심 자산은 이 트랙에서 주로 나온다

#### Track B. Internal Operator Track

- 목적: VP가 장기적으로 CEO parity에 가까워지도록 Harness operator 감각을 익히는 것
- 범위: Harness 미러 환경, operator toolflow, routing/venv/secret 분리 이해, 운영 화면 읽기
- 본 트랙은 Phase 1에 넣지 않고, Track A baseline 통과 후 심화 단계로만 연다

### 5.3 성공적으로 끝난 상태

VP가 다음을 독립적으로 수행할 수 있어야 한다.

1. 자신의 기기와 선택 툴에서 AI를 실행한다.
2. 좋은 질문과 나쁜 질문의 차이를 설명한다.
3. AI 결과를 그대로 믿지 않고 검토 포인트를 말한다.
4. 자녀/가정 맥락에 맞는 AI 사용 기준 초안을 만든다.
5. 외부 고객용 문구를 보고 `어렵다 / 허세다 / 실전성이 없다`를 구체적으로 지적한다.

---

## 6. 커리큘럼 구조

총 6주를 기본으로 한다.

이 6주는 `CEO 수준 도달의 완성형`이 아니라,
그 수준으로 가기 위한 첫 번째 운영 가능한 사다리다.

### 6.0 Phase 1 실제 구현 단위

문서상 6주 구조와 별개로, 실제 첫 구현 단위는 아래 하나의 slice다.

- `Week 0 intake`
- `Week 1 practice`
- `selected-LLM primary path 1개`
- `mobile → PC/Mac handoff 1개`

이 slice가 안정적으로 돌기 전에는 Week 2~6를 제품 범위로 확장하지 않는다.

### 6.0A 주차별 실습 계약

모든 주차는 아래 4개가 없으면 완료로 보지 않는다.

1. `required_action`
2. `proof_artifact`
3. `pass_fail_rubric`
4. `blocked_at_step`

설명:

- `required_action`: 이번 주에 반드시 직접 해야 하는 한 가지 행동
- `proof_artifact`: 실제로 했음을 보여주는 결과물
- `pass_fail_rubric`: 실행 성공 여부를 판단하는 기준
- `blocked_at_step`: 어디서 막혔는지 남기는 필드

반드시 지키는 원칙:

- reflection은 보조 증거다
- completion의 주 증거는 artifact와 실행 성공이다

### Phase A. Intake + Baseline

목적:

- VP의 현재 기기 환경, 경험 수준, 불안 지점, 선호 툴, 생활 맥락을 구조화

수집 항목:

- 현재 주 사용 기기: iPhone / Android / Mac / Windows
- 현재 AI 사용 경험: 없음 / 가끔 / 주 1회+ / 업무 활용 중
- 가장 큰 불안: 잘 모르겠다 / 틀릴까 무섭다 / 귀찮다 / 영어가 어렵다 / 자녀 교육 기준이 없다
- 선택 LLM: ChatGPT / Gemini / Claude / 아직 모름
- 학습 목표: 본인 업무 / 가정 운영 / 자녀 지도 / 콘텐츠 검토

산출물:

- baseline snapshot
- week 0 readiness score
- personalized starting path
- 첫 실습 환경 확인 결과

실습:

- 선택한 LLM 실행 성공 확인
- 로그인 성공 확인
- 첫 입력 1회 수행
- 결과 복사 또는 저장 1회 수행

### Week 1. AI가 실제로 잘하는 것과 못하는 것

학습 목표:

- 과대평가/과소평가를 동시에 줄인다.

실습 계약:

- `required_action`: 같은 질문을 2가지 방식으로 던지고 직접 재질문해 결과를 개선한다
- `proof_artifact`: 개선 전/후 결과 1건
- `pass_fail_rubric`: VP가 직접 재질문을 1회 이상 수행하고 결과 차이를 저장
- `blocked_at_step`: 입력 / 실행 / 비교 / 저장 중 막힌 단계

실습:

- "아이 숙제 봐주다 답답했던 순간"을 질문으로 바꿔보기
- "단톡방 답장 쓰기 싫었던 순간"을 질문으로 바꿔보기
- 같은 질문을 AI에 두 가지 방식으로 던져 결과 차이 보기
- 좋은 요청과 애매한 요청 비교
- 직접 재질문해서 결과를 개선해 보기

결과물:

- `내가 느낀 AI의 장점 3개`
- `내가 불안한 이유 3개`
- `첫 번째 개선 전/후 결과` 비교 캡처 또는 기록

### Week 2. 내 일상/업무에서 첫 성공 경험 만들기

학습 목표:

- "나도 실제로 쓸 수 있다"는 감각 확보

실습 계약:

- `required_action`: 생활 또는 업무 관련 산출물 1개를 AI로 만들고 직접 수정한다
- `proof_artifact`: 처음 결과 vs 수정 후 결과 1건
- `pass_fail_rubric`: 최종 결과물을 실제로 복사/저장해 남김
- `blocked_at_step`: 질문 / 수정 / 복사 / 저장 중 막힌 단계

실습:

- 아이 학교 준비물/일정 정리
- 선생님/학부모/가족에게 보낼 메시지 초안 작성
- 일정 정리
- 메시지 초안 작성
- 가족/생활 운영 메모 요약
- 결과가 마음에 안 들 때 직접 다시 요청해서 고쳐 보기

결과물:

- 5~10분짜리 실제 산출물 2개
- 불편했던 점 로그
- `처음 결과 vs 수정 후 결과` 1건

### Week 3. AI 결과 검토법 배우기

학습 목표:

- AI 답변을 그대로 믿지 않는 습관 형성

실습 계약:

- `required_action`: AI 답변 1건을 쉬운 한국어로 직접 다시 쓴다
- `proof_artifact`: 원문 / VP 수정문 비교
- `pass_fail_rubric`: 과한 확신 또는 어려운 표현 1개 이상을 직접 고침
- `blocked_at_step`: 읽기 / 판단 / 재작성 중 막힌 단계

실습:

- 과한 확신 표현 찾기
- 근거 없는 일반화 찾기
- 모르는 용어를 쉬운 말로 바꾸기
- 마음에 들지 않는 답변을 VP가 직접 다시 쓰게 만들기

결과물:

- `이 답변이 불안한 이유` 메모
- `쉬운 한국어로 다시 쓰기` 실습
- `원문 / VP 수정문` 비교

### Week 4. 자녀/가정 맥락으로 옮기기

학습 목표:

- 본인 숙련을 가족 리드 언어로 전환

실습 계약:

- `required_action`: 집에서 바로 쓸 수 있는 AI 관련 문장 3개를 만든다
- `proof_artifact`: 가정용 AI 사용 기준 1장
- `pass_fail_rubric`: 실제 생활 문장 3개가 포함됨
- `blocked_at_step`: 초안 / 수정 / 생활문장화 중 막힌 단계

실습:

- "우리 집에서 허용할 AI 사용 / 주의할 AI 사용" 초안
- 자녀에게 할 수 있는 짧은 대화 스크립트 작성
- 실제 집에서 써볼 수 있는 한 줄 멘트 3개 만들기
- "내가 아이에게 화내지 않고 말할 수 있는 표현"으로 바꿔보기

결과물:

- 1페이지 `가정용 AI 사용 기준`
- `오늘 바로 쓸 문장 3개`

### Week 5. 외부 고객 시나리오 리허설

학습 목표:

- 실제 부모 고객 관점에서 friction 감지

실습 계약:

- `required_action`: edu 화면을 직접 써보고 막힌 지점 1개 이상을 표시한다
- `proof_artifact`: VP 리뷰 카드 + confusing step list
- `pass_fail_rubric`: 실제 friction point가 최소 1건 기록됨
- `blocked_at_step`: 진입 / 이해 / 실행 / 이어보기 중 막힌 단계

실습:

- `부모 AI 진단 (1호 파일럿)` 또는 후속 edu 화면을 직접 사용
- 답변의 공감도, 난이도, 실전성 평가
- 본인이 막힌 화면과 문장을 직접 표시

결과물:

- VP 리뷰 카드
- jargon blacklist
- confusing step list
- `내가 여기서 멈춘 이유` 로그

### Week 6. 독립 수행 + 품질 게이트

학습 목표:

- guided use를 넘어 최소 독립 수행

실습 계약:

- `required_action`: 선택한 LLM으로 미니 과제를 완수하고 외부 고객용 가이드 1건을 수정한다
- `proof_artifact`: before/after rewrite sample
- `pass_fail_rubric`: 실행 결과 + 수정 결과를 모두 남김
- `blocked_at_step`: 실행 / 검토 / 수정 / 저장 중 막힌 단계

실습:

- 선택한 LLM으로 실제 미니 과제 완수
- 외부 고객용 가이드 1건 검토
- 검토한 가이드를 쉬운 한국어와 더 실전적인 행동으로 직접 수정

최종 산출물:

- final readiness assessment
- next 30-day growth plan
- external-service transfer note
- before/after rewrite sample

### Post-Program. CEO parity 심화 트랙

6주 종료 후 바로 끝내지 않고, 아래 심화 트랙을 둔다.

1. 새 도구를 스스로 선택하고 온보딩하는 과제
2. 같은 문제를 여러 LLM으로 비교하는 과제
3. 외부 고객 시나리오 3건을 독립 처리하는 과제
4. CEO가 사용하는 AI handling 패턴을 shadowing하는 과제
5. 주간 `CEO 수준과의 gap memo` 작성

즉, 6주 프로그램은 `입문+실전 기초`, 그 이후는 `CEO parity 추격 단계`다.

### Post-Program A. Harness 미러 환경 구축

심화 트랙의 첫 단계는 `VP 개인 작업 환경을 Harness 운영 환경과 부분적으로 미러링`하는 것이다.

필수 구성:

1. VP 전용 Mac/PC 기본 세팅
2. 선택 LLM 2개 이상 로그인 및 실행 가능 상태
3. 파일 다운로드/업로드/정리 기본 동선
4. Harness OS 접속 및 주요 메뉴 사용
5. 문서 읽기 + 링크 열기 + 결과 메모 + 다음 행동 기록 흐름

권장 미러 항목:

- 브라우저 북마크 또는 작업 폴더 구조
- 자주 쓰는 LLM 탭/앱 세트
- Harness OS 진입 링크
- reflection/notes 저장 위치
- 스크린샷/파일 공유 기본 방식

금지:

- 프로덕션 민감 권한을 VP 교육 명목으로 그대로 부여
- 대표 개인 환경을 무차별 복제
- 비밀키/API 키를 평문 공유

운영 원칙:

- 교육용 미러는 `실무 감각을 익히기 위한 최소 안전 환경`이어야 한다.
- 가능하면 read-mostly, low-risk, reversible setup으로 시작한다.
- 필요한 경우 sandbox 또는 shadow account를 쓴다.

### Post-Program A-1. Operator mirror spec

operator mirror는 문구가 아니라 명시적 spec을 가져야 한다.

최소 포함 항목:

1. `mirrored_surfaces`
2. `data_class`
3. `allowed_actions`
4. `banned_actions`
5. `shadow_account_policy`
6. `reset_reprovision_path`

설명:

- `mirrored_surfaces`: 어떤 메뉴/화면/도구를 미러링하는지
- `data_class`: synthetic / shadow / production-adjacent 중 무엇인지
- `allowed_actions`: VP가 눌러도 되는 것
- `banned_actions`: 절대 금지 행동
- `shadow_account_policy`: 어떤 계정으로 접근하는지
- `reset_reprovision_path`: 꼬였을 때 어떻게 원상복구하는지

초기 원칙:

- production write access 금지
- secret 평문 노출 금지
- irreversible command 금지
- synthetic 또는 shadow data 우선

---

## 7. 학습 경험 구조

### 7.1 모바일에서 하는 것

- intake
- 짧은 자가점검
- 주간 과제 확인
- 짧은 reflection 입력
- 이어하기 링크 복구

### 7.2 PC/Mac에서 하는 것

- 실제 툴 설치
- 로그인
- 첫 프롬프트 실습
- 복사/수정/재실행
- 문서형 결과물 작성
- Harness OS 열기 및 상태 읽기
- 교육용 미러 환경에서 결과물 저장/정리

### 7.2A 미러 환경에서 하는 것

VP가 궁극적으로 CEO 수준에 가까워지려면, 아래도 직접 해봐야 한다.

- 여러 도구를 띄운 상태에서 작업 순서 정하기
- Harness OS에서 필요한 정보를 읽고 다음 행동 정하기
- 문서와 실제 실행 결과를 오가며 수정하기
- 결과물을 보고 "이건 고객이 못 따라 한다"를 식별하기

즉, 단일 챗창 실습이 아니라 `도구-문서-운영 화면을 함께 다루는 복합 환경`에 익숙해져야 한다.

### 7.2B RAG 기반 학습 자료에서 하는 것

VP는 단순히 AI 도구를 쓰는 법만 배우는 것이 아니라,
Harness가 이미 모은 자료를 바탕으로 `어떤 설명이 실제 고객에게 먹히는지`도 익혀야 한다.

따라서 학습 자료는 아래 방식으로 제공한다.

- 이번 주 핵심 질문 1~3개
- 그 질문에 연결된 grounded evidence bundle
- 쉬운 한국어로 다시 쓴 설명
- 실제 고객이 막혔던 표현 예시
- VP가 직접 고쳐보는 rewrite 과제

즉, 자료는 `설명문`이 아니라 `evidence + 쉬운 설명 + 직접 수정 과제` 묶음으로 간다.

### 7.2C RAG lineage 계약

RAG 기반 학습 카드나 lesson bundle은 아래 메타를 반드시 함께 가진다.

- `evidence_bundle_id`
- `retrieval_mode`
- `customer_facing_safe`
- `source_version`
- `fallback_used`
- `external_reuse_safe`

설명:

- `evidence_bundle_id`: 어떤 evidence 묶음을 썼는지
- `retrieval_mode`: DB view / fallback index / manual curation 중 무엇인지
- `customer_facing_safe`: 안전 경계 통과 여부
- `source_version`: 어떤 시점/버전 자료인지
- `fallback_used`: 정상 DB retrieval이 아니라 fallback이었는지
- `external_reuse_safe`: 외부 서비스 재사용 가능한지

즉, VP가 보는 학습 자료도 black box가 아니라 lineage가 보여야 한다.

### 7.3 디바이스 handoff 설계

반드시 제공:

- `지금은 휴대폰에서 여기까지`
- `다음 단계는 PC/Mac 권장`
- `내게 이어하기 링크 보내기`
- `지금까지 한 내용 요약`
- `어디서 막혔는지 체크하기`

---

## 8. 데이터 모델

기존 edu case 구조를 최대한 재사용하되, VP training 전용 필드를 추가한다.

### 8.0 canonical state model 원칙

VP 프로그램은 standalone app과 별도의 두 번째 상태기계를 만들면 안 된다.

canonical ownership:

- case progression: `edu_cases`
- device / session / handoff: existing standalone app primitives
- tool readiness: existing standalone app primitives
- training metadata / assessment / artifact: `edu_training_*`

즉, `edu_training_*`는 보조 교육 레이어이지,
케이스 진행과 기기 상태의 canonical owner가 아니다.

### 8.1 재사용 오브젝트

- `edu_customers`
- `edu_cases`
- `edu_case_turns`
- `edu_case_snapshots`
- `edu_case_offers`
- `edu_magic_links`

### 8.2 추가가 필요한 오브젝트

#### `edu_training_plans`

- `id`
- `case_id`
- `track` (`vp_internal`)
- `selected_llm`
- `starting_level`
- `goal_summary`
- `program_version`
- `primary_llm_path`
- `phase_scope`
- `created_at`

#### `edu_training_sessions`

- `id`
- `plan_id`
- `week_no`
- `session_type` (`intake` | `lesson` | `practice` | `assessment`)
- `device_context`
- `required_action`
- `proof_artifact_ref`
- `blocked_at_step`
- `status`
- `started_at`
- `completed_at`

#### `edu_training_artifacts`

- `id`
- `session_id`
- `artifact_type` (`reflection` | `prompt` | `output` | `guide_draft` | `household_rule`)
- `content_json`
- `source_case_snapshot_id`
- `evidence_bundle_id`
- `external_reuse_safe`
- `created_at`

#### `edu_training_assessments`

- `id`
- `plan_id`
- `week_no`
- `rubric_json`
- `pass_flag`
- `pass_reason`
- `reviewer`
- `created_at`

#### `edu_training_friction_events`

- `id`
- `session_id`
- `friction_type` (`install` | `login` | `concept` | `jargon` | `trust` | `handoff` | `tool_mismatch`)
- `severity`
- `note`
- `created_at`

---

## 9. 운영 루프

### 9.1 1주 운영 사이클

1. 주간 lesson 공개
2. VP 실습 수행
3. reflection / artifact 저장
4. friction event 태깅
5. human review
6. 다음 주차 난이도 조정

### 9.2 리뷰 책임

- HR Training Agent: curriculum, assessment, progression
- VP: reflection, comprehension, reader-empathy signal
- Codex: product implementation, logs, evaluation tooling
- CEO: advancement / resourcing / externalization 승인

### 9.3 진급 규칙

- 주차 assessment 미통과 시 다음 주 진입 보류
- 반복 friction은 backlog가 아니라 curriculum defect로 처리
- selected LLM mismatch나 디바이스 mismatch는 immediate fix 대상

---

## 10. 평가 체계

### 10.1 학습 평가

- 개념 이해
- 실제 실행 성공
- 결과 검토 능력
- 쉬운 한국어 재서술 능력
- 자녀/가정 맥락 전환 능력

평가 비중:

- 실행 성공 `50`
- 결과 검토 `20`
- 쉬운 한국어 재서술 `15`
- 생활/가정 맥락 전환 `10`
- 개념 이해 `5`

즉, 개념 점수만 높아도 pass가 될 수 없다.

### 10.2 제품 평가

- 모바일 시작 성공률
- PC/Mac handoff 성공률
- 주간 과제 완료율
- jargon complaint rate
- help-needed rate
- selected-LLM mismatch rate
- session drop-off point
- "해보고 싶다" 반응률
- 감성 공감 예시 선호도
- required_action completion rate
- proof_artifact submission rate
- blocked_at_step concentration

### 10.3 사업 자산 평가

- 외부 서비스로 재사용 가능한 문구 수
- 반복 friction taxonomy 축적량
- reusable prompt/template 품질
- VP review quality improvement

---

## 11. 구현 범위

### Phase 1. Planning + instrumentation

- 프로그램 정의 문서
- data contract 확정
- assessment rubric 설계
- friction taxonomy 설계

### Phase 2. Harness OS internal flow

- 내부 메뉴 추가 또는 기존 edu flow 내부 모드 추가
- VP intake
- session progression
- artifact 저장
- assessment 화면
- mirror environment checklist
- primary LLM 1개 기준 first cohort flow
- mobile→PC/Mac handoff 1개 기준 first cohort flow

### Phase 3. Guidance quality hardening

- selected-LLM별 실습 가이드 분기
- device-specific step guide
- 쉬운 한국어 강제
- answer grounding / safety gate
- Harness 미러 환경 과제 추가

### Phase 3A. Scope expansion 조건

아래가 통과되기 전에는 지원 행렬을 늘리지 않는다.

1. primary LLM 1개 경로 안정화
2. handoff 1개 경로 안정화
3. required_action completion rate 기준 충족
4. blocked_at_step 상위 실패 구간 정리

그 후에만:

- 추가 LLM 경로
- 추가 디바이스 경로
- Track B operator 확장

으로 넓힌다.

### Phase 4. External transfer readiness

- 부모 선수과정으로 일반화
- 법무 카피 정리
- external pilot용 템플릿 분리

---

## 12. 재사용 가능한 핵심 자산

이 프로그램에서 꼭 뽑아내야 하는 재사용 자산:

1. 초보자 jargon blacklist
2. selected-LLM별 onboarding playbook
3. Mac/iPhone handoff checklist
4. "고객이 여기서 멈춘다" friction taxonomy
5. 쉬운 한국어 rewrite examples
6. 외부 부모용 4주 선수과정 skeleton
7. VP review rubric 강화 데이터

---

## 13. 주요 리스크와 사전 완화

### 리스크 1. 내부 교육이 문서 프로젝트로만 끝남

완화:

- 매주 실제 artifact 제출 필수
- session completion / failure를 DB에 남김
- lesson만 만들고 실습이 없으면 실패로 간주

### 리스크 2. 외부 서비스와 분리된 별도 장난감이 됨

완화:

- 데이터 모델을 edu case 계열과 최대한 통합
- selected-LLM, device handoff, reflection 구조를 외부 서비스와 공유
- Track A를 외부 재사용 핵심 트랙으로 명시

### 리스크 3. VP에게 과도한 난이도 부여

완화:

- 5~15분 과제 우선
- 주차당 핵심 행동 1~2개만
- 주차 평가 미통과 시 난이도 rollback
- 미러 환경은 6주 본과정 이후 심화 트랙으로 단계 분리
- Phase 1은 Week 0 + Week 1 + primary path 1개로 제한

### 리스크 3A. 미러 환경 없이 CEO parity를 목표로 해도 실제 handling 수준이 안 오를 위험

완화:

- 심화 트랙에 `Harness 미러 환경 구축`을 명시
- 공개 서비스 UX 실습과 내부 operator 실습을 둘 다 포함
- read-mostly shadow environment부터 시작

### 리스크 3B. practice-first를 말하면서 실제로는 문서/설명 중심으로 흐를 위험

완화:

- 주차별 `required_action`, `proof_artifact`, `pass_fail_rubric`, `blocked_at_step` 강제
- 실행 성공 비중을 가장 높게 평가
- reflection 단독 completion 금지

### 리스크 3C. standalone app과 별도 state machine이 생길 위험

완화:

- case/device/readiness는 기존 standalone app primitives를 canonical owner로 유지
- `edu_training_*`는 training metadata와 artifact/assessment만 담당

### 리스크 3D. RAG를 쓰면서도 lineage가 안 보여 black box가 될 위험

완화:

- 모든 학습 카드에 `evidence_bundle_id`, `retrieval_mode`, `customer_facing_safe`, `fallback_used` 메타 부착
- external reuse 전 `external_reuse_safe` 확인

### 리스크 3E. operator mirror가 unsafe하거나 반대로 너무 fake해질 위험

완화:

- operator mirror spec 명문화
- mirrored_surfaces / data_class / allowed_actions / banned_actions / reset path 사전 확정
- synthetic 또는 shadow data 우선

### 리스크 4. 답변이 다시 허세형/교과서형으로 흐름

완화:

- 쉬운 한국어 기준 고정
- jargon blacklist 운영
- VP reflection에서 `어려웠던 표현`을 강제 수집

### 리스크 5. formal red team / legal / QA 없이 외부 전이

완화:

- 내부 프로그램과 외부 발행을 분리
- 외부 전환 전 `red_team_clear + legal_review_approve + qa_clear` 필수

---

## 14. 게이트

이 문서는 계획서일 뿐이며 곧바로 대외 서비스 출시를 승인하지 않는다.

필수 게이트:

- plan red-team clear
- internal simulation clear
- legal wording review for external reuse
- qa_clear for customer-facing artifacts
- CEO explicit go/no-go

---

## 15. 다음 구현 순서 제안

1. 이 계획서 red-team
2. `vp_internal` track data contract 확정
3. Harness OS 내 VP 프로그램 entry 설계
4. Week 0 intake + Week 1 baseline 구현
5. artifact / assessment 저장
6. week-by-week 운영 후 외부 선수과정 generalization

---

## 16. 성공 정의

이 프로그램이 성공했다는 뜻은 다음과 같다.

- VP가 AI 초보 고객의 막힘을 실제 경험한 뒤 언어화할 수 있다.
- Harness OS 안에 `반복 가능한 내부 교육 제품`이 생긴다.
- 외부 부모 서비스에 재사용 가능한 운영 데이터와 UX 기준이 쌓인다.
- "VP 검수"가 감각 의존이 아니라 실제 훈련과 artifact에 의해 강화된다.
