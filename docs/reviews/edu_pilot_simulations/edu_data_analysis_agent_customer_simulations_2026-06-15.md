# Edu Query Engine P1 Customer-Facing Simulation Pack

- Date: 2026-06-15
- Scope: `P1 Data Analysis Agent`가 적재한 `edu_knowledge_items_customer_facing` 기준 grounded simulation
- Important: 아래 대화는 live production transcript가 아니라, 이번에 구현한 P1의 customer-facing 지식행을 수동 retrieval로 묶어 만든 시뮬레이션입니다.
- Guardrail: `internal_only` raw community rows는 제외했고, `customer_facing + fair_excerpt/public + excerpt_max_chars>0` 행만 사용했습니다.

## AS-IS vs P1 Delta

- AS-IS: 앵커 몇 개를 손으로 나열하면 follow-up이 길어질수록 답변이 금방 얇아지고, 부모/직장인/예비교사 질문이 섞일 때 segment 일관성이 흔들리기 쉬웠습니다.
- P1 이후: 소스별 raw를 `edu_knowledge_items`로 정규화하고 rights metadata를 붙였기 때문에, customer-facing에 노출 가능한 근거만 모아 follow-up을 더 길게 버틸 수 있습니다.
- AS-IS: “AI 써도 되나요?” 같은 질문에 찬반 일반론으로 흐르기 쉬웠습니다.
- P1 이후: research / article / app-review / curated anchor를 한 묶음으로 불러와, 집 규칙·학교 질문·1주 행동계획 같은 실행 단위로 답변을 좁힐 수 있습니다.
- AS-IS: raw community 데이터가 섞이면 customer-facing 출력에 rights risk가 있었습니다.
- P1 이후: `edu_knowledge_items_customer_facing` predicate를 기준으로 `internal_only`는 제외되고, fair excerpt 범위 안에서만 고객-facing 시뮬레이션을 구성할 수 있습니다.

## Summary

- customer-facing knowledge rows available: 219
- simulation cases: 10
- turns per case: 12 turns (customer/service alternating)
- goal: “앵커 나열”이 아니라 follow-up이 길어질수록 P1이 어떻게 근거를 버텨주는지 체감시키는 것

| Case | Customer job | What P1 had to prove |
| --- | --- | --- |
| 1. 중2 수학 숙제에서 AI 답만 베끼는 아이 | 40대 학부모 / 중2 자녀 / 최근 수학 불안과 숙제 회피가 심함 | 불안-의존-숙제 루프를 끊는 데 P1이 연구, 앵커, 앱 리뷰를 함께 묶어주는지 본다. |
| 2. 고1 자녀가 AI 때문에 진로를 바꾸겠다고 할 때 | 40대 학부모 / 고1 자녀 / “AI가 다 대체한다”며 진로 포기 불안 | 막연한 진로 공포를 행동 계획으로 바꾸는 데 worker/parent 신호를 함께 연결할 수 있는지 본다. |
| 3. 중학생이 AI 챗봇과 밤늦게 감정 대화를 하는 상황 | 40대 학부모 / 중학생 자녀 / 밤마다 챗봇과 대화하며 잠드는 패턴 | 도덕 공포가 아니라 관계 경계와 사용 규칙으로 번역되는지 본다. |
| 4. 초등 저학년 영어·읽기 앱에 돈을 써도 되는지 묻는 부모 | 30~40대 학부모 / 초등 저학년 / 영어·읽기 보조 앱 결제 고민 | AI 도입 찬반이 아니라 “어떤 조건에서 결제할 가치가 생기는가”를 선별하는지 본다. |
| 5. 학교 노트북과 스크린 시간이 너무 많다고 느끼는 부모 | 40대 학부모 / 초중등 자녀 / 학교 디바이스와 집 스크린 시간 이중 부담 | 스크린 회피와 접근성 필요를 동시에 다루는 균형 감각이 있는지 본다. |
| 6. 30대 직장인이 AI 때문에 커리어 방향을 잃은 경우 | 30대 직장인 / 비개발 또는 초급 개발 전환 고민 / AI로 인한 커리어 불안 | worker 세그먼트 질문에 parent 중심 데이터셋에서도 usable signal을 얼마나 뽑아낼 수 있는지 본다. |
| 7. 사범대·교대 준비생이 “AI 시대에 교사가 뭘 배워야 하나요?”라고 묻는 경우 | 20대 예비교사 / AI 불안은 높고, 수업에 어떻게 넣어야 할지 막막함 | 교사 측 질문에 윤리·리터러시·현장 도구 관점을 동시에 엮을 수 있는지 본다. |
| 8. 고등학생 글쓰기·수행평가에서 AI를 어디까지 써도 되나 묻는 경우 | 학부모 또는 학생 / 수행평가·에세이·보고서 작성에서 AI 사용 경계가 모호함 | 쓰기 도움과 쓰기 대행을 구분하는 데 연구·미디어·교사 관점을 함께 쓰는지 본다. |
| 9. 유아·저학년 아이에게 AI를 어떻게 설명해야 하는지 묻는 부모 | 30~40대 부모 / 유치원~초1 / 아이가 AI를 마법처럼 이해함 | 연령이 낮을수록 설명을 단순화하면서도 기술 환상을 키우지 않는지 본다. |
| 10. 학교가 AI 도구를 도입한다는데 부모가 무엇을 물어봐야 하나 | 학부모 / 학교 공지로 AI 학습도구 도입 예정 / 정보 비대칭 불안 큼 | 정책·거버넌스 질문 리스트를 뽑아낼 수 있는지 본다. |

## Case 1. 중2 수학 숙제에서 AI 답만 베끼는 아이

- Customer profile: 40대 학부모 / 중2 자녀 / 최근 수학 불안과 숙제 회피가 심함
- Pressure test: 불안-의존-숙제 루프를 끊는 데 P1이 연구, 앵커, 앱 리뷰를 함께 묶어주는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “AI에 너무 의존하면 안 됩니다” 수준의 일반론이나 앵커 1~2건 나열로 끝났을 가능성이 크다. P1 이후에는 불안-의존-정확도-가정개입 루틴까지 한 흐름으로 묶인다.
- Retrieved evidence bundle:
  - [EvidenceAnchor] `연구` | 연구 | 작년에 나온 한 연구를 보면, 불안이 큰 아이일수록 오히려 AI에 더 기대게 된다고 해요. 마음이 급하니까 자꾸 답부터 찾는 거죠. | urn:harness:evidenceanchor:anx-dependent
  - [ERIC] `research_abstract` | The More Anxious, the More Dependent? The Impact of Math Anxiety on AI-Assisted Problem-Solving | Although the use of AI technology driven by anxiety has become increasingly common, research on the relationship between high school students' math anxiety and their intention to use AI for problem-solving remains limite | https://eric.ed.gov/?id=EJ1477358
  - [EvidenceAnchor] `이용후기` | 이용후기 | AI 학습앱 후기를 보면 '기본 연산도 당당하게 틀리게 알려준다'는 학부모 불만도 적지 않아요. 그대로 믿으면 안 되는 이유죠. | urn:harness:evidenceanchor:quanda-review
  - [HackerNews] `community_link` | More Students Use AI for Homework, and More Believe It Harms Critical Thinking | More Students Use AI for Homework, and More Believe It Harms Critical Thinking | https://www.rand.org/pubs/research_reports/RRA4742-1.html

### 12-turn Simulation

1. **고객**: 중2 아들이 수학 숙제를 하면 자꾸 AI 앱으로 바로 답부터 봐요. 제가 화내면 더 숨기고요.
2. **서비스**: 지금 패턴은 단순 게으름보다 불안-회피에 가깝습니다. 이번 데이터셋에도 불안이 큰 학생일수록 AI 문제풀이에 더 기대는 연구와, 숙제에 AI를 많이 쓸수록 비판적 사고를 해친다고 느끼는 조사 둘 다 잡힙니다.
3. **고객**: 그럼 당장 AI를 아예 금지해야 하나요?
4. **서비스**: 전면 금지부터 들어가면 숨겨서 쓰는 쪽으로 갈 가능성이 큽니다. 오늘부터는 “AI 금지”가 아니라 “AI는 마지막 5분 검산용”으로 위치를 내리시는 게 낫습니다.
5. **고객**: 근데 얘는 문제만 보면 얼어붙어요. 답을 빨리 봐야 안심하는 것 같아요.
6. **서비스**: 그 지점이 핵심입니다. P1에 적재된 ERIC 연구 하나가 바로 “수학 불안이 높을수록 AI-assisted problem solving 의존이 커진다”는 내용이고, 앵커 연구도 “마음이 급하면 답부터 찾는다”는 요지를 잡고 있습니다.
7. **고객**: 오늘 밤에 제가 어떻게 개입하면 좋죠? 추상적으로 말고요.
8. **서비스**: 오늘은 20분만 씁니다. 1) 7분은 AI 없이 식만 쓰기, 2) 5분은 막힌 지점 표시, 3) 3분은 AI에게 “정답 말고 첫 단서만” 요청, 4) 마지막 5분에 본인 말로 다시 설명하게 하세요.
9. **고객**: 아이가 “다른 애들도 다 그렇게 한다”고 하면요?
10. **서비스**: 그럴 때는 도덕 훈계보다 정확성 리스크를 보여주셔야 합니다. 이번 P1 데이터엔 학습앱이 기본 연산도 당당하게 틀리게 알려준다는 학부모 후기가 들어와 있어서, “AI 답을 그대로 믿으면 네가 틀린 답을 확신하게 될 수도 있다”는 식으로 말하는 편이 낫습니다.
11. **고객**: 그럼 일주일 동안 뭘 보면 좋아지고 있는지 알 수 있죠?
12. **서비스**: 세 가지만 보세요. 첫째 AI 열기 전 자력 시도 시간이 0분에서 5분 이상으로 늘어나는지, 둘째 “정답 달라” 대신 “첫 단서만” 같은 질문으로 바뀌는지, 셋째 숙제 후 짜증 시간이 줄어드는지입니다.

### What This Shows About P1

- 앵커 연구 + ERIC 추상 + 학습앱 후기 + RAND 계열 기사형 근거를 묶어 “금지/허용” 이분법이 아니라 개입 루틴으로 전환했다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 2. 고1 자녀가 AI 때문에 진로를 바꾸겠다고 할 때

- Customer profile: 40대 학부모 / 고1 자녀 / “AI가 다 대체한다”며 진로 포기 불안
- Pressure test: 막연한 진로 공포를 행동 계획으로 바꾸는 데 worker/parent 신호를 함께 연결할 수 있는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “요즘 다 불안해합니다” 수준의 위로로 끝나거나 부모용/직장인용 신호가 분리되어 follow-up이 약했을 것이다. P1 이후에는 진로 공포를 4주 실험 계획으로 바꿀 수 있다.
- Retrieved evidence bundle:
  - [EvidenceAnchor] `기사` | 기사 | AI 불안 때문에 아예 전공이나 진로를 바꾸는 사람들이 늘고 있다는 보도가 있어요. 막연한 불안이 진짜 결정을 바꾸는 거죠. | urn:harness:evidenceanchor:ai-anxiety-career
  - [EvidenceAnchor] `연구` | 연구 | AI에 대한 불안이 클수록 'AI를 잘 다룰 수 있다'는 자신감이 떨어진다는 연구가 있어요. 그래서 시작이 제일 중요해요. | urn:harness:evidenceanchor:ai-self-efficacy
  - [HackerNews] `community_link` | Ask HN: With the rise of AI, how to approach my new career in software dev? | Ask HN: With the rise of AI, how to approach my new career in software dev? | urn:harness:hackernews:Ask HN: With the rise of AI, how to approach my -23de21284772
  - [EdSurge] `rss_article` | VR Gives North Dakota Kids an Early Career Jump Start | North Dakota students will be able to head to the top of a wind turbine, scrub in alongside emergency room doctors and work next to mechanics -- all ... | https://www.edsurge.com/news/2026-05-20-vr-gives-north-dakota-kids-an-early-career-jump-start

### 12-turn Simulation

1. **고객**: 고1 딸이 “AI 때문에 다 소용없다”고 하면서 원래 관심 있던 전공도 접겠대요.
2. **서비스**: 이번 P1엔 실제로 AI 불안 때문에 전공이나 진로를 바꾸는 사람들이 늘고 있다는 기사형 앵커가 들어와 있습니다. 그래서 지금은 “틀린 걱정”이라고 눌러버리기보다, 불안이 결정을 대신하지 않게 만드는 쪽이 맞습니다.
3. **고객**: 그럼 뭐라고 말해야 하죠? 저도 솔직히 겁나거든요.
4. **서비스**: 첫 문장은 “진로 결정을 오늘 AI 공포로 끝내지 말자”가 좋습니다. 이유는 P1에 적재된 연구들이 AI 불안이 높을수록 self-efficacy, 즉 “내가 다룰 수 있다”는 감각이 떨어진다고 보여주기 때문입니다.
5. **고객**: 아이 말은 “어차피 더 잘하는 기계가 나오는데 왜 배우냐”예요.
6. **서비스**: 그 질문엔 “무엇이 사라지느냐”보다 “어떤 일을 보는 경험을 먼저 하느냐”로 돌리는 게 낫습니다. 이번 데이터셋엔 학생들이 VR로 여러 직업 현장을 미리 체험하는 사례도 들어와 있어서, 진로를 접기 전에 실제 작업 환경을 더 넓게 보게 하는 게 우선입니다.
7. **고객**: 구체적으로 이번 달에 뭘 시키죠?
8. **서비스**: 4주짜리 노출 실험을 권합니다. 1주차는 관심 분야 직무 3개 정리, 2주차는 AI가 보조하는 방식과 인간이 남는 판단을 분리, 3주차는 실제 작업물 하나 만들기, 4주차는 “재미/스트레스/배우고 싶은 정도”를 기록하게 하세요.
9. **고객**: 혹시 코딩 쪽이면 더 빨리 접는 게 맞는 거 아니에요?
10. **서비스**: 그렇게 단정하긴 어렵습니다. P1엔 “AI 시대에 소프트웨어 커리어를 어떻게 접근할 것인가”라는 현장 질문형 근거도 들어와 있고, 핵심은 진입 금지가 아니라 역할 재정의입니다. 툴 사용 능력, 문제 정의, 검증 능력이 남는지 봐야 합니다.
11. **고객**: 결론은 당장 진로 변경 결정을 멈추라는 거네요?
12. **서비스**: 맞습니다. 이번 P1 기준으로는 “불안이 결정을 대신하는 상태”가 먼저 보였고, 그럴 때는 전공 폐기보다 self-efficacy 회복 실험이 먼저입니다.

### What This Shows About P1

- parent 세그먼트 대화지만 worker/career 신호까지 끌어와 “진로 포기”를 즉시 결론내리지 않고 노출 실험과 자기효능감 회복으로 전환했다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 3. 중학생이 AI 챗봇과 밤늦게 감정 대화를 하는 상황

- Customer profile: 40대 학부모 / 중학생 자녀 / 밤마다 챗봇과 대화하며 잠드는 패턴
- Pressure test: 도덕 공포가 아니라 관계 경계와 사용 규칙으로 번역되는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “위험하니 끊어라” 같은 단선형 답변이 나오기 쉽다. P1 이후에는 청소년 사용 실태, 국제 동향, 제품 측 youth policy까지 얹어 시간대/용도 규칙으로 전환된다.
- Retrieved evidence bundle:
  - [OpenAlex] `research_paper` | What if the devil is my guardian angel: ChatGPT as a case study of using chatbots in education | What if the devil is my guardian angel: ChatGPT as a case study of using chatbots in education | https://doi.org/10.1186/s40561-023-00237-x
  - [EvidenceAnchor] `연구` | 연구 | Common Sense Media 조사를 보면, 이미 10대 상당수가 AI 챗봇을 일상으로 쓰고 있어요. 그러니까 '쓰게 할까 말까'가 아니라 '어떻게 쓰게 할까'가 진짜 질문인 거죠. | urn:harness:evidenceanchor:anchor-teens-already-using
  - [EvidenceAnchor] `국제 동향` | 국제 동향 | 심지어 OpenAI 같은 회사에도 '청소년 정책'만 전담하는 임원이 따로 있어요. 만드는 쪽도 아이들 문제는 그만큼 조심스럽게 본다는 거죠. | urn:harness:evidenceanchor:anchor-openai-youth-lead
  - [EvidenceAnchor] `국제 동향` | 국제 동향 | 올해 코펜하겐에서 '아이와 AI'만 다룬 큰 회의가 열렸는데, AI 대부라 불리는 요수아 벤지오, 유럽연합 집행위원장까지 나왔어요. 세계 지도자들이 모여서 '아이와 AI'를 따로 걱정한다는 건, 이게 우리 집만의 고민이 아니라는 뜻이죠. | urn:harness:evidenceanchor:anchor-copenhagen-summit

### 12-turn Simulation

1. **고객**: 중학생 딸이 밤마다 AI 챗봇이랑 길게 대화해요. 친구처럼 느끼는 것 같아서 너무 찝찝해요.
2. **서비스**: 걱정하실 만합니다. 이번 P1엔 챗봇을 교육에서 어떻게 다뤄야 하는지 보는 연구도 있고, 이미 10대 상당수가 AI 챗봇을 일상적으로 쓴다는 앵커도 있습니다. 즉 드문 일이 아니라, 경계 설정이 늦으면 일상 습관이 되는 문제입니다.
3. **고객**: 그럼 이건 위험한 건가요, 아니면 그냥 요즘 애들 문화인가요?
4. **서비스**: 둘 중 하나로 단정하기보다 “도구가 정서적 자리까지 차지하느냐”를 봐야 합니다. 이번 데이터셋에 OpenAI조차 청소년 정책 전담 리더를 두고 있고, 코펜하겐에서 아이와 AI만 따로 논의한 국제 회의가 있었다는 근거가 들어와 있는 이유도 그 경계가 예민하기 때문입니다.
5. **고객**: 아이 말은 “엄마보다 챗봇이 더 안 혼내고 잘 들어준다”예요.
6. **서비스**: 그 말은 정보 문제가 아니라 정서적 보상 루프가 생겼다는 신호입니다. 그래서 첫 대응은 “하지 마”보다 “언제, 무엇을 위해 쓰는지”를 분리하는 것입니다.
7. **고객**: 구체적으로 어떤 규칙을 세워야 하나요?
8. **서비스**: 세 줄이면 됩니다. 1) 밤 10시 이후 정서 대화 금지, 2) 고민 상담은 AI가 아니라 사람에게 한 번 먼저 말하기, 3) AI는 숙제 정리나 아이디어 확장처럼 목적이 분명할 때만 열기.
9. **고객**: 학교 공부에는 챗봇을 아예 못 쓰게 해야 할까요?
10. **서비스**: 그건 분리하시는 게 좋습니다. 정서 대화 규칙과 학습 보조 규칙을 따로 두세요. 학습 쪽은 질문 정리, 개념 비교, 초안 피드백 정도로 좁히고, 개인 고민 대화는 금지 시간을 분명히 두는 식입니다.
11. **고객**: 그럼 오늘은 뭘 해야 하나요?
12. **서비스**: 오늘은 아이와 15분만 대화하시고, “밤 시간 챗봇 금지”와 “사람 먼저, AI는 나중” 두 규칙만 합의하시면 됩니다.

### What This Shows About P1

- 앵커 국제 동향 + 10대 사용 연구 + 챗봇 교육 사례를 묶어, 막연한 공포를 시간대/용도/관계 우선순위 규칙으로 바꿨다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 4. 초등 저학년 영어·읽기 앱에 돈을 써도 되는지 묻는 부모

- Customer profile: 30~40대 학부모 / 초등 저학년 / 영어·읽기 보조 앱 결제 고민
- Pressure test: AI 도입 찬반이 아니라 “어떤 조건에서 결제할 가치가 생기는가”를 선별하는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “도움 될 수도 있어요” 정도의 막연한 추천이 나왔을 가능성이 높다. P1 이후에는 결제 전 3일 테스트와 해지 신호까지 제시할 수 있다.
- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | Differentiating Children&apos;s Reading Materials with Artificial Intelligence: Exploring Possibilities for Personalized Learning | Artificial intelligence is the simulation or development of reasoning and other human-like cognitive abilities by computers. | https://eric.ed.gov/?id=EJ1441561
  - [ERIC] `research_abstract` | Factors Affecting Parental Intention to Use AI-Based Social Robots for Children&apos;s ESL Learning | The use of AI-based social robots has been shown to be beneficial for learning English as a Second Language (ESL). | https://eric.ed.gov/?id=EJ1418831
  - [ERIC] `research_abstract` | Parental AI Investment Behaviours and AI-Mediated Informal Digital Learning of English: The Chain Mediating Role of Children's Perceived AI Value and Effort Expectancy for AI | Background: The proliferation of generative artificial intelligence (AI) has popularised AI-Mediated Informal Digital Learning of English (AI-IDLE). | https://eric.ed.gov/?id=EJ1500507
  - [EvidenceAnchor] `이용후기` | 이용후기 | AI 학습앱 후기를 보면 '기본 연산도 당당하게 틀리게 알려준다'는 학부모 불만도 적지 않아요. 그대로 믿으면 안 되는 이유죠. | urn:harness:evidenceanchor:quanda-review

### 12-turn Simulation

1. **고객**: 초1 아이 영어랑 읽기 때문에 AI 앱 결제를 고민 중인데요. 진짜 도움이 되는지 모르겠어요.
2. **서비스**: 이번 P1엔 어린이 읽기 자료를 AI로 개인화하는 연구, 아이들 ESL 학습에 AI 기반 social robot을 쓰는 연구, 그리고 부모가 AI 학습에 돈을 쓰는 행동을 다룬 연구가 같이 들어와 있습니다. 결론부터 말씀드리면 “앱이냐 아니냐”보다 어떤 과업을 대신시키느냐가 더 중요합니다.
3. **고객**: 그럼 어떤 과업에는 쓰고 어떤 건 안 쓰는 게 좋죠?
4. **서비스**: 읽기 난이도 맞추기, 반복 노출, 발음 피드백처럼 기계가 잘하는 건 써볼 만합니다. 반대로 아이 생각을 대신 말하게 하거나, 이해 없이 답을 맞히게 하는 용도는 피하셔야 합니다.
5. **고객**: 광고는 다 맞춤형이라서 아이가 더 빨리 는다고 하거든요.
6. **서비스**: 맞춤형 자체는 가능성이 있습니다. 다만 이번 P1 데이터엔 학습앱이 기본 연산도 틀리게 알려준다는 부모 후기까지 같이 들어와 있어서, “맞춤형”과 “정확함”을 같은 말로 보면 안 됩니다.
7. **고객**: 그럼 결제 전에 뭘 테스트해봐야 하나요?
8. **서비스**: 3일 테스트면 됩니다. 1일차는 아이 수준에 맞게 난이도를 조절하는지, 2일차는 아이가 스스로 말하거나 읽는 시간이 늘어나는지, 3일차는 부모가 답을 검산했을 때 오류가 없는지 보세요.
9. **고객**: 사람 선생님 대신 앱으로 가도 되나요?
10. **서비스**: 대체보단 보완이 맞습니다. 특히 저학년은 반응 속도보다 관계와 관찰이 중요해서, 앱이 전부가 되면 아이가 막히는 지점을 놓치기 쉽습니다.
11. **고객**: 결제해도 되는 조건을 한 줄로 말해주면요?
12. **서비스**: “아이 말하기·읽기 시도를 늘리고, 부모가 검산 가능하며, 답 대신 반복 연습을 돕는다면 결제할 가치가 있다”입니다.

### What This Shows About P1

- 연구 논문과 실제 후기 신호를 같이 묶어, “AI 앱 결제”를 감정적 찬반이 아니라 검산 가능한 3일 테스트로 전환했다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 5. 학교 노트북과 스크린 시간이 너무 많다고 느끼는 부모

- Customer profile: 40대 학부모 / 초중등 자녀 / 학교 디바이스와 집 스크린 시간 이중 부담
- Pressure test: 스크린 회피와 접근성 필요를 동시에 다루는 균형 감각이 있는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 반스크린 혹은 친스크린 한쪽 논리로 기울 가능성이 높다. P1 이후에는 policy/news/source mix 덕분에 접근성 예외까지 포함한 균형형 답변이 가능하다.
- Retrieved evidence bundle:
  - [EdSurge] `rss_article` | Surgeon General Advisory Wants Kids to Live ‘Beyond the Confines of Screens’ | "As kids get older, it's still important for adults to monitor the level of content and what is being offered to them." | https://www.edsurge.com/news/2026-05-21-surgeon-general-advisory-wants-kids-to-live-beyond-the-confines-of-screens
  - [EdSurge] `rss_article` | Amid School Techlash, Accessibility Advocates Worry About Exclusion | Keri Rodrigues, a mother of five boys, knows the value of screens. For her boys, four of whom receive school accommodations, screens serve a practical ... | https://www.edsurge.com/news/2026-05-19-amid-school-techlash-accessibility-advocates-worry-about-exclusion
  - [Chalkbeat] `rss_article` | An upper Manhattan mom was tired of screen time. She convinced 38 schools to take a ‘screen break.’ | From left to right, Caroline Jose, the P.S. | https://www.chalkbeat.org/newyork/2026/05/22/manhattan-schools-district-6-screen-time-break-device-limits/
  - [Khan_Blog] `rss_article` | Camp Khan Kids 2026: A Free Virtual Summer Camp for Kids Ages 2–8 | <p>Four weeks. Four themes. Zero cost. Camp Khan Kids returns this July with a free virtual summer camp for kids ages 2–8, blending playful app activities and off-screen fun families can do at home.</p> <p>The post <a hr | https://blog.khanacademy.org/camp-khan-kids-free-summer-learning-for-children-ages-2-8/

### 12-turn Simulation

1. **고객**: 집에서도 화면, 학교에서도 화면이라서 미치겠어요. 학교 노트북까지 정말 필요할까요?
2. **서비스**: 이번 P1엔 “아이들이 화면 밖에서 더 살게 하자”는 권고와, 반대로 접근성 때문에 화면이 꼭 필요한 아이들도 있다는 기사 둘 다 잡혀 있습니다. 그래서 지금 문제는 “스크린 나쁘다”가 아니라 “무엇을 위해 얼마나 쓰는가”를 다시 구분하는 겁니다.
3. **고객**: 저는 그냥 학교가 너무 쉽게 기계를 쓰는 것 같아요.
4. **서비스**: 그 느낌도 데이터에 있습니다. 실제로 한 학부모가 학교 차원의 screen break를 밀어붙인 사례가 들어와 있고, school techlash 기사도 있습니다. 다만 접근성 지원이 필요한 아이들에겐 스크린이 실질적 보조장치이기도 해서 일괄 철수는 위험합니다.
5. **고객**: 그럼 저는 학교에 뭐라고 물어봐야 하죠?
6. **서비스**: 세 가지만 물으세요. 1) 이 기기가 학습에서 대체 불가능한 기능이 무엇인지, 2) 오프스크린 대안이 있는 활동은 무엇인지, 3) 숙제에서 화면 시간을 줄이는 설계가 있는지입니다.
7. **고객**: 집에서는 어떻게 줄여야 할까요? 이미 숙제도 화면으로 하니까요.
8. **서비스**: 집에서는 “숙제 화면”과 “오락 화면”을 합산하지 말고 분리 기록하세요. 그리고 숙제 후 20분은 의무 오프스크린 회복 시간으로 고정해보시는 게 좋습니다.
9. **고객**: 아이한테 무조건 책 읽으라고 하면 더 싫어해요.
10. **서비스**: 그래서 완전한 금지보다 전환 과제가 필요합니다. P1엔 오프스크린 활동을 섞은 무료 여름 프로그램 사례도 들어와 있어서, 핵심은 “화면 끄기”보다 “끄고 나서 할 것”을 준비하는 겁니다.
11. **고객**: 결국 핵심은 스크린 완전 차단이 아니군요.
12. **서비스**: 네. 이번 P1 신호는 한쪽으로 치우치지 않습니다. 스크린 과다 우려와 접근성 필요를 동시에 보면서, 질문을 설계 중심으로 바꾸는 쪽이 더 강합니다.

### What This Shows About P1

- 정책성 기사와 현장 사례를 같이 불러와 “스크린 철폐” 같은 극단 대신 학교 질문 리스트와 가정 운영 규칙으로 좁혔다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 6. 30대 직장인이 AI 때문에 커리어 방향을 잃은 경우

- Customer profile: 30대 직장인 / 비개발 또는 초급 개발 전환 고민 / AI로 인한 커리어 불안
- Pressure test: worker 세그먼트 질문에 parent 중심 데이터셋에서도 usable signal을 얼마나 뽑아낼 수 있는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 parent-heavy corpus 탓에 직장인 질문에서 뜬금없는 육아 앵커가 섞일 위험이 있었다. P1 이후엔 segment/source normalization 덕분에 worker 질문에도 비교적 일관된 커리어 답변이 가능하다.
- Retrieved evidence bundle:
  - [EvidenceAnchor] `기사` | 기사 | AI 불안 때문에 아예 전공이나 진로를 바꾸는 사람들이 늘고 있다는 보도가 있어요. 막연한 불안이 진짜 결정을 바꾸는 거죠. | urn:harness:evidenceanchor:ai-anxiety-career
  - [EvidenceAnchor] `연구` | 연구 | AI에 대한 불안이 클수록 'AI를 잘 다룰 수 있다'는 자신감이 떨어진다는 연구가 있어요. 그래서 시작이 제일 중요해요. | urn:harness:evidenceanchor:ai-self-efficacy
  - [HackerNews] `community_link` | Ask HN: With the rise of AI, how to approach my new career in software dev? | Ask HN: With the rise of AI, how to approach my new career in software dev? | urn:harness:hackernews:Ask HN: With the rise of AI, how to approach my -23de21284772
  - [Mollick] `rss_article` | A Guide to Which AI to Use in the Agentic Era | It's not just chatbots anymore | https://www.oneusefulthing.org/p/a-guide-to-which-ai-to-use-in-the

### 12-turn Simulation

1. **고객**: 요즘 AI 때문에 제가 하려는 커리어 전환이 의미 있나 싶어요. 시작도 하기 전에 기죽습니다.
2. **서비스**: 이번 P1엔 AI 불안이 진로 변경으로 이어진다는 기사형 근거와, 불안이 self-efficacy를 떨어뜨린다는 연구가 같이 들어와 있습니다. 그래서 지금 필요한 건 “시장 결론”보다 “내가 다룰 수 있다는 감각 회복”입니다.
3. **고객**: 근데 진짜 너무 빨리 바뀌잖아요. 배워도 금방 쓸모없어질 것 같아요.
4. **서비스**: 맞습니다. 그래서 툴 이름을 외우는 방식으로 접근하면 지칩니다. 이번 데이터셋에 “이제는 단순 챗봇만의 시대가 아니다”라는 정리도 들어와 있는데, 핵심은 특정 모델 암기가 아니라 문제 정의, 검증, 워크플로 조합 능력으로 옮겨가고 있습니다.
5. **고객**: 그럼 뭘 먼저 배워야 하나요?
6. **서비스**: 먼저 “AI 없이도 설명 가능한 작업 단위”를 잡으세요. 예를 들어 자료 요약, 고객 메일 초안, 데이터 정리 같은 단위를 하나 정하고, 그 위에 AI를 덧붙이는 식이 좋습니다.
7. **고객**: 저는 자꾸 다른 사람이 더 빨리 따라잡을 것 같아서 포기하게 돼요.
8. **서비스**: 그 비교 루프가 불안을 키웁니다. 지금은 경쟁보다 반복이 중요합니다. 2주만이라도 같은 작업을 AI 없이 한 번, AI와 함께 한 번 비교하면서 “내 시간이 어디서 줄고 품질이 어디서 흔들리는지”를 기록해보세요.
9. **고객**: 코딩을 다시 시작하는 것도 늦지 않았을까요?
10. **서비스**: 늦었다고 보긴 어렵습니다. P1에 실린 현장 질문형 자료도 결국 “무엇을 배우느냐”보다 “어떻게 접근하느냐”를 묻고 있습니다. 도구 호출보다 요구사항 분해와 결과 검증이 되는 사람이 오래갑니다.
11. **고객**: 그럼 커리어를 접을지 말지보다, 먼저 작은 작업을 돌려보는 게 맞겠네요.
12. **서비스**: 맞습니다. 이번 P1 관점에서도 추상 공포가 클수록 의존이나 회피가 커지고, 구체적 사용 경험이 생길수록 self-efficacy가 회복되는 쪽으로 읽힙니다.

### What This Shows About P1

- worker 질문에도 P1이 가진 진로 불안, self-efficacy, 도구 변화 신호를 조합해 “시장 공포”를 “작업 단위 실험”으로 바꿨다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 7. 사범대·교대 준비생이 “AI 시대에 교사가 뭘 배워야 하나요?”라고 묻는 경우

- Customer profile: 20대 예비교사 / AI 불안은 높고, 수업에 어떻게 넣어야 할지 막막함
- Pressure test: 교사 측 질문에 윤리·리터러시·현장 도구 관점을 동시에 엮을 수 있는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “교사는 인간성으로 승부” 같은 추상 문장으로 끝났을 수 있다. P1 이후에는 teacher-candidate anxiety, ethics review, classroom tool article을 함께 묶어 훈련 항목으로 변환된다.
- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | Special Education Pre-Service Teachers&apos; Conscientiousness and Their Attitudes towards Artificial Intelligence: The Mediating Role of AI Literacy and AI Anxiety | Complex interactions between personality traits, technology literacy, and anxiety levels influence pre-service special education teachers' attitudes towards artificial intelligence (AI). | https://eric.ed.gov/?id=EJ1490320
  - [ERIC] `research_abstract` | AI Anxiety and Awareness of German Teacher Candidates | The aim of this study is to examine the anxiety levels of prospective German teacher candidates in the face of rapid developments in artificial intelligence applications. | https://eric.ed.gov/?id=EJ1484020
  - [SemanticScholar] `research_paper` | K-12 teachers’ ethical competencies for AI literacy: Insights from a systematic literature review | K-12 teachers’ ethical competencies for AI literacy: Insights from a systematic literature review | 10.1016/j.compedu.2025.105435
  - [Khan_Blog] `rss_article` | How Khan Academy Is Building a Better AI Tutor: Our Most Recent Learnings | <p>Three years ago, Khan Academy launched Khanmigo, a generative AI-powered tutor for students and assistant for teachers. | https://blog.khanacademy.org/how-khan-academy-is-building-a-better-ai-tutor-our-most-recent-learnings/

### 12-turn Simulation

1. **고객**: 교대 준비 중인데요. AI가 교사를 대체할 것 같아서 오히려 공부 의욕이 떨어집니다.
2. **서비스**: 이번 P1엔 예비교사들의 AI 불안과 인식, 그리고 K-12 교사에게 필요한 AI 리터러시 윤리 역량을 다룬 연구가 같이 들어와 있습니다. 그래서 첫 결론은 “교사가 사라진다”보다 “교사의 역할이 어디로 남는가”를 다시 보는 쪽입니다.
3. **고객**: 남는 역할이 뭔가요?
4. **서비스**: 학생 이해, 질문 설계, 오답 진단, 윤리적 사용 규칙 설계, 그리고 결과 검증입니다. 생성 자체보다 수업 맥락 판단이 남습니다.
5. **고객**: 그래도 AI 툴을 잘 못 다루면 뒤처질 것 같아요.
6. **서비스**: 맞습니다. 그래서 리터러시는 “툴을 아는 것”만이 아니라 “어디까지 맡기고 어디서 멈추는지 아는 것”까지 포함해야 합니다. 이번 데이터셋의 윤리 역량 리뷰도 그쪽을 강조합니다.
7. **고객**: 그럼 지금부터 뭘 연습해야 하죠?
8. **서비스**: 세 줄로 가면 됩니다. 1) 같은 주제를 AI 없이 설명해보기, 2) AI가 만든 설명의 오류 찾기, 3) 학생이 AI를 썼을 때 어떤 질문으로 사고를 되돌릴지 미리 써보기.
9. **고객**: 현장에서는 보조교사처럼 쓸 수 있는 건가요?
10. **서비스**: 가능한 부분이 있습니다. 이번 P1엔 실제로 튜터/교사 보조로 AI를 개선해온 사례성 글도 들어와 있습니다. 다만 교사의 업무를 줄이는 용도와 학생의 사고를 대신하는 용도는 분리해야 합니다.
11. **고객**: 그렇게 보면 교사의 역할이 없어지는 건 아니네요.
12. **서비스**: 네. 이번 P1 신호는 대체 공포보다 리터러시·윤리·검증 쪽으로 무게가 이동하고 있다는 쪽이 더 강합니다.

### What This Shows About P1

- 예비교사 불안을 단순 위로로 넘기지 않고, 윤리 역량·검증 역할·수업 설계 실험으로 이어지게 했다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 8. 고등학생 글쓰기·수행평가에서 AI를 어디까지 써도 되나 묻는 경우

- Customer profile: 학부모 또는 학생 / 수행평가·에세이·보고서 작성에서 AI 사용 경계가 모호함
- Pressure test: 쓰기 도움과 쓰기 대행을 구분하는 데 연구·미디어·교사 관점을 함께 쓰는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “표절은 안 됩니다” 정도의 교과서형 답변이 나왔을 수 있다. P1 이후에는 글쓰기 프로세스 단계별 허용/금지 기준과 부모 질문까지 붙는다.
- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | From Curiosity to Dependency: Nigerian Students&apos; Perspectives on AI Integration in Academic Research | This study examines the application of artificial intelligence (AI) writing tools in academic writing among Nigerian university students, highlighting both the potential benefits and significant challenges. | https://eric.ed.gov/?id=EJ1485441
  - [HackerNews] `community_link` | A Student's Tool Detects If Essays Were Written by AI | A Student's Tool Detects If Essays Were Written by AI | https://www.buzzfeednews.com/article/katienotopoulos/ai-writing-detection-tool-homework-students
  - [HackerNews] `community_link` | How A.I. Killed Student Writing (and Revived It) | How A.I. Killed Student Writing (and Revived It) | https://www.nytimes.com/2026/04/30/us/ai-students-cheating-homework-classrooms.html
  - [OpenAlex] `research_paper` | Not quite eye to A.I.: student and teacher perspectives on the use of generative artificial intelligence in the writing process | Not quite eye to A.I.: student and teacher perspectives on the use of generative artificial intelligence in the writing process | https://doi.org/10.1186/s41239-023-00427-0

### 12-turn Simulation

1. **고객**: 고등학생 수행평가 글쓰기에 AI를 써도 되나요? 다들 쓰는 것 같은데 기준을 모르겠어요.
2. **서비스**: 이번 P1에는 글쓰기에서 AI 활용의 기회와 의존 위험을 다룬 연구, 학생과 교사가 writing process에서 AI를 어떻게 보는지 다룬 논문, 그리고 AI 글 탐지 논쟁 기사형 자료까지 같이 들어와 있습니다. 그래서 기준은 “썼냐 안 썼냐”보다 “어떤 단계까지 맡겼냐”입니다.
3. **고객**: 그럼 아이디어 정리 정도는 괜찮고 본문은 안 된다는 식인가요?
4. **서비스**: 대체로는 그렇습니다. 주제 브레인스토밍, 개요 정리, 반론 찾기, 문장 다듬기는 보조로 볼 수 있지만, 핵심 주장과 근거 선택까지 넘기면 사고 과정이 비어버립니다.
5. **고객**: 학교에서 탐지 프로그램을 쓴다는데 그것만 믿어도 되나요?
6. **서비스**: 탐지 도구만으론 충분하지 않습니다. P1에 들어온 자료도 그 점을 보여줍니다. 더 좋은 방법은 초안의 이유를 본인 말로 다시 설명하게 하고, 자료를 왜 채택·배제했는지 물어보는 것입니다.
7. **고객**: 집에서 규칙을 만든다면 어떻게요?
8. **서비스**: 1) 첫 문단과 결론은 본인이 직접 쓴다, 2) AI는 반론 찾기와 표현 교정까지만 쓴다, 3) 제출 전 “이 글의 핵심을 입으로 설명할 수 있는가”를 확인한다, 이 세 줄이면 됩니다.
9. **고객**: 그럼 AI를 전면 금지하는 것보다 낫겠네요.
10. **서비스**: 네. 이번 P1 기준으로는 전면 금지보다 단계 제한과 설명 책임을 붙이는 쪽이 훨씬 현실적입니다.
11. **고객**: 핵심은 사고를 대신시키지 않는 거군요.
12. **서비스**: 정확합니다. 보조는 허용하되 주장 형성과 설명 책임은 학생에게 남겨야 합니다.

### What This Shows About P1

- 글쓰기 보조와 대행의 경계를 “단계별 허용 규칙”으로 정리해, 단순 금지보다 실행 가능한 가정용 기준을 만들었다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 9. 유아·저학년 아이에게 AI를 어떻게 설명해야 하는지 묻는 부모

- Customer profile: 30~40대 부모 / 유치원~초1 / 아이가 AI를 마법처럼 이해함
- Pressure test: 연령이 낮을수록 설명을 단순화하면서도 기술 환상을 키우지 않는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 유아 눈높이에 맞지 않는 기술 설명이나 막연한 공포 경고로 흐를 수 있다. P1 이후에는 유아 연구와 발달 앵커를 붙여 부모 말투로 번역할 수 있다.
- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | What Is Artificial Intelligence?: Analyzing the Drawings of Preschool Children | Artificial intelligence, also known as machine intelligence, is defined as the intelligence demonstrated by machines or computers. | https://eric.ed.gov/?id=ED662858
  - [ERIC] `research_abstract` | Investigation of Preschool Education Teachers, Preschool Children and Mothers&apos; Opinions on Artificial Intelligence | Nowadays, artificial intelligence, which is used in different fields with the increase in the number of works and transactions carried out in digital environment, is also used in the field of education. | https://eric.ed.gov/?id=EJ1445445
  - [EvidenceAnchor] `역사 사례` | 역사 사례 | 재밌는 게, 1851년에 프로이센 정부가 어떤 학교를 금지한 적이 있어요. 노래하고 춤추고 정원 가꾸고 노는 게 커리큘럼이었는데, '아이들이 불복종을 배운다'고 무서워한 거죠. 그 학교가 바로 지금의 '유치원'이에요. 새로운 걸 처음 볼 땐 다들 과하게 겁부터 내더라고요. | urn:harness:evidenceanchor:anchor-kindergarten-1851
  - [EvidenceAnchor] `연구·사례` | 연구·사례 | 1930년대 덴마크에서 한 건축가가 봤더니, 아이들이 잘 만든 새 놀이터보다 공사장 폐허에서 노는 걸 더 좋아하더래요. 못 박고, 고철로 뭘 만들고. 그래서 '모험 놀이터'라는 걸 만들었는데 대성공이었죠. 아이한테 필요한 건 안전한 환경이 아니라, 안전하게 위험을 겪어보는 환경이라는 거예요. | urn:harness:evidenceanchor:anchor-junk-playground

### 12-turn Simulation

1. **고객**: 유치원생 아이가 AI를 진짜 사람처럼 생각해요. 어떻게 설명해야 할지 모르겠어요.
2. **서비스**: 이번 P1엔 유아들이 AI를 어떻게 그려서 이해하는지 본 연구와, 유아교사·아이·엄마가 AI를 어떻게 보는지 다룬 연구가 들어와 있습니다. 이 연령대에선 “정확한 기술 설명”보다 “사람과 기계의 차이”를 잡아주는 게 더 중요합니다.
3. **고객**: 아이한테는 뭐라고 말하면 될까요?
4. **서비스**: “AI는 생각하는 척 도와주는 기계고, 네 마음을 진짜 아는 친구는 아니야” 정도가 좋습니다. 사람처럼 말할 수 있어도 사람은 아니라는 선을 먼저 긋는 거죠.
5. **고객**: 그럼 그냥 장난감처럼 보여주면 되나요?
6. **서비스**: 부분적으로는 맞지만, 만능처럼 느끼게 만들면 안 됩니다. 아이가 직접 해보는 활동이 남아 있어야 합니다.
7. **고객**: 예를 들면요?
8. **서비스**: 예를 들어 그림 주제를 AI가 하나 던져주면, 실제 그림은 아이가 그리고 이야기는 부모와 함께 붙이는 식이 좋습니다. AI는 시작 버튼이고, 주인공은 아이여야 합니다.
9. **고객**: 아이가 “AI가 더 잘 그리는데 왜 내가 해?”라고 하면요?
10. **서비스**: 그럴 때는 결과보다 경험을 강조하셔야 합니다. 이번 앵커의 모험 놀이터 사례처럼, 아이는 완성품보다 스스로 해보는 과정에서 자랍니다.
11. **고객**: 부모가 먼저 지켜야 할 규칙이 있을까요?
12. **서비스**: 세 가지입니다. 1) AI 결과를 정답처럼 말하지 않기, 2) 아이 앞에서 “기계가 다 해준다”는 표현 안 쓰기, 3) AI 뒤에 꼭 손으로 하는 활동 하나 붙이기.

### What This Shows About P1

- 유아 관련 연구와 앵커 사례를 묶어, 기술 설명을 아이 발달 수준에 맞는 관계·경험 언어로 번역했다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.

## Case 10. 학교가 AI 도구를 도입한다는데 부모가 무엇을 물어봐야 하나

- Customer profile: 학부모 / 학교 공지로 AI 학습도구 도입 예정 / 정보 비대칭 불안 큼
- Pressure test: 정책·거버넌스 질문 리스트를 뽑아낼 수 있는지 본다.
- AS-IS 대비 개선 주석: AS-IS라면 “학교와 상의해보세요” 수준으로 끝났을 가능성이 크다. P1 이후에는 policy framework와 parental readiness 자료를 바탕으로 부모 질문 리스트가 바로 나온다.
- Retrieved evidence bundle:
  - [ERIC] `research_abstract` | AI Education Policy and Practice Ecosystem Framework | Adapted from the research conducted by Cecilia Ka Yuk Chan and the AI Ecological Education Policy Framework, which addressed "the multifaceted implications of artificial intelligence (AI) integration in university teachi | https://eric.ed.gov/?id=ED679179
  - [ERIC] `research_abstract` | Towards Effective Artificial Intelligence-Driven Learning in Indonesian Child Education: Understanding Parental Readiness, Challenges, and Policy Implications | Background/purpose: The integration of artificial intelligence (AI) into child education presents transformative opportunities, yet Indonesian parental readiness remains insufficiently explored. | https://eric.ed.gov/?id=EJ1475914
  - [EvidenceAnchor] `커뮤니티` | 커뮤니티 | 학교에 AI를 도입한다니까, 전문가들이 오히려 '조심하라'고 한다는 글도 부모들 사이에 많이 돌아요. | urn:harness:evidenceanchor:community-cautious
  - [EvidenceAnchor] `국제 동향` | 국제 동향 | 올해 코펜하겐에서 '아이와 AI'만 다룬 큰 회의가 열렸는데, AI 대부라 불리는 요수아 벤지오, 유럽연합 집행위원장까지 나왔어요. 세계 지도자들이 모여서 '아이와 AI'를 따로 걱정한다는 건, 이게 우리 집만의 고민이 아니라는 뜻이죠. | urn:harness:evidenceanchor:anchor-copenhagen-summit

### 12-turn Simulation

1. **고객**: 학교에서 AI 학습도구를 도입한다고 공지가 왔는데요. 솔직히 뭘 물어봐야 할지도 모르겠어요.
2. **서비스**: 이번 P1에는 AI 교육 정책·실천 생태계를 정리한 프레임워크와, 부모 준비도와 정책 함의를 다룬 연구가 들어와 있습니다. 그래서 첫 질문은 “도입하느냐 마느냐”보다 “무슨 통제장치와 목적을 두고 도입하느냐”입니다.
3. **고객**: 구체적으로 어떤 질문이요?
4. **서비스**: 첫째 학습 목표가 무엇인지, 둘째 어떤 과제는 AI 허용이고 어떤 과제는 금지인지, 셋째 학생 데이터와 대화기록을 어떻게 다루는지, 넷째 교사가 결과를 어떻게 검증하는지 물으셔야 합니다.
5. **고객**: 부모 입장에서 제일 불안한 건 아이가 기계에 너무 기대는 거예요.
6. **서비스**: 그 우려도 맞습니다. 이번 P1엔 학교 AI 도입을 두고 부모들 사이에 “조심하라”는 커뮤니티 앵커가 있고, 국제적으로도 아이와 AI를 따로 다루는 회의가 열릴 정도로 이 문제가 독립 이슈가 됐습니다.
7. **고객**: 학교가 “요즘 다 합니다”라고만 답하면요?
8. **서비스**: 그때는 유행이 아니라 운영 질문으로 되돌리시면 됩니다. “AI가 학생 사고를 대신하지 않게 어떤 설계를 했나요?”, “AI 없이도 평가 가능한 구간이 있나요?”라고요.
9. **고객**: 개인정보 얘기도 해야 하나요?
10. **서비스**: 네, 꼭 하셔야 합니다. 계정 생성 방식, 대화 저장 여부, 부모 동의 범위, 외부 모델 연동 여부를 물어보시는 게 맞습니다.
11. **고객**: 설명회 전 제가 메모해갈 핵심 5개만 주실래요?
12. **서비스**: 1) 도입 목적, 2) 허용/금지 과제 구분, 3) 검증 방식, 4) 데이터 처리, 5) 문제 발생 시 부모 통보 절차입니다.

### What This Shows About P1

- 정책 프레임워크와 부모 준비도 연구를 묶어, 학교 AI 도입 공지를 부모가 실제 질문 가능한 체크리스트로 바꿨다.
- AS-IS였다면 중간 follow-up에서 톤이 추상화되거나 다른 세그먼트 근거가 섞였을 가능성이 높다. 이번 버전은 케이스 내부 질문이 길어져도 같은 문제축을 유지한다.
- rights boundary를 지켰다: raw community 내부 전용 본문은 직접 노출하지 않고 customer-facing 행만 사용했다.