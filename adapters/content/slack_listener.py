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
from logging.handlers import RotatingFileHandler
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
from adapters.content.slack_format import to_slack_mrkdwn
from core.reader_feedback import classify_feedback, upsert_reader_profile, record_feedback
from adapters.content.vp_review_card import parse_vp_response
from agents.registry import find_mentioned_personas, get_active_personas

import re

_LOG_FILE = _PROJECT_ROOT / "logs" / "slack_listener.log"
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_fmt = logging.Formatter("%(asctime)s [slack_listener] %(levelname)s %(message)s")

# 중복 핸들러 방지: RotatingFileHandler가 아직 없을 때만 추가
if not any(isinstance(h, RotatingFileHandler) for h in _root_logger.handlers):
    _rotating_handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    _rotating_handler.setFormatter(_fmt)
    _root_logger.addHandler(_rotating_handler)

# StreamHandler: 기존 basicConfig StreamHandler가 없을 때만 추가
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in _root_logger.handlers):
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_fmt)
    _root_logger.addHandler(_stream_handler)

logger = logging.getLogger(__name__)

# ── Slack event dedup (retry guard) ──────────────────────────────────────────
# Slack retries event delivery when the handler takes > 3 s.  Without dedup,
# a long agent_run() call causes multiple identical DMs to be processed.
import time as _time
import threading as _threading

_SEEN_EVENTS: dict[str, float] = {}
_SEEN_LOCK = _threading.Lock()
_EVENT_TTL = 120.0  # seconds


def _is_duplicate_event(event: dict) -> bool:
    key = f"{event.get('user', '')}:{event.get('ts', '')}:{event.get('client_msg_id', '')}"
    now = _time.monotonic()
    with _SEEN_LOCK:
        # purge stale entries
        stale = [k for k, v in _SEEN_EVENTS.items() if now - v > _EVENT_TTL]
        for k in stale:
            del _SEEN_EVENTS[k]
        if key in _SEEN_EVENTS:
            return True
        _SEEN_EVENTS[key] = now
        return False


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
    if _is_duplicate_event(event):
        logger.info("[app_mention] 중복 이벤트 무시 (Slack retry)")
        return

    user = event.get("user", "unknown")
    raw_text = event.get("text", "")
    text = " ".join(w for w in raw_text.split() if not w.startswith("<@")).strip()
    channel = event.get("channel", "")
    logger.info(f"[app_mention] user={user} channel={channel} text={text!r}")

    if CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID:
        say(text=":thinking_face: 처리 중...", thread_ts=event.get("ts"))
        session_id = f"slack:{channel}:{user}"
        response = agent_run(text, dm_channel_id=channel, requester_user_id=user, session_id=session_id)
        say(text=to_slack_mrkdwn(response), thread_ts=event.get("ts"))
    else:
        _handle_reader_feedback(user, text, source_channel=f"slack_mention:{channel}", say=say,
                                thread_ts=event.get("ts"), logger=logger)


@app.event("message")
def handle_dm(event, say, logger):
    if event.get("bot_id") or event.get("subtype"):
        return
    if _is_duplicate_event(event):
        logger.info("[DM] 중복 이벤트 무시 (Slack retry)")
        return

    user = event.get("user", "unknown")
    text = event.get("text", "")
    channel = event.get("channel", "")

    # 회의실/팀 채널 메시지 → orchestration 라우터
    if not channel.startswith("D"):
        if channel in _orchestration_channels():
            _handle_meeting_message(user, text, channel, say, logger)
        return

    logger.info(f"[DM] user={user} text={text!r}")

    if CEO_SLACK_USER_ID and user == CEO_SLACK_USER_ID:
        say(text=":thinking_face: 처리 중...")
        session_id = f"slack:{channel}:{user}"
        try:
            response = agent_run(text, dm_channel_id=channel, requester_user_id=user, session_id=session_id)
        except Exception as exc:
            logger.exception("[DM] OpenClaw agent 처리 실패")
            response = (
                ":warning: OpenClaw 처리 중 내부 오류가 발생했습니다.\n"
                f"- 오류: {type(exc).__name__}\n"
                "- 조치: 로그에 기록했습니다. 같은 지시를 반복 실행하지 말고 원인 확인 후 재시도하겠습니다."
            )
        say(text=to_slack_mrkdwn(response))
    elif VP_SLACK_USER_ID and user == VP_SLACK_USER_ID:
        _handle_vp_dm(user, text, say=say, logger=logger)
    else:
        _handle_reader_feedback(user, text, source_channel=f"slack_dm:{channel}", say=say,
                                thread_ts=None, logger=logger)


# ── 회의실 / 팀 채널 orchestration 라우터 ──────────────────────────────────────

_CONVENE_RE = re.compile(r"회의\s*소집|소집해|회의\s*시작|전체\s*회의|다\s*같이|orchestrate", re.IGNORECASE)


def _orchestration_channels() -> set[str]:
    """회의실 + 활성 팀 채널 ID 집합 (env에서 동적 수집)."""
    ids = set()
    room = os.environ.get("SLACK_CHANNEL_CONFERENCE_ROOM", "")
    if room:
        ids.add(room)
    for p in get_active_personas():
        if p.channel_env:
            cid = os.environ.get(p.channel_env, "")
            if cid:
                ids.add(cid)
    return ids


def _is_principal(user: str) -> bool:
    return bool(user) and user in (CEO_SLACK_USER_ID, VP_SLACK_USER_ID)


def _strip_convene(text: str) -> str:
    """소집 트리거 뒤의 실제 주문(order)만 추출."""
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return _CONVENE_RE.sub("", text).strip(" .!~") or text.strip()


def _orchestrate_bg(order: str, logger):
    try:
        from adapters.content.orchestrator import orchestrate
        orchestrate(order)
    except Exception as exc:
        logger.error(f"[meeting] orchestrate 실패: {exc}")


def _mentions_bg(handles: list[str], question: str, channel: str, logger):
    try:
        from adapters.content.orchestrator import respond_as_persona
        for handle in handles:
            respond_as_persona(handle, question, channel_id=channel)
    except Exception as exc:
        logger.error(f"[meeting] mention 응답 실패: {exc}")


def _fetch_url_text(url: str) -> str:
    """URL 내용을 텍스트로 가져옴. YouTube는 yt-dlp 자막 추출, 일반 URL은 HTTP."""
    import subprocess, tempfile, os, re

    # YouTube URL → yt-dlp 자막 추출
    if re.search(r"(youtube\.com/watch|youtu\.be/)", url):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    ["/opt/homebrew/bin/yt-dlp",
                     "--write-auto-sub", "--skip-download",
                     "--sub-lang", "ko,en",
                     "--sub-format", "vtt",
                     "-o", os.path.join(tmpdir, "%(id)s.%(ext)s"),
                     url],
                    capture_output=True, text=True, timeout=30,
                )
                vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
                if vtt_files:
                    vtt = open(os.path.join(tmpdir, vtt_files[0])).read()
                    # VTT 타임코드·태그 제거
                    lines = [l for l in vtt.splitlines()
                             if l.strip() and not re.match(r"^\d{2}:\d{2}|^WEBVTT|^NOTE|^-->", l)]
                    transcript = " ".join(dict.fromkeys(lines))  # 중복 제거
                    return f"[YouTube 자막]\n{transcript[:4000]}"
                # 자막 없으면 영상 제목/설명만
                info = subprocess.run(
                    ["/opt/homebrew/bin/yt-dlp", "--dump-json", "--skip-download", url],
                    capture_output=True, text=True, timeout=20,
                )
                if info.returncode == 0:
                    import json as _j
                    d = _j.loads(info.stdout)
                    title = d.get("title", "")
                    desc = (d.get("description", "") or "")[:1500]
                    return f"[YouTube 제목] {title}\n[설명]\n{desc}"
        except Exception:
            pass
        return f"[YouTube URL — 자막 추출 실패, URL만 전달: {url}]"

    # 일반 URL → HTTP GET
    try:
        import httpx
        r = httpx.get(url, timeout=10, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        text = re.sub(r"<[^>]+>", " ", r.text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception:
        return ""


def _jarvis_route_bg(question: str, channel: str, logger):
    """
    비서실장(Jarvis) 라우터: CEO/VP 모든 메시지의 1차 수신자.
    1. URL이 있으면 내용 파악
    2. Claude로 어떤 페르소나가 답해야 할지 결정
    3. #회의실에 라우팅 안내 게시
    4. 선택된 페르소나 호출
    """
    import re, json as _json
    from adapters.content.orchestrator import respond_as_persona, _post_raw
    from agents.registry import get_active_personas
    from scripts.run_persona import call_llm

    active = [p for p in get_active_personas() if p.handle != "jarvis"]
    active_info = "\n".join(
        f"- {p.handle} ({p.name}, {p.team_short}팀)" for p in active
    )

    # URL 내용 수집
    urls = re.findall(r"https?://\S+", question)
    url_summaries = ""
    for url in urls[:2]:
        content = _fetch_url_text(url)
        if content:
            url_summaries += f"\n[{url} 내용 요약]\n{content[:1500]}\n"
        else:
            url_summaries += f"\n[{url}: 직접 접근 불가 — URL만 페르소나에게 전달]\n"

    # Jarvis가 라우팅 결정
    routing_prompt = (
        "당신은 Harness의 비서실장(Jarvis)입니다.\n"
        "대표님이 #회의실에 다음 지시를 내리셨습니다.\n\n"
        f"[대표님 지시]\n{question}\n"
        f"{url_summaries}\n"
        "[활성 팀 목록]\n"
        f"{active_info}\n\n"
        "이 지시에 답변하기 가장 적절한 팀 handle을 1~3개 선택하고, "
        "그 팀들에게 전달할 구체적인 과제를 작성하세요.\n"
        "반드시 아래 JSON 형식으로만 응답하세요:\n"
        '{"route_to": ["handle1"], '
        '"enriched_task": "페르소나에게 전달할 구체 과제 (URL 요약 포함)", '
        '"jarvis_note": "#회의실에 게시할 비서실장 한 줄 안내"}'
    )

    routing_text, ok = call_llm("claude", routing_prompt)

    # JSON 파싱
    route_to, enriched_task, jarvis_note = [], question, ""
    try:
        m = re.search(r"\{.*\}", routing_text, re.DOTALL)
        if m:
            parsed = _json.loads(m.group())
            route_to = parsed.get("route_to", [])
            enriched_task = parsed.get("enriched_task", question)
            jarvis_note = parsed.get("jarvis_note", "")
    except Exception:
        pass

    # 폴백: 파싱 실패 시 전 팀 호출
    if not route_to:
        route_to = [p.handle for p in active]
        enriched_task = question + (f"\n\n[URL 참고]\n{url_summaries}" if url_summaries else "")

    # #회의실에 비서실장 안내 게시
    target_names = ", ".join(
        f"{p.name}님" for p in active if p.handle in route_to
    ) or "전 팀"
    note = jarvis_note or f"{target_names}께 과제를 전달했습니다."
    _post_raw(channel, f"*Jarvis(비서실장)*: {note}")
    logger.info(f"[meeting] Jarvis 라우팅: {route_to} | task={enriched_task[:60]!r}")

    # 선택된 페르소나 호출
    for p in active:
        if p.handle in route_to:
            try:
                respond_as_persona(p.handle, enriched_task, channel_id=channel)
            except Exception as e:
                logger.warning(f"[meeting] {p.handle} 응답 실패: {e}")


def _handle_meeting_message(user: str, text: str, channel: str, say, logger):
    # CEO/VP만 트리거. persona 발언(bot)·독자는 위에서 이미 걸러짐.
    if not _is_principal(user):
        return
    if not text.strip():
        return

    # 1. 소집 트리거 → 오케스트레이션 시작
    if _CONVENE_RE.search(text):
        from core.meeting_scheduler import add_meeting, parse_meeting_time

        order = _strip_convene(text)
        when = parse_meeting_time(text)
        if when:
            rec = add_meeting(when, order, channel, user)
            logger.info(f"[meeting] 예약 by {user}: {rec['id']} {rec['when']} {order!r}")
            say(text=f":calendar: {when.strftime('%m월 %d일 %H:%M')} 회의 예약했습니다.\n> {order}")
            return
        logger.info(f"[meeting] 회의 소집 by {user}: {order!r}")
        say(text=":speech_balloon: 회의 소집하겠습니다. 잠시만 기다려 주세요.")
        threading.Thread(target=_orchestrate_bg, args=(order, logger), daemon=True).start()
        return

    # 2. 특정 페르소나 멘션 → 해당 페르소나만 응답
    personas = find_mentioned_personas(text)
    if personas:
        handles = [p.handle for p in personas]
        names = ", ".join(f"{p.name}님" for p in personas)
        logger.info(f"[meeting] 멘션 by {user}: {handles}")
        say(text=f":speech_balloon: {names} 호출하셨습니다. 답변 준비하겠습니다.")
        threading.Thread(target=_mentions_bg, args=(handles, text, channel, logger), daemon=True).start()
        return

    # 3. 자유 발언 / URL / 복합 지시 → Jarvis가 라우팅 결정 후 적절한 페르소나 호출
    logger.info(f"[meeting] Jarvis 라우팅 위임 by {user}: {text[:60]!r}")
    threading.Thread(target=_jarvis_route_bg, args=(text, channel, logger), daemon=True).start()


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
