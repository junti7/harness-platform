# EDU UX RED TEAM — Claude Review

> Reviewer: Claude Sonnet 4.5  
> Date: 2026-06-13  
> Target: EDU_UX_SERVICE_GUIDELINES.md, EDU_STANDALONE_APP_IMPLEMENTATION.md, EDU_SIMULATION_GATING.md  
> Language: Korean

---

## Verdict: **needs_work**

---

## Findings

### 1. [CRITICAL] 다중 기기 세션 충돌 로직이 명세 수준에 머무름

**Why it matters:**

현재 설계는 "동시성 제어를 해야 한다", "충돌을 막아야 한다"고 반복하지만, **어떻게** 막을지 구체적 결정이 없다.

- 같은 케이스를 모바일과 PC에서 동시에 열면 어느 쪽이 read-only가 되는가?
- 마지막 활성 기기가 자동 우선권을 얻는가, 아니면 사용자가 명시적으로 선택해야 하는가?
- 한쪽 기기에서 입력 중일 때 다른 기기에서 열면 경고만 보이는가, 아니면 강제 잠금인가?
- 입력 중이던 내용이 날아가는 상황을 어떻게 방지하는가?
- 웹소켓이나 주기적 polling으로 다른 기기의 활성 상태를 감지하는가?

이 질문에 답이 없으면, 구현자는 "대충 막는다" 방식으로 가게 되고, 실제로는 input loss나 케이스 상태 corruption이 발생한다.

**Recommendation:**

`EDU_STANDALONE_APP_IMPLEMENTATION.md` §4.7에 아래를 명시:
- 세션 우선권 결정 알고리즘 (last active wins / explicit takeover / read-only mode)
- 타임스탬프 기반 충돌 감지 로직
- 경고 UI 흐름도
- 입력 중 데이터 보존 정책
- 구현 기술 (WebSocket, polling interval, server-side lock TTL)

---

### 2. [HIGH] 매직 링크 보안 모델이 "소유자 재확인"과 "즉시 열림" 사이에서 결정 지연

**Why it matters:**

문서는 "민감한 상담은 소유자 재확인이 필요하다"고 하면서도, "Pretotyping에서는 마찰이 늘 수 있다"며 보류를 암시한다.

이는 전형적인 "나중에 고치자" 보안 debt다.

실제 운영에서는 다음 시나리오가 즉시 발생한다:
- 부모가 자녀 상담 링크를 가족 단톡에 실수로 공유
- 노인이 사기범에게 링크를 보냄
- 직장인이 회사 슬랙에 링크를 잘못 붙여넣음

"나중에 추가"는 사고 이후 추가가 된다.

**Recommendation:**

Phase 1부터 최소한의 소유자 확인을 강제:
- 새 기기/브라우저에서 민감 케이스 링크 접근 시, 이메일 뒷 4자리 또는 전화번호 뒷 4자리 재확인
- 같은 브라우저 세션 내에서는 24시간 유예
- 재확인 실패 3회 시 링크 자동 만료 + 운영자 알림

이 정도는 Pretotyping 마찰을 크게 늘리지 않으면서도, IDOR류 노출을 차단한다.

---

### 3. [HIGH] "교과서형 과제 금지" 원칙과 실제 과제 템플릿의 괴리

**Why it matters:**

문서는 "자녀에게 물어보세요"류 과제를 금지한다고 강조하면서도, **대체 과제의 구체적 템플릿이 없다**.

예시는 몇 개 제시되지만 ("Claude에서 중2 체크포인트 5개 만들기"), 이것이:
- 어떤 프롬프트를 복사-붙여넣기하는가?
- 결과물이 부모에게 실제로 "눈이 뜨이는" 느낌을 주는가?
- 다음 단계 행동으로 자연스럽게 이어지는가?

에 대한 검증이 전혀 없다.

결국 구현자는 "교과서형이 아니라는데, 뭘 보여줘야 하지?"로 막힌다.

**Recommendation:**

`docs/education/EDU_REALISTIC_TASK_TEMPLATES.md` 신규 작성:
- 학부모 / 직장인 / 노인 대상별 첫 실습 프롬프트 템플릿 5개 이상
- 각 프롬프트의 기대 출력물 예시
- "눈이 뜨이는" 경험의 정의 (예: "구체적 숫자/이름이 나온다", "바로 써먹을 수 있는 체크리스트다")
- 첫 실습 후 다음 단계로 이어지는 자연스러운 transition

없으면 "교과서형 금지"는 구호로 끝난다.

---

### 4. [HIGH] 디지털 트윈의 "evidence-grounded" 주장과 실제 구현 gap

**Why it matters:**

`EDU_SIMULATION_GATING.md` §2.1은 "맘카페/블로그/유튜브/커뮤니티 발화 패턴을 반영한 evidence-grounded twin"이라고 하지만:

- 어떤 corpus를 수집했는가?
- 몇 건의 발화를 분석했는가?
- 말투, 불안 표현, 이탈 패턴을 어떻게 추출했는가?
- LLM이 그 corpus를 어떻게 소화해 twin을 만드는가?

가 전혀 명시되지 않았다.

"evidence-grounded"는 현재 선언에 불과하다.

실제로는 "40대 학부모라고 하면 대충 이럴 것 같다" 수준의 stereotype twin이 나올 가능성이 높다.

**Recommendation:**

`docs/education/DIGITAL_TWIN_CORPUS_SPEC.md` 작성:
- 수집 대상 source (URL, 커뮤니티명, 기간)
- 최소 corpus 건수 (예: 학부모 발화 500건 이상)
- 추출할 특징 리스트 (어휘, 질문 패턴, 불안 표현, 거부감 신호, 이탈 신호)
- twin 프롬프트에 corpus를 어떻게 주입할지 (few-shot examples, RAG, persona instruction)

없으면 "evidence-grounded"는 마케팅 문구로 끝난다.

---

### 5. [MEDIUM] seeker / target_person 분리 모델의 실제 활용 시나리오 부재

**Why it matters:**

설계는 `seeker`, `target_person`, `goal`을 명확히 분리하고, `edu_case_targets` 테이블까지 준비했다.

하지만:
- 이 분리가 **어떤 화면**에서 **어떻게 보이는가?**
- seeker가 자녀 2명을 동시에 등록하면 어떻게 되는가?
- target이 바뀌면 case가 새로 생성되는가, 같은 case 안에서 target만 전환되는가?
- operator는 seeker와 target을 어떻게 구분해서 보는가?

구체적 흐름이 없다.

결국 "분리 모델을 만들었지만, 실제로는 자녀 1명 기준으로만 작동"하는 절름발이가 될 위험이 크다.

**Recommendation:**

`docs/education/EDU_SEEKER_TARGET_FLOWS.md` 작성:
- seeker/target 선택 화면 wireframe
- target 추가/변경/전환 흐름
- 같은 seeker가 여러 target을 관리하는 시나리오 (예: 중2 자녀 + 고1 자녀)
- operator dashboard에서 seeker-target 관계를 어떻게 시각화하는가

---

### 6. [MEDIUM] LLM 선택 후 분기 가이드의 유지보수 리스크

**Why it matters:**

고객이 Claude/Gemini/ChatGPT 중 하나를 선택하면, 설치/실행/로그인/첫 실습 가이드가 LLM별로 갈라진다.

이는 좋은 원칙이지만, 현실에서는:
- Claude Desktop이 업데이트되어 설치 흐름이 바뀜
- Gemini가 새 앱을 출시
- ChatGPT가 UI를 개편
- 각 LLM의 iOS/Android 앱이 서로 다르게 변화

가 주기적으로 발생한다.

고정 문서로 관리하면 1~2개월 만에 "가이드와 실제 화면이 다르다" 불만이 쌓인다.

**Recommendation:**

- 각 LLM별 가이드를 version-tagged artifact로 관리
- 최신 버전 확인 주기 (월 1회)
- 고객이 "가이드와 다른 화면이 나온다"고 신고할 수 있는 feedback channel
- operator dashboard에 "outdated guide" alert

없으면 "선택한 LLM 기준 가이드"는 곧 legacy 문서가 된다.

---

### 7. [MEDIUM] 도구 준비 상태 추적의 막힘 지점 분류 부족

**Why it matters:**

`edu_tool_readiness_events`는 `blocked_reason`을 저장하지만, 막힘의 **분류 체계**가 없다.

실제로는:
- 앱스토어에서 검색이 안 됨 (지역 제한)
- 다운로드는 됐지만 설치 버튼이 회색
- 설치는 됐지만 아이콘을 못 찾음
- 실행은 됐지만 로그인 화면이 안 뜸
- 로그인은 됐지만 첫 프롬프트 입력창을 못 찾음

처럼 다양한 막힘이 있다.

분류가 없으면 operator는 "많이 막힌다"는 것만 알 뿐, **어디서** 막히는지 모른다.

**Recommendation:**

`docs/education/TOOL_READINESS_BLOCKAGE_TAXONOMY.md` 작성:
- 막힘 지점 분류 (예: `app_not_found`, `download_failed`, `install_blocked`, `icon_not_visible`, `login_ui_confusion`, `first_input_confusion`)
- 각 분류별 표준 대응 안내
- operator dashboard에 막힘 지점별 집계

---

### 8. [MEDIUM] simulation 점수화 기준의 threshold 부재

**Why it matters:**

`EDU_SIMULATION_GATING.md` §5는 점수화 체계를 나열하지만, **몇 점이면 통과인가?**가 없다.

- "시작 성공률" 몇 %가 acceptable인가?
- "혼란 신호 빈도" 몇 회가 너무 많은가?
- "교과서형 처방 비율" 몇 %까지 허용되는가?

기준이 없으면 simulation을 돌려도 "이게 괜찮은 건가?"라는 논쟁만 생긴다.

**Recommendation:**

`docs/education/SIMULATION_PASS_CRITERIA.md` 작성:
- 각 점수 항목별 목표값 (예: 시작 성공률 ≥ 90%, 혼란 신호 ≤ 0.2회/turn, 교과서형 비율 ≤ 10%)
- 치명적 fail 조건 (예: 타인 케이스 노출 1건이라도 발생 시 block)
- needs_work vs clear 경계 정의

---

### 9. [LOW] 카카오 인앱 브라우저 fallback의 실제 테스트 필요

**Why it matters:**

문서는 "카카오 인앱에서 막히면 사파리/크롬으로 열기 fallback"이라고 하지만, 실제로:
- 카카오 인앱에서 "외부 브라우저로 열기" 버튼을 누르면 URL이 유지되는가?
- 링크 토큰이 쿠키에 의존하면 브라우저 전환 시 날아가는가?
- 사용자가 "외부 브라우저"가 뭔지 이해하는가?

이 문제는 수동 테스트로만 확인 가능하다.

**Recommendation:**

- Phase 1에서 카카오 인앱 → 사파리/크롬 전환 시나리오를 실제 iPhone/Android에서 테스트
- URL 파라미터 기반 토큰 전달 방식 확인
- "외부 브라우저로 열기" 안내 문구를 비기술자가 이해 가능한지 검증

---

### 10. [LOW] 결제자와 실제 사용자 분리 시나리오의 구체화 지연

**Why it matters:**

`edu_case_access_guard`는 `payer_customer_id`를 준비했지만, 실제로:
- 남편이 결제하고 아내가 사용
- 자녀가 결제하고 부모가 사용
- 회사가 결제하고 직원이 사용

할 때, **케이스는 누구 소유인가?** **매직 링크는 누구에게 가는가?**

이 질문에 답이 없으면 Phase 3에서 혼란이 온다.

**Recommendation:**

Phase 2에서 payer/user 분리 시나리오의 기본 정책 결정:
- 케이스는 실제 사용자(seeker) 소유
- payer는 결제 이력만 조회 가능
- 매직 링크는 seeker에게만 발송
- payer가 케이스 내용을 볼 수 있는지는 명시적 동의 필요

---

## Open questions

1. **도구 준비 단계가 실패하면 고객은 어디로 가는가?**
   - "Claude Desktop 설치가 안 된다"는 고객에게 대체 경로를 제시하는가? (예: 웹 버전 브라우저로 우회)
   - 아니면 "설치 지원 요청" 티켓을 열게 하는가?

2. **simulation twin은 실제 고객 feedback을 어떻게 반영하는가?**
   - 초기 corpus는 외부 수집이지만, 실제 고객이 생기면 twin도 진화하는가?
   - 아니면 twin은 고정되고, 실제 고객은 별도 분석하는가?

3. **"눈이 뜨이는 경험"의 정량적 정의는 무엇인가?**
   - 첫 실습 후 "유용했다" 평가 비율?
   - 다음 단계로 진행한 비율?
   - paid conversion까지의 시간 단축?

4. **고객이 LLM을 중간에 바꾸면 어떻게 되는가?**
   - Case에 기록된 `selected_llm_for_training`을 변경 가능한가?
   - 변경 시 이전 가이드는 어떻게 처리되는가?

5. **seeker와 target이 모두 노인인 경우는 어떻게 다루는가?**
   - 예: 70대 부부가 서로를 리드하려는 경우
   - 이 시나리오가 digital twin에 포함되는가?

---

## Brief summary

이 설계는 **방향은 옳지만, 구체성이 부족해 구현 시 혼란과 보안 debt를 유발할 위험이 높다**.

특히:
- 다중 기기 세션 충돌 해결 로직이 명세 수준에 머물러 있음
- 매직 링크 보안이 "나중에 추가"로 미뤄져 사고 가능성이 높음
- "교과서형 과제 금지" 원칙과 실제 대체 템플릿 사이에 괴리
- "evidence-grounded twin" 주장과 실제 corpus 준비 사이에 gap
- LLM별 분기 가이드의 유지보수 전략 부재

이 항목들은 **Phase 1 구현 전에** 구체화하지 않으면, 나중에 "이렇게 만들었는데 왜 안 되지?"라는 재작업으로 이어진다.

**Recommendation:** 위 HIGH/CRITICAL findings의 구체적 정책을 먼저 결정하고, 최소 1개 LLM에 대한 실제 가이드 + 막힘 분류 체계를 만든 뒤 Phase 1을 시작해야 한다.

---

**Cross-LLM verification 필요:** 이 리뷰는 Claude 단독 분석이므로, AGENTS.md §3.8 Red Team 규칙에 따라 Gemini 또는 GPT reasoning 모델의 독립 리뷰가 추가로 필요하다.

