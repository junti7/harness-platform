# CHART_AUTHORING_PLAYBOOK.md

# Version: 1.0 | Date: 2026-05-10
# 상위 규약: docs/product/PLATFORM.md, CLAUDE.md, docs/operations/QA_PLAYBOOK.md

---

## 1. Purpose

`Physical AI Weekly` PDF에 들어가는 차트, 다이어그램, 컨셉 이미지의 작성 기준과 빌드 파이프라인을 정의한다. 이 문서는 (1) 차후 시행착오 반복을 막고, (2) Codex 외 다른 LLM(Claude, Gemini, GPT reasoning, local model)에게 동일한 작업을 위임할 때 reference로 사용한다.

이 playbook을 따른 차트는 paid 발행 전 `qa_clear` + `legal_review_approve` 게이트를 통과해야 한다.

추가 적용 범위:

- 고객-facing 교육 컨설팅 보고서
- 학부모 대상 AI 교육 가이드
- 워크숍 deck / flash card / infographic / summary sheet

---

## 2. Visual Asset Taxonomy

| Type | Tool | When | Governance |
| --- | --- | --- | --- |
| **Data Chart** | matplotlib (`.venv` 내) | 시계열, 시장 규모, 비용 곡선, 분포 등 출처 데이터 기반 | 출처 명시 + QA fact check |
| **Concept Diagram** | matplotlib `Rectangle` + `annotate` 또는 graphviz | 흐름도, 매트릭스, 박스+화살표 구조도 | 본문 주장과 라벨 일치 검증 |
| **Generated Image** | Gemini 2.5 Flash Image (Nano Banana) / DALL-E 3 / Midjourney | 컨셉 일러스트, 표지, 시각 메타포 | Legal: 상업 라이선스 + AI-generated disclosure |

**Default 우선순위**: Data Chart > Concept Diagram > Generated Image. 사실 추적 가능성과 재현성이 paid 콘텐츠의 신뢰도를 결정한다.

생성형 이미지는 다음 조건을 모두 만족할 때만 사용한다:

- API 키와 상업 사용권이 확보되어 있다.
- 사실 데이터를 시각화하는 차트로 대체할 수 없는 추상 메타포다.
- 출력물에 *AI-generated* disclosure를 표기할 수 있다.

---

## 3. Build Pipeline

```
markdown (docs/issues/*.md)
   │  ![alt](filename.b64)
   ▼
scripts/render_markdown_pdf.py
   │  - layout 파싱 (layout-cover / split / summary / default)
   │  - .b64 또는 raw 이미지 → magic-byte 기반 mime 자동 감지
   │  - inline <img src="data:image/...;base64,...">
   ▼
HTML (1920×1080 슬라이드 단위)
   │
   ▼
Chrome --headless --print-to-pdf  →  PDF
```

이미지 자산 파일 명명 규칙:

- `<asset_name>.png` — 원본 (matplotlib 출력)
- `<asset_name>.b64` — base64 인코딩 텍스트 (renderer가 직접 픽업)

`generate_charts.py`의 `_save()` 함수가 두 형식을 모두 자동 출력한다.

`render_markdown_pdf.py`가 자동 처리하는 것:

- `:::layout-<name>:::` 마크업 → CSS class. `layout-` prefix를 자동 strip하므로 `layout-split` → `split`로 매칭됨.
- 매직 바이트로 이미지 mime 감지 (PNG, JPEG, GIF, WEBP). 파일명 키워드는 신뢰하지 않는다.
- footnote `[^N]` 자동 수집 + 슬라이드 하단 표시.

---

## 4. Design Tokens

ARK 스타일 프리미엄 보고서 톤. 8페이지 모두 동일한 토큰 사용.

| Token | Value | Use |
| --- | --- | --- |
| `PRIMARY` | `#2563eb` | 강조, 액센트, link, primary series |
| `GREEN` | `#10b981` | 긍정 / 성장 / Beneficiaries |
| `RED` | `#ef4444` | 위험 / 하락 / At Risk |
| `INK` | `#111827` | 본문 헤딩 |
| `SUB` | `#374151` | 본문 텍스트 |
| `MUTED` | `#9ca3af` | 캡션, 출처, meta |
| `GRID` | `#e5e7eb` | 격자, 보더 |

폰트 위계 (PDF 슬라이드 1920×1080 기준):

| Element | Size | Weight |
| --- | --- | --- |
| Cover h1 | 90pt | 900 |
| Slide h1 | 58pt | 900 |
| Section h2 | 36pt | 800 |
| Section h3 | 30pt | 800 |
| Body / li | 26pt | 400 (Summary lead 28pt) |
| Footnote | 15pt | 400 |
| Caption / meta | 18pt | 900 (uppercase) |

차트 내부 폰트 (1100×800 px export):

| Element | Size | Weight |
| --- | --- | --- |
| Chart title | 22 | 900 |
| Subtitle | 12 | 600 |
| Axis label | 13 | bold |
| Tick label | 11 | normal |
| In-chart label | 13–15 | bold |
| Source caption | 9 | italic |

한글 폰트는 `AppleGothic` 우선, fallback은 `Apple SD Gothic Neo`, `Helvetica Neue`, `sans-serif`.

---

## 5. Known Pitfalls (체크리스트)

차트 작업 시 매번 확인할 것:

### 5.1 matplotlib

- [ ] **Unicode minus 글리프 누락** — AppleGothic은 U+2212 글리프가 없어 log axis tick과 callout에서 깨진다. 두 가지 대응: (a) `axes.unicode_minus = False`를 rcParams에 설정, (b) tick formatter를 `FuncFormatter(lambda v, _: f"{v:g}")`로 일반 숫자 포맷으로 강제, (c) callout 텍스트에는 ASCII hyphen `-` 사용.
- [ ] **한글 폰트 가족 명시** — `plt.rcParams["font.family"] = ["AppleGothic", "Apple SD Gothic Neo", "sans-serif"]` 안 하면 한글이 박스로 출력된다.
- [ ] **DPI** — `dpi=220`, `bbox_inches="tight"`, `facecolor="white"`. 슬라이드 visual-pane 크기에 fit.
- [ ] **Title vs Subtitle 겹침** — `set_title(pad=38, loc="left")` + `ax.text(0.0, 1.04, ..., transform=ax.transAxes)` 패턴. pad가 18 이하면 겹친다.
- [ ] **박스 안 multi-line text** — `va="top"`으로 정렬하고 title/sub 사이 vertical offset 9–14 단위 확보. center 정렬에 `va="center"` 두 개 겹쳐 쓰지 말 것.

### 5.2 render_markdown_pdf.py

- [ ] **Layout prefix** — markdown의 `:::layout-split:::`은 layout 값이 `"layout-split"`이다. 코드 내부에서는 `layout.removeprefix("layout-")` 처리되어 `"split"`로 매칭됨. 새 layout 추가 시 동일 규칙.
- [ ] **Image mime detection** — 매직 바이트 기반 자동 감지. 파일명에 `"robot"` 같은 키워드가 있어도 실제 파일이 PNG면 `image/png`로 처리됨. 새 이미지 형식 추가 시 magic byte 분기 추가.
- [ ] **Chrome headless 캐시** — Chrome이 가끔 동일 출력 파일을 안 갱신한다. 디버깅 시 PDF + HTML 둘 다 `rm -f` 후 재실행.
- [ ] **Split-grid + footnote 충돌** — split-grid height 600px + li margin-bottom 28px + footnote bottom 90px가 안전 조합. 본문 bullet 4개 이상이면 폰트/마진 더 줄여야 함.
- [ ] **`.full-pane` / `.layout-summary` 누락** — 명시 안 하면 브라우저 default(16pt)로 fallback해서 가독성 무너짐. 새 layout 추가 시 li 폰트 명시 필수.

### 5.3 Pipeline

- [ ] **`.venv` 강제** — `python` 직접 호출 금지. 항상 `.venv/bin/python`. CLAUDE.md §3의 Python Environment Rule.
- [ ] **`.b64`와 `.png` 동시 출력** — `_save()`가 둘 다 만들어둔다. renderer는 둘 다 픽업 가능하지만 `.b64`가 우선.
- [ ] **출처 캡션** — 모든 차트 우하단에 출처 italic 캡션. 본문 footnote와 일관.
- [ ] **이미지가 빈 visual-pane으로 나오면** — `grep -c "data:image" <html>` 로 확인. 0이면 layout 매칭 또는 b64 fetch 실패.

---

## 6. Adding a New Chart (절차)

1. **데이터 출처 확인** — 이슈 본문에 인용된 출처(ARK, McKinsey, SemiAnalysis 등)와 정확히 일치해야 함. 본문에 없는 데이터를 차트에 넣으면 QA에서 reject.
2. **`scripts/generate_charts.py`에 함수 추가** — 기존 `cost_trend_chart`, `concept_diagram`, `tam_breakdown_chart`, `watchlist_matrix`를 reference로. 함수 docstring에 데이터 출처와 본문 §번호 명시.
3. **`_save(fig, "<asset_name>")` 호출** — `.png` + `.b64` 동시 생성.
4. **`__main__`에 함수 추가** — 모든 차트가 한 번의 `python scripts/generate_charts.py`로 재현되어야 한다.
5. **markdown에 `![alt](<asset_name>.b64)` 삽입** — split layout이어야 visual-pane에 들어감.
6. **PDF rebuild** — `rm -f <pdf> <html>` 후 `python scripts/render_markdown_pdf.py <md> <pdf>`.
7. **시각 검증** — `pdftoppm -png -r 80 <pdf> /tmp/<name>` 로 페이지 렌더링 후 사람 눈 검토.
8. **거버넌스 게이트 준비** — Legal review (출처 라이선스), QA fact check (수치 일치), Red Team cross-LLM (왜곡 여부), Pre-Mortem (paid 발행 시 risk) 메모 첨부.

---

## 7. Delegating to Other LLMs

다른 LLM(Claude, Gemini, GPT reasoning, local model)에게 차트 작업을 위임할 때는 아래 prompt template을 사용한다.

### 7.1 Required Context to Pass

위임 전에 LLM에게 항상 다음을 context로 제공:

1. `CLAUDE.md` (운영 헌법, approval semantics)
2. `docs/operations/CHART_AUTHORING_PLAYBOOK.md` (이 문서)
3. `scripts/generate_charts.py` (reference implementation 4개)
4. `scripts/render_markdown_pdf.py` (build pipeline)
5. `docs/operations/QA_PLAYBOOK.md` (verification gate)
6. 대상 issue markdown (`docs/issues/*.md`)

### 7.2 Prompt Template (XML structured)

```xml
<task>
Add a new chart to `docs/issues/<issue_filename>.md` for §<section_number>.
The chart must visualize the body claim: "<paste the exact claim sentence>".
Cited data source(s): <paste citation strings from the issue>.
</task>

<environment>
- Working directory: /Users/juntae.park/projects/harness-platform
- Python: .venv/bin/python (NEVER use system python)
- All charts go to docs/issues/<asset_name>.{png,b64}
- Reference: scripts/generate_charts.py (4 working chart functions)
</environment>

<deliverables>
1. New function in scripts/generate_charts.py that produces the chart.
2. Function call added to __main__.
3. Markdown updated to insert ![alt](<asset_name>.b64) under correct slide.
4. PDF rebuilt and at least one rendered page verified.
</deliverables>

<grounding_rules>
- Use only data points cited in the issue body. Do not introduce numbers from your own knowledge.
- Use design tokens from docs/operations/CHART_AUTHORING_PLAYBOOK.md §4 — do not invent colors or fonts.
- All chart text labels must be checkable against the issue body.
- AppleGothic does NOT have unicode minus (U+2212). Use ASCII hyphen in callouts and FuncFormatter for log axis ticks.
</grounding_rules>

<verification>
1. Run: .venv/bin/python scripts/generate_charts.py
2. Confirm `saved: <asset_name>.png + <asset_name>.b64` line.
3. Run: rm -f <pdf_path> <html_path> && .venv/bin/python scripts/render_markdown_pdf.py <md> <pdf>
4. Run: pdftoppm -png -r 80 -f <page_num> -l <page_num> <pdf> /tmp/check
5. Visually inspect the rendered page.
</verification>

<constraints>
- DO NOT call external image-generation APIs without explicit owner approval (cost gate).
- DO NOT modify CSS unless the chart actually requires a layout change.
- DO NOT skip the verification step — silent layout failures (empty visual-pane) are common.
- DO NOT publish or share the resulting PDF — the President controls publishing decisions.
</constraints>
```

### 7.3 Cross-LLM Verification

CLAUDE.md §2의 Red Team 규약상 차트 변경도 cross-LLM verification 대상이다. 한 LLM이 차트를 만들면, 다른 LLM이 다음을 점검한다:

- 차트의 모든 라벨이 본문 주장과 일치하는가?
- 데이터 출처가 정확히 인용되었는가?
- 시각적 왜곡(축 잘림, 비율 조작, log/linear 혼동)이 없는가?
- AI-generated 이미지가 사용된 경우 disclosure가 있는가?

두 LLM의 의견이 갈리면 third opinion 또는 인간(대표/부대표) 결정.

---

## 8. Governance Gates

Paid 콘텐츠의 차트는 다음 게이트를 모두 통과해야 발행 가능하다.

| Gate | 책임 | 점검 항목 |
| --- | --- | --- |
| `qa_clear` | QA Agent | 차트 수치와 본문 주장 일치, 라벨 오타, 출처 표기, 다국어 일관성 |
| `legal_review_approve` | Legal Counsel | 데이터 출처 인용 범위, AI-generated 이미지 라이선스, disclaimer |
| `red_team_clear` | Red Team (cross-LLM) | 시각적 왜곡, 사실 누락, 약한 가정 |
| `pre_mortem_approve` | 대표 (high-impact 시) | 차트가 잘못 인용될 시 worst-case |

게이트가 누락되면 묵시적으로 차단. CLAUDE.md §4 Approval Semantics 참조.

---

## 9. Known Reference Charts (현재 issue #002)

| Asset | Section | Type | Description |
| --- | --- | --- | --- |
| `robotics_cost.b64` | §1 Cost Trend | Data chart (log) | 액추에이터 / LiDAR / AI 추론 비용 곡선 2020–2025, -86%/yr 콜아웃 |
| `concept_robot.b64` | §2 Convergence | Concept diagram | `[멀티모달 LLM] × [정밀 액추에이터] = [범용 휴머노이드]` 박스 + 화살표 |
| `tam_breakdown.b64` | §3 TAM | Data chart | $12T + $12.5T = $24.5T+ stacked bar + Operating-Margin Gap ±30pp |
| `watchlist.b64` | §4 Watchlist | Concept diagram | Beneficiaries(녹) vs At Risk(빨) 2-column matrix |

---

## 10. Update Triggers

이 playbook은 다음 발생 시 업데이트한다:

- 새 layout / CSS class 추가
- 새 시각자료 type (예: 영상, 인터랙티브) 도입
- 알려진 함정 발견 — 함정 해결 후 §5에 추가
- 다른 LLM 위임 시 새 prompt 패턴 검증됨
- Paid 발행 후 QA에서 반복 reject되는 패턴 확인됨

업데이트 시 cross-LLM Red Team 검증 후 `red_team_clear`.

---

## 11. Customer Education Report Standard Toolchain

교육사업 고객용 시각물은 "예쁨"보다 **학습 전달력, 신뢰감, 재사용성, 빠른 수정 가능성**을 우선한다.

### 11.1 Tool Selection by Asset Type

| Asset Type | Default Tool | Why | Notes |
| --- | --- | --- | --- |
| 정량 차트 | `pandas` + `seaborn` | 수치 재현성, QA 용이 | 고객 납품본의 숫자는 코드가 기준 원본이어야 함 |
| 상호작용형 차트 | `plotly` | hover / filtering / embeddable | web report 또는 workshop portal용 |
| 개념도 / 흐름도 | matplotlib / graphviz / SVG | 수정 용이, 텍스트 선명도 | 가능하면 생성형 이미지보다 코드/벡터 우선 |
| 복잡 인포그래픽 | Nano Banana / OpenAI image generation | 고밀도 visual metaphor 제작 속도 | 긴 한글 텍스트는 후편집 권장 |
| 슬라이드 / 워크북 레이아웃 | Claude Design | 구조 설계, presentation 초안에 강함 | 최종 카피는 후편집 권장 |
| 플래시카드 / 학습 카드 | 이미지 생성 + Figma/SVG 후처리 | 템플릿 재사용에 유리 | 텍스트 공간을 미리 비워두는 prompt 사용 |

### 11.2 Customer Deliverable Rule

- **숫자와 축이 있는 시각물은 코드 생성**이 기본값이다.
- **설명용 메타포 / 분위기형 비주얼**만 생성형 이미지 사용을 허용한다.
- **긴 한글 텍스트는 이미지에 bake-in 하지 않는다.** 생성 후 Figma/SVG/HTML에서 후편집한다.
- 고객용 교육 자료는 아동용 장식이 아니라 **성인 학습자용 프리미엄 교육물**처럼 보여야 한다.

### 11.3 When to Use Nano Banana / Claude Design

#### Nano Banana 또는 동급 이미지 생성 모델

사용 적합:

- 복잡한 교육용 인포그래픽
- 비주얼 메타포가 필요한 1페이지 설명 자산
- 플래시카드 커버, 카드 배경, 모듈 대표 이미지
- 동일 스타일 변형이 여러 장 필요한 경우

주의:

- 긴 한글 본문은 직접 넣지 말고 placeholder zone만 확보
- 수치/표/정확한 법규 문구는 이미지 생성에 맡기지 않는다

#### Claude Design

사용 적합:

- 슬라이드 / handout / 보고서 레이아웃 초안
- 교육 flow / 페이지 구조 / hierarchy 설계
- 클릭 가능한 prototype 또는 workshop flow 시안

주의:

- pure image generator 대체재가 아니라 **layout and prototype tool**에 가깝다
- 최종 납품 전 typography, spacing, Korean copy는 사람 검수 필요

---

## 12. Customer Education Prompt Templates

### 12.1 Data Chart Brief

```md
목적: 고객용 교육 보고서에 들어갈 차트 설계
대상: 비전문가 성인 학습자 / 학부모 / 실무자
핵심 메시지: [한 문장]
데이터: [컬럼/수치/출처]
추천 차트 형태: [bar/line/scatter/heatmap 중 선택]
강조 포인트:
1. [포인트1]
2. [포인트2]
3. [포인트3]
피해야 할 것:
- 3D 효과
- 장식 과다
- 작은 글씨
- 색만으로 의미 전달
산출:
1. 차트 유형 추천
2. 축/범례/주석 설계
3. 발표용 캡션 2종
```

### 12.2 Educational Infographic Prompt

```md
Create a premium educational infographic for adult learners.
Audience: Korean parents, professionals, executive education clients.
Tone: calm, modern, trustworthy, practical.
Layout: clear headline zone, 3-step information flow, strong hierarchy, generous spacing.
Need: highly readable composition with room for later Korean text editing.
Avoid: childish illustration, neon palette, clutter, random icons, dense baked-in text.
Use: restrained blue accents, soft neutral background, editorial clarity.
Topic: [주제]
Key points:
1. [포인트1]
2. [포인트2]
3. [포인트3]
Visual metaphor: [roadmap / ladder / feedback loop / risk map / before-after]
Output: presentation-quality infographic with clean text zones.
```

### 12.3 Flash Card Prompt

```md
Create a premium educational flashcard visual for adult learners.
Audience: parents and professionals learning AI-era decision making.
Style: minimal, modern, Korean tech-education aesthetic.
Need:
- strong central visual metaphor
- empty title zone
- empty subtitle zone
- space for 3 bullet takeaways
Avoid:
- cartoonish style
- noisy gradients
- excessive icons
- text baked deeply into the image
Topic: [주제]
```

### 12.4 Claude Design Layout Brief

```md
Design a client-facing educational slide or one-page handout.
Audience: executives, parents, adult learners.
Need a calm, premium, highly readable layout.
Sections:
1. Key lesson
2. Why it matters
3. Example
4. Action takeaway
Use large Korean-friendly text zones, restrained blue accents, minimal decoration, card-based structure.
```

---

## 13. Customer-Facing QA Checklist

- [ ] 숫자와 축 라벨이 코드 원본과 정확히 일치하는가
- [ ] 한글 텍스트가 이미지 내에서 깨지지 않는가
- [ ] 시각 계층이 제목 → 핵심 메시지 → 보조 설명 순으로 읽히는가
- [ ] 흑백 인쇄 또는 축소 PDF에서도 핵심 정보가 유지되는가
- [ ] 장식 요소가 내용을 돕는가, 방해하는가
- [ ] 고객 브랜드 톤과 충돌하지 않는가
- [ ] 성인 교육용으로 충분히 차분하고 신뢰감 있는가
- [ ] 저작권/상표 위험이 있는 참조 이미지가 섞이지 않았는가
- [ ] 생성형 이미지 사용 시 disclosure 정책이 필요한가
- [ ] 모바일/슬라이드 축소 환경에서도 읽을 수 있는가

---

## 14. Sample — Harness Education Consulting Visual Pack

아래는 Harness의 교육사업 주제를 사용한 **고객용 샘플 시각화 패키지**다. 핵심 컨셉은 "부모가 먼저 AI를 능동적으로 학습하고 실제로 다룰 수 있는 상태가 된 뒤, 그 숙련을 바탕으로 자녀를 올바른 방향으로 이끈다"는 것이다. 숫자 차트, 인포그래픽, 플래시카드가 어떻게 분리되어야 하는지 예시로 제시한다.

### 14.1 Sample Deliverable Context

- 주제: **부모 먼저, 자녀는 나중 — AI 시대 학부모 AX 교육 8주 로드맵**
- 고객: 초중등 자녀를 둔 30–45세 학부모 대상 교육 컨설팅 프로그램
- 목적: "왜 부모가 먼저 AI를 이해하는 수준을 넘어 직접 다루고 숙련되어야 하는가"를 한 번에 납득시키는 orientation 자료

### 14.2 Sample Asset Pack

#### Asset A — Data Chart

- 제목: `학부모 AI 불안은 높지만, 부모의 능동적 활용 숙련은 아직 낮다`
- 형식: horizontal bar chart
- 데이터 구조:
  - `AI는 중요하다고 느낀다`
  - `AI를 자녀 교육에 써야 한다고 느낀다`
  - `우리 집 사용 기준이 있다`
  - `부모 본인이 매주 직접 AI를 써본다`
- 메시지:
  - 인식은 높다
  - 실행 기준과 부모 숙련은 낮다
  - 그래서 자녀 지도 전에 부모의 능동적 AI 학습이 먼저 필요하다

샘플 캡션:

> 한국 학부모층은 AI의 중요성에는 이미 동의하지만, 가정 내 사용 기준과 부모 본인의 실사용 루틴은 아직 낮은 단계에 머무른다. 교육 상품의 첫 가치는 "자녀를 바로 지도하는 법"이 아니라, 부모가 먼저 AI를 익숙하게 다루고 기준을 세울 수 있게 만드는 데 있다.

#### Asset B — Educational Infographic

- 제목: `부모가 먼저 익숙해져야, 자녀도 흔들리지 않는다`
- 형식: 3-step infographic
- 구조:
  1. 부모가 먼저 AI를 직접 써보고 익숙해진다
  2. 우리 집 기준을 만든다
  3. 그 기준으로 자녀 사용 원칙을 설계한다

샘플 이미지 프롬프트:

```md
Create a premium educational infographic for Korean parents.
Topic: Parents first, children later in AI education.
Audience: 30-45 year old parents, especially mothers evaluating AI use at home.
Tone: calm, intelligent, reassuring, premium.
Layout: 3-step vertical or left-to-right flow.
Steps:
1. Parent experiences AI directly
2. Family usage standard is defined
3. Child guidance is designed from that standard
Use a soft editorial aesthetic with restrained blue accents and minimal visual noise.
Leave clean text zones for Korean headline and 3 step labels.
Avoid childish school illustration, neon colors, emoji, crowded icon grids.
```

#### Asset C — Flash Card

- 카드 제목: `이번 주 부모가 먼저 익혀볼 것 3가지`
- 목적: 교육 종료 후 부모가 먼저 AI 사용 근육을 붙이게 만드는 follow-up card
- 전면 문구:
  - ChatGPT로 질문 1개 직접 해보기
  - 자녀와 AI 사용 10분 대화하기
  - 우리 집 AI 허용/금지 기준 1줄 쓰기

샘플 플래시카드 프롬프트:

```md
Create a modern educational flashcard for Korean parents.
Topic: 3 actions to start AI learning at home this week.
Audience: adult parents, premium education consulting clients.
Need: one strong central metaphor for guided progress, plus clean title and bullet zones.
Tone: calm, practical, trustworthy.
Avoid bright children-school motifs, mascot characters, and clutter.
```

### 14.3 Sample Production Split

| Asset | Best Tool | Why |
| --- | --- | --- |
| Asset A | seaborn | 숫자/라벨 정확성 우선 |
| Asset B | Nano Banana or OpenAI image generation + text post-edit | visual metaphor 품질 우선 |
| Asset C | image generation + Figma/SVG final text | 재사용 가능한 카드 템플릿화에 유리 |

### 14.4 Sample Governance Notes

- Asset A는 반드시 코드 기반 수치 원본을 보관한다.
- Asset B/C는 생성형 이미지 사용 사실을 내부 제작 노트에 남긴다.
- 고객 납품 전에는 한국어 카피를 이미지에 직접 박지 말고 후편집한다.
- 학부모 대상 교육물은 과장된 "성적 향상 보장" 메시지를 금지한다.
- 모든 고객-facing 카피는 "부모가 먼저 AI를 능동적으로 학습하고 숙련된다"는 1차 포커스를 흐리지 않아야 한다.
