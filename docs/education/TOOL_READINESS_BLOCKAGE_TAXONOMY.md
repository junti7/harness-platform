# EDU 도구 준비 막힘 분류

> 작성일: 2026-06-13

---

## 1. 목적

`blocked_reason`를 자유 텍스트로만 남기지 않고, 운영자가 집계 가능한 taxonomy로 표준화한다.

---

## 2. 분류

- `app_not_found`
- `download_failed`
- `install_blocked`
- `icon_not_visible`
- `app_launch_failed`
- `login_ui_confusion`
- `account_creation_blocked`
- `first_input_confusion`
- `copy_paste_confusion`
- `file_picker_confusion`
- `managed_device_restriction`
- `inapp_browser_limitation`
- `unknown`

---

## 3. 활용

operator dashboard는 최소 아래 집계를 보여야 한다.

- platform별 막힘 순위
- selected_llm별 막힘 순위
- 단계별 이탈률
