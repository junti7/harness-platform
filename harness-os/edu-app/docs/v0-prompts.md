# v0 프롬프트 — VP 훈련 pilot 화면

v0(https://v0.dev)에 붙여넣어 React+Tailwind+shadcn 화면을 생성한 뒤,
이 앱(`harness-os/edu-app`)으로 반입한다. 모든 색/타이포는 아래 토큰을 따른다.

## 0. 모든 프롬프트에 공통으로 먼저 붙일 토큰 스펙

```
디자인 토큰(반드시 이 값만 사용, 임의 색 금지):
- 배경 background #f8fafc, 카드 surface #ffffff, 테두리 border #e2e8f0 / strong #cbd5e1
- 텍스트: ink-strong #0f172a(헤드라인/숫자), ink #111827(본문), muted #475569(보조), faint #64748b(메타)
- 브랜드/CTA: primary(accent) #2563eb, accent-soft #dbeafe, accent-cyan #0ea5e9
- 상태: success #059669, warning #d97706, danger #dc2626 (손익색은 상태에만 제한적으로)
- radius: sm 4px / md 10px / lg 14px / pill 9999px. 카드·버튼은 rounded-lg/md.
- 폰트: Pretendard(한글). 헤드라인 700, 섹션 600, 본문 400.
요구사항:
- shadcn/ui 컴포넌트 사용(Button, Card, Input, Label 등). Tailwind v4.
- 모바일 우선: 단일 컬럼, max-w-[480px] 중앙정렬, 큰 탭타깃(최소 44px), 한 손 조작.
- 한국어 UI. 톤은 따뜻하고 신뢰감 있게(트레이딩 콘솔 톤 아님, 학습자 대상).
- 색은 위 토큰을 CSS 변수/유틸로. 데이터 fetch 로직은 넣지 말고 props 콜백으로 분리.
```

---

## 프롬프트 1 — 로그인 / 가입 화면

```
[위 토큰 스펙 블록을 먼저 붙인다]

"부대표 훈련" 앱의 로그인/가입 화면을 만들어줘. 모바일 우선, 단일 카드 중앙 배치.

상단: 작은 라벨 "Harness · 훈련", 제목 "부대표 훈련", 한 줄 설명.

탭 또는 토글 2개: [로그인] / [가입].
- 로그인 폼: 이메일(email), 비밀번호(password), [로그인] primary 버튼.
- 가입 폼: 이름(name), 이메일(email), 비밀번호(password), [가입하기] primary 버튼.

상태 처리:
- 제출 중 버튼 로딩(스피너 + 비활성).
- 에러 메시지 영역(danger 색, 카드 안 상단). 예: "이메일 또는 비밀번호가 올바르지 않습니다."

props 인터페이스(이 시그니처를 그대로 사용, fetch 는 넣지 말 것):
  type Props = {
    onLogin: (v: { email: string; password: string }) => Promise<void>
    onRegister: (v: { name: string; email: string; password: string }) => Promise<void>
    loading?: boolean
    error?: string | null
  }
컴포넌트 이름: AuthScreen. 단일 파일 export default.
```

반입 후 배선: `onLogin` → `vpPost('/api/edu/vp-training/account/login', {email,password})`,
`onRegister` → `vpPost('/api/edu/vp-training/account/register', {name,email,password})`.
로그인 응답의 `training_auth_token`/`email`/`name`/`customer_id` 를 로컬에 저장.

---

## 프롬프트 2 — 케이스 선택 화면

```
[위 토큰 스펙 블록을 먼저 붙인다]

로그인 후 "내 훈련" 케이스 선택 화면을 만들어줘. 모바일 우선, 카드 리스트.

상단 헤더: "내 훈련", 우측에 사용자 이름 + 작은 [로그아웃] 텍스트 버튼.
기본 행동(맨 위 고정): [+ 새 훈련 시작] primary 버튼(풀폭).

케이스 카드 리스트(각 카드 탭 가능):
- 제목: case_label (예: "Day 1 · 진행률 40%")
- 진행률 바(progress_pct, 0~100). primary 색 채움.
- 메타 줄: 상태 칩(status) + "수정 N일 전"(updated_at 상대시간) — faint 색, pill 칩.
- 카드 전체가 버튼(onSelect).

빈 상태(cases 길이 0): 일러스트 자리 + "아직 시작한 훈련이 없어요" + 강조된 [첫 훈련 시작] 버튼.

로딩 상태: 카드 3개 스켈레톤.

props(이 시그니처 그대로, fetch 금지):
  type TrainingCase = {
    case_id: number
    status: string
    updated_at: string
    progress_pct: number
    case_label: string
    has_training_state: boolean
  }
  type Props = {
    userName: string
    cases: TrainingCase[]
    loading?: boolean
    onSelect: (caseId: number) => void
    onNew: () => void
    onLogout: () => void
  }
컴포넌트 이름: CaseSelectScreen. 단일 파일 export default.
```

반입 후 배선: 마운트 시 `vpGet('/api/edu/vp-training/cases', { email })` → `cases`.
`onNew` → `vpPost('/api/edu/vp-training/intake', { email, name, force_new: true, ... })` 후 케이스 새로고침.
`onSelect(caseId)` → 훈련 단계 화면으로 라우팅(다음 프롬프트에서 제작).

---

## 반입 절차 (공통)

1. v0 출력 코드를 `src/components/AuthScreen.tsx` / `CaseSelectScreen.tsx` 로 저장.
2. 색/spacing 을 토큰 유틸로 정규화(`bg-card`, `text-ink-strong`, `text-muted-foreground`, `rounded-lg`, `bg-primary` 등). 하드코딩 hex 가 남아있으면 토큰 변수로 교체.
3. 필요한 shadcn 컴포넌트 설치: `npx shadcn@latest add button card input label` (필요분만).
4. 데이터 로직은 화면 밖(상위 컨테이너)에서 `src/lib/api.ts` 의 `vpGet`/`vpPost` 로 배선.
5. `npm run build` + `npm run lint` 통과 확인.
6. 폰 뷰포트에서 한 손 조작·정보 안 잘림 검증(Mobile-First Rule) 후에야 완료.
```
