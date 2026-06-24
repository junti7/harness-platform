# edu-app — VP 훈련 pilot (App #2)

Harness 3-앱 전략의 두 번째 앱. **전문 UX 툴(v0/Figma) 기반 frontend의 시험대**다.

| 앱 | 위치 | 성격 | 포트 |
|---|---|---|---|
| App #1 | `harness-os/frontend` | 내부 운영 콘솔(트레이딩·결재·Jarvis 등) | 5173 |
| **App #2 (이 앱)** | `harness-os/edu-app` | **VP 훈련 pilot** — UX 파이프라인 검증 | 5174 |
| App #3 (향후) | 미생성 | 대외 고객 edu 서비스. pilot 완성도 담보 후 본격 구축 | — |

## 왜 이 앱인가
- 기존 VP 훈련 화면은 콘솔(`frontend`) 안 `EduVpTrainingPage.tsx`(1,695줄)에 7,311줄짜리 공용 CSS와 엉켜 있었다.
- 이 앱은 그것을 **그대로 복사하지 않고**, v0/Figma로 화면을 새로 짓고 **검증된 로직만 이식**하는 방식으로 다시 만든다.
- 여기서 UX 파이프라인(토큰→v0→코드)이 검증되면, 같은 방식으로 App #3(대외 고객)을 짓는다.

## 경계 (반드시 지킬 것)
- 이 앱은 **secret 티어 `/api/edu/vp-training/*` 만** 호출한다. (`src/lib/api.ts`)
- 내부 콘솔 API(`/api/dashboard`, `/api/approvals`, `/api/trading*` 등) import/호출 **금지**.
- 대외 public 티어(`/api/public/edu/*`)는 **App #3**의 몫. 여기서 쓰지 않는다.
- vp-training API는 `X-Harness-Secret`을 요구한다 → 이 앱은 **접근 제어 전제**이며 secret이 번들에 들어가므로 **완전 공개 URL로 노출 금지**. (대외 공개는 secret이 필요 없는 public 티어를 쓰는 App #3에서)

## 스택
- Vite + React 19 + TypeScript
- **Tailwind v4** (`@tailwindcss/vite`) — CSS 우선 설정, `src/index.css`의 `@theme`
- **shadcn/ui** 준비 완료(`components.json`, `@/lib/utils`의 `cn()`). 컴포넌트 추가: `npx shadcn@latest add button card ...`
- 디자인 토큰 단일 출처 = **`/DESIGN.md`**. `src/index.css`가 그 값을 1:1 매핑. 토큰 변경은 DESIGN.md 먼저.

## 개발
```bash
cd harness-os/edu-app
npm install
cp .env.example .env   # VITE_HARNESS_SECRET 등 채우기
npm run dev            # http://127.0.0.1:5174 (proxy: /api → :8000)
```
백엔드(uvicorn :8000)가 떠 있어야 vp-training API가 응답한다.

## v0 / Figma 워크플로우
1. **토큰 확인** — `DESIGN.md` ↔ `src/index.css`의 `@theme`가 일치하는지.
2. **화면 생성(v0)** — 모바일 우선 프롬프트로 React+Tailwind 컴포넌트 생성. `shadcn/ui` 사용.
3. **반입** — 생성 코드를 `src/components/`에 두고, 색/spacing을 DESIGN 토큰 유틸(`bg-card`, `text-ink-strong`, `rounded-lg` 등)로 정규화.
4. **로직 이식** — `EduVpTrainingPage.tsx`의 API/상태/인증 로직을 `src/lib/api.ts`(`vpGet`/`vpPost`) 위로 옮긴다.
5. **모바일 검증** — 폰에서 한 손 조작·정보 안 잘림 통과해야 "완성"(Mobile-First Rule).

## 빌드 / 배포 (향후)
- `npm run build` → `dist/`. 프로덕션 서빙은 `serve dist -p 5174`(`serve:prod`).
- 배포는 **`scripts/deploy_to_macmini.sh` 경로로만**(별도 launchd 잡 추가 필요). Mac Mini 수동수정/scp 금지.
- PWA(manifest/서비스워커)·HTTPS는 화면이 선 뒤 단계. App #1 `index.html`의 PWA 메타가 참고 예시.
