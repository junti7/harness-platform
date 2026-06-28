# Staff Penalty & Reward Ledger

| 날짜 | 대상 | 사유 | 구분 | 점수 | 누적 점수 | 비고 |
|------|------|------|------|------|-----------|------|
| 2026-05-10 | 비서실장 (Codex) | 반복적인 리포트 이미지 누락 및 허위 승인 | Penalty | -100 | -100 | CEO 엄중 경고 |
| 2026-05-10 | QA Team (Claude/Gemini/Gemma) | 이미지 정합성 검수 태만 | Penalty | -50 | -50 | |
| 2026-05-10 | 비서실장 (Codex) | 우측 텍스트 잘림 현상 방치 (Attempt #1~9) | Penalty | -50 | -150 | |
| 2026-06-28 | Codex | EDU coach 수정 완료 보고 전 실제 사용자 진입점 검증 미흡, mock 파일럿을 충분한 검증으로 오판 | Penalty | -100 | -250 | 재발방지: `scripts/agent_completion_guard.py` 통과 전 완료 보고 금지. 동일 유형 재발 시 -200 + 다음 3개 코드 변경은 Claude+Gemini Red Team artifact 필수 |
