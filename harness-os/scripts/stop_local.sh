#!/bin/sh
set -eu

for port in 8000 5173 5174; do
  pid="$(lsof -t -iTCP:${port} -sTCP:LISTEN || true)"
  if [ -n "${pid}" ]; then
    kill "${pid}"
    echo "Stopped process on :${port} (pid=${pid})"
  else
    echo "No running process on :${port}"
  fi
done
