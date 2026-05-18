"""
Slack Socket Mode Listener — OpenClaw Agent 연동
Harness Platform

모든 DM / @멘션을 openclaw_agent.run()으로 라우팅.
Claude Tool Calling 에이전트가 파일 읽기/쓰기, 스크립트 실행,
Slack 전송, PDF 생성 등을 자율 판단하여 실행.
"""

import os
import sys
import logging
import threading
from pathlib import Path

# launchd 실행 시에도 프로젝트 루트 import가 가능하도록 sys.path 주입
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ⚠️ load_dotenv를 에이전트 import보다 먼저 실행 — 모듈 레벨 환경변수 반영을 위해 필수
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env", override=True)

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from adapters.content.openclaw_agent import run as agent_run, OLLAMA_CHAT_MODEL, OLLAMA_REMOTE_HOST, OLLAMA_HOST
from core.reader_feedback import classify_feedback, upsert_reader_profile, record_feedback
from adapters.content.vp_review_card import parse_vp_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [slack_listener] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
CEO_SLACK_USER_ID = os.environ.get("SLACK_CEO_USER_ID", "")
VP_SLACK_USER_ID = os.environ.get("SLACK_VP_USER_ID", "")

if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN is not set in .env")
if not SLACK_APP_TOKEN:
    raise RuntimeError("SLACK_APP_TOKEN (xapp-...) is not set in .env")

app = App(token=SLACK_BOT_TOKEN)


@app.event("app_mention")
def handle_mention(event, say, logger):
    user = event.get("user", "unknown")
    raw_text = event.get("text", "")
    text = " ".join(w for w in raw_text.split() if not w.startswith("<@")).strip()
    channel = event.get("channel", "")
    logger.info(f"[app_mention] user={user} channel={channel} text={text!r}")

    if CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID:
        say(text=":thinking_face: 처리 중...", thread_ts=event.get("ts"))
        session_id = f"slack:{channel}:{user}"
        response = agent_run(text, dm_channel_id=channel, requester_user_id=user, session_id=session_id)
        say(text=response, thread_ts=event.get("ts"))
    else:
        _handle_reader_feedback(user, text, source_channel=f"slack_mention:{channel}", say=say,
                                thread_ts=event.get("ts"), logger=logger)


@app.event("message")
def handle_dm(event, say, logger):
    if event.get("bot_id") or event.get("subtype"):
        return
    if not event.get("channel", "").startswith("D"):
        return

    user = event.get("user", "unknown")
    text = event.get("text", "")
    channel = event.get("channel", "")
    logger.info(f"[DM] user={user} text={text!r}")

    if not CEO_SLACK_USER_ID or user == CEO_SLACK_USER_ID:
        say(text=":thinking_face: 처리 중...")
        session_id = f"slack:{channel}:{user}"
        response = agent_run(text, dm_channel_id=channel, requester_user_id=user, session_id=session_id)
        say(text=response)
    elif VP_SLACK_USER_ID and user == VP_SLACK_USER_ID:
        _handle_vp_dm(user, text, say=say, logger=logger)
    else:
        _handle_reader_feedback(user, text, source_channel=f"slack_dm:{channel}", say=say,
                                thread_ts=None, logger=logger)


def _handle_vp_dm(user: str, text: str, say, logger):
    """VP DM 처리: 검토 응답이면 content_reviews에 기록, 아니면 reader_feedback."""
    import re
    issue_match = re.search(r"이슈\s*ID\s*:\s*(\d+)", text)
    if issue_match:
        issue_id = int(issue_match.group(1))
        review_text = re.sub(r"이슈\s*ID\s*:\s*\d+", "", text).strip()
        result = parse_vp_response(review_text, issue_id, user)
        if result:
            rec = result["recommendation"]
            replies = {
                "ready": "✅ 검토 완료! 발행 승인 기록됨.",
                "revise": f"🔁 수정 요청 기록됨. 메모: {result['jargon_notes'] or '(없음)'}",
                "hold": "⏸ 보류 기록됨.",
            }
            say(text=replies.get(rec, "기록 완료"))
            logger.info(f"[vp_review] 응답 처리: issue={issue_id} rec={rec}")
            return
    _handle_reader_feedback(user, text, source_channel="slack_dm:vp", say=say,
                            thread_ts=None, logger=logger)


def _handle_reader_feedback(user: str, text: str, source_channel: str, say, thread_ts, logger):
    """CEO가 아닌 사용자의 메시지를 독자 피드백으로 분류·저장."""
    if not text.strip():
        return
    try:
        classification = classify_feedback(text)
        customer_id = upsert_reader_profile(f"slack:{user}")
        record_feedback(customer_id, text, classification, source_channel)
        logger.info(f"[reader_feedback] user=slack:{user} intent={classification['intent']}")

        intent = classification["intent"]
        if intent == "question":
            reply = "질문 감사합니다! 다음 이슈에서 다뤄볼게요. 🙏"
        elif intent == "praise":
            reply = "응원해주셔서 감사합니다! 😊"
        elif intent == "complaint":
            reply = "불편하셨군요. 피드백 반영해서 개선할게요. 감사합니다."
        elif intent == "unsubscribe_signal":
            reply = "구독 관련 문의는 Substack 이메일을 통해 처리됩니다. 감사합니다."
        else:
            reply = "메시지 감사합니다! 📬"

        kwargs = {"text": reply}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        say(**kwargs)
    except Exception as exc:
        logger.error(f"[reader_feedback] 저장 실패: {exc}")


if __name__ == "__main__":
    logger.info("Harness Slack Listener 시작 (OpenClaw Agent Mode)")

    # Ollama 모델 사전 로드 (백그라운드) — 첫 메시지 콜드 스타트 방지
    def _prewarm_ollama():
        import time, json, subprocess

        time.sleep(15)  # launchd 시작 직후 네트워크 라우팅 안정화 대기

        def _curl_probe(host: str) -> bool:
            """curl로 Ollama 온라인 여부 확인 (launchd ARP 문제 우회)"""
            try:
                r = subprocess.run(
                    ["curl", "-sf", "--max-time", "5", f"{host}/api/tags"],
                    capture_output=True, timeout=7
                )
                return r.returncode == 0
            except Exception:
                return False

        def _curl_warmup(host: str) -> bool:
            """curl로 모델 warmup"""
            payload = json.dumps({
                "model": OLLAMA_CHAT_MODEL,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "keep_alive": 3600,
            })
            try:
                r = subprocess.run(
                    ["curl", "-sf", "--max-time", "35",
                     "-X", "POST", f"{host}/api/chat",
                     "-H", "Content-Type: application/json",
                     "-d", payload],
                    capture_output=True, timeout=40
                )
                return r.returncode == 0
            except Exception:
                return False

        candidates = []
        if OLLAMA_REMOTE_HOST:
            candidates.append((OLLAMA_REMOTE_HOST, "MBP"))
        candidates.append((OLLAMA_HOST, "Local"))

        for host, label in candidates:
            for attempt in range(3):
                if _curl_probe(host):
                    if _curl_warmup(host):
                        logger.info(f"[prewarm] {label} Ollama({OLLAMA_CHAT_MODEL}) 모델 로드 완료 ✅")
                    break
                wait = 10 * (attempt + 1)
                if attempt < 2:
                    logger.info(f"[prewarm] {label} 재시도 {attempt+1}/3 — {wait}초 대기")
                    time.sleep(wait)
                else:
                    logger.info(f"[prewarm] {label} Ollama 불가 — 건너뜀")

    threading.Thread(target=_prewarm_ollama, daemon=True).start()

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
