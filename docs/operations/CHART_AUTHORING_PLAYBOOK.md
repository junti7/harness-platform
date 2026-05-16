# CHART_AUTHORING_PLAYBOOK.md

# Version: 1.0 | Date: 2026-05-10
# 상위 규약: docs/product/PLATFORM.md, CLAUDE.md, docs/operations/QA_PLAYBOOK.md

---

## 1. Purpose

`Physical AI Weekly` PDF에 들어가는 차트, 다이어그램, 컨셉 이미지의 작성 기준과 빌드 파이프라인을 정의한다. 이 문서는 (1) 차후 시행착오 반복을 막고, (2) Codex 외 다른 LLM(Claude, Gemini, GPT reasoning, local model)에게 동일한 작업을 위임할 때 reference로 사용한다.

이 playbook을 따른 차트는 paid 발행 전 `qa_clear` + `legal_review_approve` 게이트를 통과해야 한다.

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
