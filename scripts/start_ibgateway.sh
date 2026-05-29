#!/bin/bash
# IBKR Client Portal Web API Gateway 시작 스크립트
# Mac Mini 전용 — 포트 5001, 페이퍼 트레이딩 모드
# 실행 전 ~/ibgateway/ 에 clientportal.gw 압축 해제 필요

set -euo pipefail

GATEWAY_DIR="$HOME/ibgateway"
CONF_FILE="$HOME/projects/harness-platform/configs/ibgateway/conf.yaml"
JAVA_BIN="/opt/homebrew/opt/openjdk@17/bin/java"
LOG_FILE="$HOME/ibgateway/gateway.log"

# Java 경로 확인
if [ ! -f "$JAVA_BIN" ]; then
    JAVA_BIN=$(which java 2>/dev/null || echo "")
fi
if [ -z "$JAVA_BIN" ] || [ ! -f "$JAVA_BIN" ]; then
    echo "[ERROR] Java를 찾을 수 없습니다. brew install openjdk@17 실행 필요"
    exit 1
fi

# Gateway 파일 존재 확인
if [ ! -f "$GATEWAY_DIR/bin/run.sh" ] && [ ! -f "$GATEWAY_DIR/run.sh" ]; then
    echo "[ERROR] IB Gateway 미설치"
    echo "  1. https://www.interactivebrokers.com/en/trading/ibkr-api.php 접속"
    echo "  2. 'Client Portal Web API' → 'Download the IBKR Web API' 다운로드"
    echo "  3. 압축 해제 → $GATEWAY_DIR/ 에 붙여넣기"
    echo "  예: unzip clientportal.gw.zip -d $GATEWAY_DIR"
    exit 1
fi

# conf.yaml 복사 (gateway root 디렉토리에 필요)
cp "$CONF_FILE" "$GATEWAY_DIR/root/conf.yaml" 2>/dev/null || true

# 실행
echo "[$(date '+%Y-%m-%d %H:%M:%S')] IB Gateway 시작 (포트 5001, 페이퍼 트레이딩)"

if [ -f "$GATEWAY_DIR/bin/run.sh" ]; then
    export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
    cd "$GATEWAY_DIR"
    exec bash bin/run.sh root/conf.yaml >> "$LOG_FILE" 2>&1
else
    cd "$GATEWAY_DIR"
    exec bash run.sh root/conf.yaml >> "$LOG_FILE" 2>&1
fi
