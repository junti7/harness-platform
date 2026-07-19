# Harness OS 재고가치회복형 커머스 Dashboard UX 구현안

- Date: 2026-07-19
- Source plan: `docs/strategy/LIQUIDATION_RECOMMERCE_MALL_OPPORTUNITY_PLAN_20260719.md`
- Target: Mac Mini Harness OS internal dashboard
- Status: implementation candidate
- Scope: Phase 0~2 opportunity discovery control plane
- Explicitly out of scope: 상품 매입, 결제, 주문, 환불, marketplace API, 외부 공개, approval 자동발행

## 1. Feasibility verdict

현시점 구현 가능하다.

기존 Harness OS는 React/Vite frontend, FastAPI backend, role session, Mac Mini launchd, `scripts/deploy_to_macmini.sh` 배포 경로를 갖고 있다. production DB에 미구현 roadmap object를 가장하지 않고 `runtime/recommerce/workspace.json`에 v1 workspace를 저장할 수 있다. 파일은 git 추적 대상이 아니며 `core.atomic_io.update_json_atomic`으로 latest-disk delta update를 보장한다.

현재 구현할 수 없는 범위:

- 실제 marketplace 판매·주문·정산 자동연동
- 통신판매·세무·제품인증 완료 판정 자동화
- `capital_action_approve` 또는 다른 canonical approval 자동발행
- paid demand를 검증 완료로 표시하는 기능

## 2. UX objective

초보 운영자가 dashboard에서 아래 질문에 바로 답하게 한다.

1. 지금 어느 Phase인가?
2. 다음 행동 하나는 무엇인가?
3. 아직 막힌 gate는 무엇인가?
4. 공급처와 SKU 후보가 몇 개인가?
5. 이 SKU는 모든 비용 반영 후 남는가?
6. 본업 시간·재고손실 한도를 넘고 있는가?

## 3. Information architecture

TopBar에 `사업 > 재고가치회복 Mall` 메뉴를 추가한다. 모바일 더보기 sheet에도 같은 메뉴를 노출한다.

Page layout:

1. Hero/status band
   - `opportunity_candidate`
   - Red Team 상태는 별도 감사 artifact에서만 판정하며 runtime UI/API에는 승인 상태를 하드코딩하지 않음
   - 현재 허용: 조사·인터뷰·무매입 Pretotyping
   - 금지: 매입·판매·유료광고
2. Safety KPI cards
   - 현재 Phase
   - checklist 진행률
   - 공급처 수 / 증빙 가능 공급처 수
   - SKU 후보 수 / score 30+ 수
   - 주간 투입시간 / 6시간 cap
3. Phase rail
   - Phase 0~4
   - Phase 0~2만 active workspace
   - Phase 3~4는 locked, required gates 표시
4. Stop/Go banner
   - 본업 시간 초과, 보수 margin 음수, 증빙 미확인 등 block reason
5. Phase 0 checklist
   - 역할분담, 시간한도, 금지목록, 손익 sheet, 공급처 질문, 후보목록, Day 10 회의
6. Supplier workspace
   - name, contact status, evidence status, available quantity, quote valid until, note
7. SKU candidate workspace
   - name, supplier, allowed category, unit purchase cost, conservative sale price
   - platform fee, inbound/outbound shipping, packaging, ad/coupon, return/defect reserve, labor, aging loss, dispute/tax reserve
   - evidence/safety status
   - contribution amount/rate 자동계산
   - score 8개 축 자동합계
8. Guardrail/footer
   - dashboard data는 market validation 아님
   - 승인 없는 매입·판매 금지

## 4. Interaction contract

Allowed writes:

- Phase 0 checklist toggle
- weekly hours update, 0~168
- supplier candidate add
- SKU candidate add
- supplier/SKU delete

Not allowed:

- gate clear toggle
- approval creation
- purchase/sell/reserve action
- paid-demand number entry before authorized experiment
- state import from untrusted external content

Every write:

- requires `X-Harness-Secret`
- requires valid `X-Harness-Auth` role token
- requires role `ceo`; VP is read-only in v1
- validates enum/range/string length server-side
- records `updated_at`, `updated_by`
- changes only owned field/delta through `update_json_atomic`
- includes `expected_version`; stale version returns HTTP 409 and fresh workspace

The existing internal secret remains a deployment preflight, not user authorization. New write authorization is decided from the signed role token on the server. Custom headers and same-origin deployment are required; CORS origins must not be widened for this feature.

## 5. Backend contract

### `GET /api/recommerce/workspace`

Returns:

```json
{
  "opportunity": {},
  "guardrails": {},
  "phases": [],
  "checklist": [],
  "suppliers": [],
  "sku_candidates": [],
  "metrics": {},
  "stop_reasons": [],
  "next_action": ""
}
```

### `POST /api/recommerce/workspace`

Request:

```json
{
  "expected_version": 3,
  "action": "toggle_checklist|set_weekly_hours|add_supplier|delete_supplier|add_sku|delete_sku",
  "payload": {}
}
```

Response returns complete normalized workspace and incremented `workspace_version`. Server generates UUIDs; client IDs are never accepted for add. Delete uses an existing server UUID only.

Inside one `update_json_atomic` lock, backend must:

1. read fresh disk state
2. compare fresh `workspace_version` to request `expected_version`
3. reject mismatch without mutation
4. append/delete/toggle only the addressed UUID/key
5. increment version

Whole-array replacement is forbidden.

## 6. Persistence contract

- default: `runtime/recommerce/workspace.json`
- override: `HARNESS_RECOMMERCE_WORKSPACE_PATH`
- atomic lock/update: `core.atomic_io.update_json_atomic`
- all list mutations use UUID append/delete inside the lock; no stale list replacement
- unknown or corrupt state: normalize to safe empty workspace
- runtime state never committed
- no personal contact detail or account/payment data stored
- deploy script receives code paths only and must never receive `runtime/`
- deployment verification records pre/post SHA-256, supplier count, SKU count, checklist state and workspace version
- mismatch blocks completion and triggers restoration from a timestamped local backup made before deploy

## 7. Computed metrics

```text
full_variable_cost
= unit_purchase_cost
+ platform_fee
+ inbound_shipping
+ outbound_shipping
+ packaging_cost
+ ad_coupon_cost
+ return_defect_reserve
+ labor_cost
+ aging_markdown_loss
+ dispute_tax_reserve

contribution = conservative_sale_price - full_variable_cost
contribution_rate = contribution / conservative_sale_price
qualified_supplier = evidence_status == verified
qualified_sku = total_score >= 30 AND evidence_score >= 4
```

All cost fields are required, numeric, non-negative, and independently visible. Zero is allowed only after the operator checks `해당 비용 없음 확인`; default blank never means zero.

Stop reasons:

- weekly_hours > 6
- any SKU has evidence/safety score < 4 but status marked candidate-ready
- any SKU contribution rate < 20%

The UI must not claim `go`, `통과`, `검증`, or `수요 확인`. It may show only `비용검토 조건 충족`; this means arithmetic inputs passed, not market validation. Human approval remains required.

## 7A. Product safety hard block

Server accepts only v1 allowlist categories:

- stationery
- storage_organization
- non_electric_household_small_goods
- adult_hobby_supplies_non_regulated

Server rejects category/title/note containing restricted-product indicators including child/baby, electric/battery, food/supplement, cosmetic/medical, expiration-date, luxury/brand-authenticity, apparel/shoes, large/installable. Korean and English indicator lists are tested. This is a conservative screen, not a legal classification.

No API action exists to mark a SKU `candidate-ready`. Evidence/safety fields are observations only. Promotion requires a future reviewed implementation.

## 7B. Phase and evidence separation

- current phase is derived from immutable implementation config: Phase 0~2 workspace only
- no `set_phase`, `unlock`, `approve`, `record_paid_demand`, or gate mutation action exists
- Phase 3/4 cards are explanatory locked cards only
- approval artifacts are displayed as requirements, never editable or inferred
- interest signals, if added later, need a separate dataset from paid demand
- v1 stores no CTR, reservation, order, paid-demand, conversion, or revenue fields
- therefore this dashboard cannot render a false paid-market-validation state

## 8. Visual/accessibility rules

- existing Harness calm mission-control tokens reused
- no emoji-dependent meaning
- mobile single-column forms
- minimum touch target 44px
- tables become stacked cards below 760px
- status uses text + color, never color alone
- WCAG 2.1 AA contrast: 4.5:1 normal text, 3:1 large text and controls
- all interactions keyboard reachable with visible `:focus-visible`
- modal use avoided; inline errors linked through `aria-describedby`
- save/conflict/server errors use `role="alert"` or `aria-live="polite"`
- loading state preserves focus; 409 conflict reload announces changed data
- Korean plain-language labels with exact approval values in secondary text
- light/dark mode support

## 9. Verification plan

Local:

- backend syntax
- focused API/unit tests for normalization, calculations, auth, atomic persistence
- frontend lint/build
- browser desktop/mobile render and interaction

Mac Mini:

- deploy only through `scripts/deploy_to_macmini.sh`
- backend/frontend launchd active
- authenticated GET/POST API against production entrypoint without logging secrets
- production frontend bundle contains page marker
- actual dashboard page desktop/mobile browser verification
- Mac Mini worktree/HEAD/status verification
- pre/post runtime SHA-256, record counts and version parity
- backend `/api/health`, frontend HTTP 200, new API HTTP 200
- deploy failure uses existing deploy script rollback; runtime mismatch restores predeploy backup before service completion report

## 10. Red Team questions

1. Does dashboard accidentally authorize business execution?
2. Can stale concurrent writes lose supplier/SKU/checklist data?
3. Can users enter unsafe products and misread them as approved?
4. Do computed margins omit labor, inventory-loss, tax, or dispute costs?
5. Does UX turn small samples into false market validation?
6. Can Phase 3/4 be reached without legal/pre-mortem/QA/experiment/capital gates?
7. Does new page distract from Harness core priorities?

## 10A. Core-priority protection

- page header always shows `보조 discovery track`
- weekly hours > 6 creates hard red stop banner
- no automatic notifications, scheduled jobs, premium model calls, or homepage KPI promotion
- menu lives under `사업`, not Home primary KPI row
- dashboard does not alter weekly issue or creator-subscription data

## 11. Completion boundary

Implementation is complete only when the production Mac Mini page and API are verified. Code/build success alone is insufficient.
