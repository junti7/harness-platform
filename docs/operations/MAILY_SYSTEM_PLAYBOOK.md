# Maily System Playbook
# Version: 1.0
# Date: 2026-05-24

---

## 0. Current Workspace Profile

> 마지막 업데이트: 2026-05-24

- Maily account owner: `junti7@gmail.com`
- Workspace slug (address): `physicalaiweeklykr`
- Base app entry: `https://maily.so/app/guides`
- New newsletter entry: `https://maily.so/new`

운영 원칙:

1. slug 변경 전에는 위 주소를 canonical 운영 식별자로 사용한다.
2. 계정/slug 변경 시 이 섹션을 먼저 갱신하고 나서 스크립트/운영 노트를 수정한다.

---

## 1. Purpose

Substack에서 사용하던 weekly 발행/성과 추적 루프를 Maily에서도 동일하게 운영하기 위한 실행 기준서.

핵심 원칙:

1. Maily는 Substack의 대체가 아니라 병렬 운영 채널이다.
2. `All` 뷰는 통합 기준선으로 유지한다.
3. 트레이딩 운영 판단 레이어는 플랫폼 전환에 종속시키지 않는다.

---

## 2. Day 0 Bootstrap

### 2.1 Metrics ingest 활성화

```bash
source .venv/bin/activate
python scripts/sync_maily_metrics.py --date $(date +%F) --csv data/maily_metrics.sample.csv
```

### 2.2 Dashboard 반영 확인

- `subscriber_snapshots.platform='maily'` 행이 생성되면 대시보드 Maily 상태가 준비중에서 활성 상태로 전환된다.
- `All / Substack` 전환 시 subscriber/engagement 값만 변하는지 확인한다.

---

## 3. Weekly Issue Flow (Maily)

### 3.1 패키지 생성

```bash
source .venv/bin/activate
python scripts/publish_weekly_to_maily.py --issue 1 --date 2026-05-24
```

이미지/그래프 포함:

```bash
source .venv/bin/activate
python scripts/publish_weekly_to_maily.py \
  --issue 1 \
  --date 2026-05-24 \
  --image docs/issues/robotics_cost.png \
  --image docs/issues/tam_breakdown.png
```

참고:

- 존재하지 않는 이미지 경로는 빌드 실패 대신 `skipped_images`로 표시되고 계속 진행된다.
- `.b64` 파일(`docs/issues/chart1.b64`)도 이미지로 자동 임베드된다.

산출물:

- `runtime/maily/issue-*.md` (Maily 에디터 입력용)
- `runtime/maily/issue-*.html` (브라우저에서 열어 rich copy용)
- `runtime/maily/issue-*.json` (운영 메타데이터)
- `newsletter_issues` upsert (`publishing_platform='maily'`, status=`draft`)

붙여넣기 권장:

1. `.html` 파일을 브라우저에서 연다.
2. 렌더된 본문 전체를 복사한다.
3. Maily 에디터 본문 블록에 붙여넣는다.

### 3.2 발행 후 상태 확정

```bash
source .venv/bin/activate
python scripts/publish_weekly_to_maily.py \
  --issue 1 \
  --date 2026-05-24 \
  --mark-published \
  --public-url https://maily.so/...
```

`--mark-published`는 아래 gate가 모두 통과된 경우에만 허용된다:

- VP review approved
- `qa_clear`
- `legal_review_approve`
- `red_team_clear`

---

## 4. Minimal KPI Set

- free_subscribers
- paid_subscribers
- paid_revenue_krw
- opens
- clicks
- replies
- shares
- unsubscribe_count

Maily는 위 지표만 우선 안정화하고, 그다음 자동화/API 연동 확장을 진행한다.
