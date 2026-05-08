#!/bin/bash
# Harness Platform - Mac Mini 초기 셋업 스크립트
# 실행: bash infra/setup_mac_mini.sh

set -e  # 오류 즉시 중단

REPO_DIR="$HOME/projects/harness-platform"
DB_NAME="harness_prod"
PLIST_NAME="com.harness.pipeline"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

echo "======================================"
echo " Harness Platform 셋업 시작"
echo "======================================"

# ── 1. Homebrew ──────────────────────────
echo ""
echo "[1/7] Homebrew 확인..."
if ! command -v brew &>/dev/null; then
    echo "  → Homebrew 설치 중..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "  → 이미 설치됨: $(brew --version | head -1)"
fi

# ── 2. Python 3.12 ───────────────────────
echo ""
echo "[2/7] Python 확인..."
if ! command -v python3.12 &>/dev/null; then
    echo "  → Python 3.12 설치 중..."
    brew install python@3.12
else
    echo "  → 이미 설치됨: $(python3.12 --version)"
fi

# ── 3. PostgreSQL ─────────────────────────
echo ""
echo "[3/7] PostgreSQL 확인..."
if ! command -v psql &>/dev/null; then
    echo "  → PostgreSQL 설치 중..."
    brew install postgresql@16
    brew services start postgresql@16
    echo "  → 서비스 시작 대기..."
    sleep 5
else
    echo "  → 이미 설치됨: $(psql --version)"
    if ! pg_isready -q; then
        echo "  → PostgreSQL 서비스 시작..."
        brew services start postgresql@16
        sleep 5
    fi
fi

echo "  → DB '$DB_NAME' 생성..."
createdb "$DB_NAME" 2>/dev/null && echo "  → 생성 완료" || echo "  → 이미 존재함"

echo "  → 스키마 적용..."
psql "$DB_NAME" < "$REPO_DIR/infra/schema.sql"
echo "  → 스키마 적용 완료"

# ── 4. Ollama + Gemma4 ────────────────────
echo ""
echo "[4/7] Ollama 확인..."
if ! command -v ollama &>/dev/null; then
    echo "  → Ollama 설치 중..."
    brew install ollama
    brew services start ollama
    sleep 5
else
    echo "  → 이미 설치됨"
    if ! curl -s http://localhost:11434 &>/dev/null; then
        echo "  → Ollama 서비스 시작..."
        brew services start ollama
        sleep 5
    fi
fi

echo "  → gemma4:latest 모델 확인..."
if ollama list 2>/dev/null | grep -q "gemma4"; then
    echo "  → 이미 다운로드됨"
else
    echo "  → gemma4:latest 다운로드 중 (시간이 걸립니다)..."
    ollama pull gemma4:latest
fi

# ── 5. 레포 클론 ──────────────────────────
echo ""
echo "[5/7] 레포 확인..."
if [ -d "$REPO_DIR" ]; then
    echo "  → 이미 존재함. git pull 실행..."
    git -C "$REPO_DIR" pull
else
    echo "  → 클론 중..."
    mkdir -p "$HOME/projects"
    git clone https://github.com/junti7/harness-platform "$REPO_DIR"
fi

# ── 6. Python venv + 패키지 ───────────────
echo ""
echo "[6/7] Python 환경 설정..."
cd "$REPO_DIR"

if [ ! -d ".venv" ]; then
    echo "  → venv 생성..."
    python3.12 -m venv .venv
fi

echo "  → 패키지 설치..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet \
    anthropic \
    httpx \
    psycopg2-binary \
    python-dotenv \
    feedparser \
    requests

echo "  → 설치 완료"

# ── 7. .env 파일 ──────────────────────────
echo ""
echo "[7/7] 환경 변수 설정..."
if [ ! -f "$REPO_DIR/.env" ]; then
    cat > "$REPO_DIR/.env" << 'ENV'
# Tier 2 - 로컬 LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma4:latest

# Tier 3 - Premium AI
ANTHROPIC_API_KEY=여기에_입력

# Tier 4 - 배포 채널
NOTION_API_KEY=여기에_입력
NOTION_DATABASE_ID=여기에_입력
SLACK_WEBHOOK_URL=여기에_입력

# 비용 통제
DAILY_COST_LIMIT_USD=1.00

# DB
DATABASE_URL=postgresql://localhost/harness_prod
ENV
    echo "  → .env 파일 생성됨 → API 키를 직접 채워넣으세요: $REPO_DIR/.env"
else
    echo "  → .env 이미 존재함 (덮어쓰지 않음)"
fi

# ── launchd 등록 ──────────────────────────
echo ""
echo "[+] launchd 스케줄 등록 (매일 08:00 KST)..."

mkdir -p "$REPO_DIR/logs"

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$PLIST_NAME</string>

  <key>ProgramArguments</key>
  <array>
    <string>$REPO_DIR/.venv/bin/python3</string>
    <string>$REPO_DIR/run_pipeline.py</string>
  </array>

  <key>WorkingDirectory</key>
  <string>$REPO_DIR</string>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>8</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>

  <key>StandardOutPath</key>
  <string>$REPO_DIR/logs/pipeline.log</string>

  <key>StandardErrorPath</key>
  <string>$REPO_DIR/logs/pipeline.error.log</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
  </dict>
</dict>
</plist>
PLIST

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "  → 등록 완료"

# ── 완료 ──────────────────────────────────
echo ""
echo "======================================"
echo " 셋업 완료"
echo "======================================"
echo ""
echo "다음 단계:"
echo "  1. .env에 API 키 입력: nano $REPO_DIR/.env"
echo "  2. 즉시 실행 테스트:   launchctl start $PLIST_NAME"
echo "  3. 로그 확인:          tail -f $REPO_DIR/logs/pipeline.log"
echo ""
