#!/usr/bin/env bash
# 벤치 조립도 HTML → PNG 렌더.
#
# 왜 스크립트로 두는가: PNG 만 커밋하면 몇 달 뒤 "이 그림을 어떻게 고치지?"가 된다.
# HTML 이 원본이고 PNG 는 산출물이다. 배선을 바꾸면 HTML 을 고치고 이 스크립트를 다시 돌린다.
# 순서는 항상 BENCH_WIRING.md → HTML → render.sh → 커밋.
#
# 사용: ./render.sh            (전체)
#       ./render.sh 03         (03 으로 시작하는 파일만)
#
# 의존: Google Chrome (headless 렌더), 그리고 바닥 여백 자동 트림에 프로젝트 .venv 의 Pillow.
#       Pillow 가 없으면 트림만 건너뛰고 렌더는 정상 진행한다(경고 1줄).
set -euo pipefail

cd "$(dirname "$0")"
repo_root="$(cd ../../.. && pwd)"

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
PY="${PY:-$repo_root/.venv/bin/python}"
SCALE="${SCALE:-3}"          # 3 = 폰에서 확대해도 단자대 번호가 읽히는 배율
WIDTH=960                    # _diagram.css 의 body width 와 반드시 일치
CANVAS_H="${CANVAS_H:-2600}" # 넉넉히 잡고 아래에서 잘라낸다

if [ ! -x "$CHROME" ]; then
  echo "✖ Chrome 을 찾을 수 없습니다: $CHROME" >&2
  echo "  CHROME=/path/to/chrome ./render.sh 로 지정하세요." >&2
  exit 1
fi

filter="${1:-}"
shopt -s nullglob
rendered=0

for html in [0-9][0-9]_*.html; do
  [ -n "$filter" ] && case "$html" in "$filter"*) ;; *) continue ;; esac
  png="${html%.html}.png"

  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor="$SCALE" \
    --window-size="$WIDTH,$CANVAS_H" \
    --default-background-color=FFFFFFFF \
    --screenshot="$png" "file://$PWD/$html" >/dev/null 2>&1

  [ -s "$png" ] || { echo "✖ 렌더 실패: $html" >&2; exit 1; }

  # 캔버스를 넉넉히 잡았으므로 내용 아래 흰 여백을 잘라낸다. 폭은 건드리지 않는다.
  if [ -x "$PY" ] && "$PY" -c "import PIL" >/dev/null 2>&1; then
    "$PY" - "$png" "$SCALE" <<'PYTRIM'
import sys
from PIL import Image, ImageChops

path, scale = sys.argv[1], int(sys.argv[2])
im = Image.open(path).convert("RGB")
bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
if bbox:
    bottom = min(im.height, bbox[3] + 20 * scale)   # body 하단 padding 만큼만 남긴다
    if bottom < im.height:
        im.crop((0, 0, im.width, bottom)).save(path)
PYTRIM
  else
    echo "⚠ Pillow 없음 → 바닥 여백 트림 생략 ($png)" >&2
  fi

  echo "✓ $png  $(du -h "$png" | cut -f1)"
  rendered=$((rendered + 1))
done

[ "$rendered" -gt 0 ] || { echo "✖ 렌더 대상이 없습니다 (filter='$filter')" >&2; exit 1; }
echo "완료: $rendered 장"
