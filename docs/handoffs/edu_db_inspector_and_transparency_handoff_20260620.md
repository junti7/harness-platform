# Handoff — Edu DB Inspector + Transparency Stack (2026-06-20)

> 작성일: 2026-06-20
> 목적: `/clear` 전 fresh start용 인수인계
> 범위: edu DB transparency, Harness OS inspector UX, xlsx export, mac mini deploy/cleanup

---

## 0. 한 줄 요약

이번 라운드의 핵심은 `edu DB가 black box처럼 보이는 문제`를 깨기 위해:

- DB 구조/lineage를 문서와 API로 드러내고
- Harness OS 안에 `Edu DB Inspector` 메뉴를 넣고
- 선택한 object 전체 row를 `xlsx`로 내려받을 수 있게 만든 것

입니다.

다만 **중요한 현재 상태**가 하나 있습니다.

- 실제 mac mini DB에는 기대했던 P1 knowledge schema가 완전히 올라와 있지 않습니다.
- 특히 `edu_knowledge_items`, `edu_rag_accumulation`, `edu_knowledge_items_customer_facing` 부재가 transparency tooling으로 확인됐습니다.

즉 현재 inspector는 “운영 중인 live edu knowledge DB”를 예쁘게 보여주는 수준이 아니라,
**실제 DB가 코드 기대 상태와 어긋나 있다는 사실까지 드러내는 관측 도구**입니다.

---

## 1. 이번에 만든 것

### 1.1 문서 / transparency artifact

추가/정리 파일:

- [docs/education/EDU_DB_TRANSPARENCY_PLAN.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_DB_TRANSPARENCY_PLAN.md)
- [scripts/inspect_edu_db.py](/Users/juntae.park/projects/harness-platform/scripts/inspect_edu_db.py)
- [scripts/export_edu_transparency_bundle.py](/Users/juntae.park/projects/harness-platform/scripts/export_edu_transparency_bundle.py)
- `docs/reviews/edu_db_transparency/*`

역할:

- 기대 schema vs 실제 schema 비교
- table/view/column/index/row_count/sample row 덤프
- recent `pipeline_runs` / `dead_letter_queue` 노출
- retrieval path와 lineage를 운영자 관점에서 설명

### 1.2 Harness OS 내 inspector UI

핵심 파일:

- [harness-os/frontend/src/pages/EduDbInspectorPage.tsx](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/pages/EduDbInspectorPage.tsx)

이 페이지는 Harness OS 메뉴에서 들어가는 crude/raw inspector입니다.

주요 기능:

- object list
- 선택 object의 raw structure
- columns dataframe
- sample rows dataframe
- selected sample row raw JSON
- object meaning / analytics use 설명
- full xlsx export 버튼

### 1.3 backend debug / export API

핵심 파일:

- [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)

추가/사용 endpoint:

- `/api/admin/edu/db/transparency`
- `/api/admin/edu/db/object`
- `/api/admin/edu/db/object-export.xlsx`
- `/api/admin/edu/db/retrieval-debug`

### 1.4 xlsx full export

Inspector sample rows는 기본 `limit=20` 이라 큰 테이블 전체를 볼 수 없어서,
선택 object 전체 row를 엑셀로 내리는 기능을 붙였습니다.

예:

- `dead_letter_queue` 총 `3929 rows`여도 전체 export 가능

다운로드 결과:

- workbook sheets: `meta`, `columns`, `rows`

---

## 2. 실제로 확인된 운영 상태

Transparency tooling으로 확인된 mac mini DB 상태:

실제 테이블 예시:

- `dead_letter_queue`
- `pipeline_runs`
- `edu_customers`
- `edu_cases`
- `edu_case_turns`
- `edu_case_snapshots`
- `edu_case_offers`
- `edu_magic_links`
- `edu_conversation_log`

빠진 기대 object:

- `edu_knowledge_items`
- `edu_rag_accumulation`
- `edu_knowledge_items_customer_facing`

의미:

- 코드상 customer-facing retrieval은 `edu_knowledge_items_customer_facing` view를 읽도록 설계되어 있음
- 하지만 실제 DB에는 그 view가 없음
- 따라서 이전 simulation artifact를 `현재 live DB-backed 동작 증거`로 읽으면 안 됨

즉 지금 inspector의 가장 큰 가치 중 하나는,
**“무엇이 있나”뿐 아니라 “무엇이 아직 실제 DB에 없나”를 눈으로 보여준다는 점**입니다.

---

## 3. UI/UX에서 이미 한 수정

`Edu DB Inspector`는 여러 번 방향을 바꿨습니다.

주요 변경 흐름:

- 초기 카드형/요약형 뷰
- table-first raw browser로 전환
- single-column 강제
- narrow screen overflow 완화
- object meaning 설명 추가
- sample rows는 giant raw text 대신 preview 중심으로 전환
- full xlsx export 추가

관련 최근 commit 흐름:

- `869c6a7` — Make edu DB inspector table-first
- `9117355` — Rework edu DB inspector into raw table browser
- `5126e2a` — Make edu DB inspector aggressively table-first
- `eee75c6` — Fix edu DB inspector overflow on narrow screens
- `6a033a0` — Force single-column edu DB inspector layout
- `2b8d4bc` — Explain edu DB objects and widen raw row scrolling
- `6117d97` — Add edu DB xlsx export and inspector download

---

## 4. 아직 남아 있는 문제

사용자 피드백 기준 unresolved issue:

1. 좁은 화면에서 우측 상세 영역 일부가 여전히 잘릴 수 있음
2. 내부 horizontal scroll이 기대대로 동작하지 않는 구간이 있었음
3. object meaning 설명이 실제 사용자 화면에서 안 보인 시점이 있었음
4. 전반적으로 “pandas dataframe처럼 단순하고 직관적인 raw browser”에 아직 못 미친다는 피드백이 있었음

즉 **기능 자체는 많이 붙었지만, UI 완성도는 아직 미완료**입니다.

다음 세션에서는 이걸 “대시보드”가 아니라
`진짜 raw dataframe browser`로 더 단순화하는 게 맞습니다.

---

## 5. xlsx export 확인 사실

실제로 확인한 endpoint 예:

- `/api/admin/edu/db/object-export.xlsx?name=dead_letter_queue`

검증 메모:

- `200 OK`
- `content-disposition: attachment; filename="dead_letter_queue_full_export.xlsx"`
- `content-length: 891250`
- body starts with `PK` (xlsx zip signature)

즉 현재는 sample 20개만 보는 게 아니라, 전체 object를 엑셀로 내려받아 직접 분석 가능합니다.

---

## 6. mac mini 반영 / 정리 상태

### 6.1 git 상태

이전에는 mac mini 작업트리가 많이 더러웠고 unrelated 변경이 섞여 있었습니다.

안전하게 정리한 방법:

1. dirty state를 backup branch에 보존
2. backup commit 생성
3. `main`을 `origin/main` 기준으로 hard reset
4. untracked clean

정리 결과:

- mac mini `main` HEAD: `6117d97`
- `origin/main` HEAD: `6117d97`
- `git status`: clean

백업:

- branch: `backup/macmini-cleanup-20260620_094703`
- backup commit: `7d06f44`

즉 필요하면 이전 mac mini dirty 상태를 이 branch에서 다시 복구할 수 있습니다.

### 6.2 MBP / origin 상태

이 라인의 공식 commit/push 기준점:

- `6117d97` — `Add edu DB xlsx export and inspector download`

당시 MBP에서는 해당 변경 3파일을 commit/push 했고, mac mini에는 그 상태를 배포했습니다.

주의:

- 그 이후 MBP 작업트리는 다시 dirty일 수 있음
- `/clear` 후에는 반드시 현재 `git status`를 다시 보고 시작할 것

---

## 7. 현재 중요한 파일

우선적으로 다시 읽을 파일:

- [docs/education/EDU_DB_TRANSPARENCY_PLAN.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_DB_TRANSPARENCY_PLAN.md)
- [scripts/inspect_edu_db.py](/Users/juntae.park/projects/harness-platform/scripts/inspect_edu_db.py)
- [scripts/export_edu_transparency_bundle.py](/Users/juntae.park/projects/harness-platform/scripts/export_edu_transparency_bundle.py)
- [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)
- [harness-os/frontend/src/pages/EduDbInspectorPage.tsx](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/pages/EduDbInspectorPage.tsx)

찾아볼 키워드:

- `EduDbInspectorPage`
- `/api/admin/edu/db/object`
- `/api/admin/edu/db/object-export.xlsx`
- `OBJECT_METADATA`
- `Download full xlsx`

---

## 8. 다음 세션에서 바로 할 일

가장 자연스러운 다음 작업 순서:

1. 현재 MBP의 실제 `git status` 재확인
2. mac mini에서 현재 inspector 화면을 실제 브라우저 기준으로 다시 열어 문제 재현
3. layout bug를 page 단위가 아니라 상위 app shell 포함해서 확인
4. inspector를 더 단순한 raw dataframe browser로 재설계
5. 필요하면 `sample rows`를 HTML table이 아니라 virtualization/grid 또는 pinned-column 방식으로 교체

UX 방향은 이렇게 가져가는 게 맞습니다:

- 카드 제거
- 요약 최소화
- object 클릭
- 바로 아래에 `columns df`
- 그 아래에 `full rows preview / pagination / export`
- wide data는 무조건 내부 scroll
- raw JSON은 보조 탭으로 내리기

---

## 9. 중요한 해석 주의

이 세션에서 드러난 가장 중요한 사실은 두 개입니다.

1. `Edu DB Inspector`는 이제 존재한다.
2. 그런데 inspector가 보여준 실제 DB 상태는, 우리가 기대한 P1 schema와 다르다.

따라서 다음 세션에서 “UI polish”만 하면 되는 게 아니라,
**실제 DB schema drift 문제와 inspector UX 문제를 분리해서 다뤄야 합니다.**

둘은 별개 이슈입니다.

