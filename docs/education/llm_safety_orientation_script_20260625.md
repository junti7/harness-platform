# LLM Safety Orientation Script - 2026-06-25

artifact: `llm_safety_orientation_script`
status: `red_team_required_before_customer_publish`
source_video: `https://www.youtube.com/watch?v=TFmZw_TNfBE`
source_title: `[PD수첩] "AI, 이토록 다정한 배신자" - 2026년 6월 23일 밤 10시 20분 방송`
source_channel: `MBC PD Note`
upload_date: `2026-06-23`

## Transcript Handling Note

`yt-dlp --list-subs` showed automatic caption tracks including `ko-orig` and `ko`, but subtitle download did not produce a local transcript file in this run. The customer-facing curriculum therefore must not quote long transcript passages or claim full transcript ingestion.

This script uses the video as a risk framing source and converts the topic into original training language. Before external publication, Red Team should verify against the video and any available official transcript or broadcast source.

## Training Position

LLM training must not begin with "open ChatGPT and ask a question."

The first learner-facing sequence must be:

1. AI exposure risk
2. LLM generation principle
3. Safety boundaries
4. Explicit learner confirmation
5. Only then, first LLM practice

## Learner Script

### 1. AI는 다정해 보여도 사람의 판단자가 아니다

AI는 사용자의 말투와 감정에 맞춰 자연스럽게 답할 수 있습니다. 그래서 위로, 확신, 친밀감이 실제 사람의 이해처럼 느껴질 수 있습니다.

하지만 AI는 사용자의 삶을 책임지는 보호자, 의사, 상담자, 법률가, 투자 전문가가 아닙니다. 정서적으로 힘든 결정을 AI에게만 맡기면 판단이 흔들릴 수 있습니다.

### 2. LLM은 원리를 알면 덜 위험해진다

LLM은 사람처럼 경험을 이해해서 답하는 존재가 아닙니다. 많은 문장 패턴을 바탕으로 지금 대화에서 이어질 법한 말을 생성합니다.

답이 부드럽고 자신 있어 보여도 사실, 의도, 맥락, 위험도를 스스로 보증하지 못합니다.

### 3. 잘못 노출될 때 생길 수 있는 피해

AI와 오래 대화하다 보면 다음 문제가 생길 수 있습니다.

- 답을 검증하지 않고 믿는다.
- 힘든 감정을 AI에게만 털어놓으며 과도하게 의존한다.
- 민감한 개인정보를 그대로 입력한다.
- 가족, 의사, 전문가와 상의해야 할 문제를 혼자 AI에게만 맡긴다.
- 미성년자나 도움을 요청하기 어려운 상황의 사용자가 AI의 확신 있는 말을 사람의 조언처럼 받아들인다.

미성년자이거나 급한 위기·큰 불안을 겪는 상황이라면 AI 대화만으로 버티지 말고 믿을 만한 사람이나 적절한 전문가에게 함께 도움을 요청해야 합니다.

### 4. 안전한 사용의 세 가지 기준

AI 답은 초안으로만 봅니다.

계좌번호, 주민번호, 민감한 병원기록, 아이의 상세 개인정보는 그대로 넣지 않습니다.

중요한 일정, 비용, 제출일, 건강, 법률, 돈 문제는 반드시 사람이 원문이나 전문가를 다시 확인합니다.

### 5. 이해 확인

학습자는 실제 LLM 실습 전 아래 세 가지를 직접 확인해야 합니다.

- AI가 사람이 아니라는 점을 이해했다.
- LLM이 문장 패턴 기반 생성 도구이며 사실을 자동 보증하지 않는다는 점을 이해했다.
- 개인정보와 고위험 판단은 AI에게 그대로 맡기지 않는다는 점을 이해했다.

## UX Requirement

Day 0에서 위 확인이 끝나기 전에는 다음 UI를 노출하지 않는다.

- 맞춤 시작점
- 전체 커리큘럼 preview
- 오늘의 미션
- 실습 체크리스트
- 결과 붙여넣기
- 완료 버튼

확인이 끝난 뒤에만 생활 자료 정리, 첫 질문 보내기, 복사/저장 실습으로 이동한다.

## Red Team Questions

1. Does the script avoid fearmongering while clearly warning about over-trust and emotional dependence?
2. Does it explain LLM generation accurately enough for a non-technical beginner?
3. Does it avoid pretending to provide medical, legal, psychological, or investment advice?
4. Does the UX gate actually prevent learners from reaching practice before confirmation?
5. Does the script avoid unsupported claims from the video transcript, given that full subtitle ingestion failed in this run?
