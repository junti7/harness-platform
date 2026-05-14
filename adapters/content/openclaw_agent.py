"""
OpenClaw Agent — 티어 라우팅 기반 CEO 지시 실행 에이전트

LLM 티어:
  Tier 0a (무료) : Ollama on MBP (OLLAMA_REMOTE_HOST) — MBP 켜져 있으면 우선 사용
  Tier 0b (무료) : Ollama on Mac Mini (OLLAMA_HOST) — MBP 꺼져 있을 때 fallback
  Tier 1 (저비용): Claude Haiku 4.5 — 모든 Ollama 실패 시 fallback
  Tier 2 (프리미엄): Claude Sonnet 4.5 — 도구 사용 (파일/PDF/스크립트/Slack)

지원 Tool:
- read_file     : Mac Mini 파일 읽기
- write_file    : Mac Mini 파일 쓰기/수정
- run_script    : 프로젝트 내 Python 스크립트 실행
- send_slack    : Slack 채널에 메시지 전송
- render_pdf    : 마크다운 → PDF 변환 후 Slack DM 전송
- list_files    : 디렉토리 내 파일 목록 조회
- fetch_url     : 공개 웹페이지 또는 인증된 Substack 페이지 내용을 가져와 요약 가능한 텍스트로 변환
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from html import unescape
from pathlib import Path

import anthropic
import httpx
from dotenv import load_dotenv
from core.logger import HarnessLogger
from adapters.content.substack_publisher import fetch_draft_as_text
from adapters.content.refiner import log_api_cost, get_today_cost, DAILY_COST_LIMIT
from core.cost_alerts import check_and_alert

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/Users/juntaepark/projects/harness-platform")
VENV_PYTHON = PROJECT_ROOT / ".venv/bin/python"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# .env 값을 항상 현재 프로젝트 기준으로 다시 로드한다.
# launchd / Slack listener / ad-hoc python 실행에서 환경 해석이 엇갈리지 않도록 override=True를 사용한다.
load_dotenv(PROJECT_ROOT / ".env", override=True)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")           # Mac Mini 로컬
OLLAMA_REMOTE_HOST = os.environ.get("OLLAMA_REMOTE_HOST", "")                  # MBP (켜져 있을 때)
OLLAMA_CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "qwen2.5:1.5b")
OLLAMA_PROBE_TIMEOUT = float(os.environ.get("OLLAMA_PROBE_TIMEOUT", "2.0"))    # 온라인 감지 제한시간
OLLAMA_CHAT_TIMEOUT = float(os.environ.get("OLLAMA_CHAT_TIMEOUT", "15.0"))     # 대화 응답 제한시간

# 도구 사용이 필요한 키워드 — 매칭 시 Claude Sonnet으로 라우팅
TOOL_KEYWORDS = [
    "파일", "보고서", "pdf", "실행", "스크립트", "수정", "저장", "삭제",
    "보내", "전송", "작성", "만들어", "만들어줘", "읽어", "읽어줘", "목록",
    "채널", "슬랙", "slack", "생성", "업로드", "분석", "코드", "수집",
    "브리핑", "신호", "스케줄", "edit", "write", "read", "send", "create",
    "뉴스레터", "이슈", "배포", "구독자", "링크", "url", "http://", "https://",
    "웹", "페이지", "substack.com", "봐줘", "검토",
]

CHANNEL_MAP = {
    "exec-president-decisions": os.environ.get("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "C0B2TQV3RDG"),
    "president": os.environ.get("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "C0B2TQV3RDG"),
    "vp-content-review": os.environ.get("SLACK_CHANNEL_VP_CONTENT_REVIEW", "C0B2TQVV602"),
    "vp": os.environ.get("SLACK_CHANNEL_VP_CONTENT_REVIEW", "C0B2TQVV602"),
    "ops-incidents": os.environ.get("SLACK_CHANNEL_OPS_INCIDENTS", "C0B2MDYDE83"),
    "ops": os.environ.get("SLACK_CHANNEL_OPS_INCIDENTS", "C0B2MDYDE83"),
}

SYSTEM_PROMPT = """You are OpenClaw, the AI Chief of Staff and command center of Harness.
Harness is a Physical AI / AGI creator subscription company operated by a President (CEO) and Vice President.

Your role:
- Execute CEO orders via tools (file read/write, script execution, Slack messaging, PDF reports)
- When the user provides a URL, fetch the page first before saying access is unavailable.
- Manage newsletter operations, signal collection, and agent workflows
- Act as Chief of Staff: decompose orders into actions, execute, and report results

Guidelines:
- Always respond in the same language the user uses (Korean preferred)
- Today's date is {today}. Use this date when writing reports, memos, or any dated content.
- For file operations, use paths relative to the project root: /Users/juntaepark/projects/harness-platform/
- For sensitive files (.env), show content with secrets masked (show first 4 chars + ***)
- Before modifying files, briefly describe what you will change and do it
- After executing tools, summarize what was done clearly
- If a task requires multiple steps, execute them in sequence using multiple tool calls
- Never expose API keys or secrets in responses
- Prefer `fetch_url` for web page review requests. For Substack draft or publish URLs under the configured publication, send the authenticated cookie automatically if available.
"""

# Ollama용 경량 시스템 프롬프트 (도구 없는 대화 전용)
CHAT_SYSTEM_PROMPT = """당신은 OpenClaw입니다. Harness의 AI 비서실장으로, Physical AI/AGI 크리에이터 구독 회사의 운영을 보조합니다.

역할:
- CEO(대표)와 부대표의 질문에 친절하고 명확하게 답변
- 회사 운영, Physical AI, AGI, 로봇공학, 뉴스레터 사업에 대한 지식 제공
- 복잡한 작업(파일 조작, 보고서 생성, 스크립트 실행 등)은 "해당 작업은 도구가 필요합니다" 라고 안내

규칙:
- 항상 한국어로 답변 (영어 질문에도 한국어 우선)
- API 키, 비밀번호 등 민감 정보 노출 금지
- 간결하고 실용적인 답변 제공
"""

TOOLS = [
    {
        "name": "read_file",
        "description": "Mac Mini 프로젝트의 파일 내용을 읽어옴. 프로젝트 루트 기준 상대경로 또는 절대경로 사용.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "파일 경로. 예: '.env', 'CLAUDE.md', 'adapters/content/slack_router.py'"
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Mac Mini 프로젝트의 파일을 수정하거나 새로 생성. overwrite는 전체 교체, append는 내용 추가.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "파일 경로 (프로젝트 루트 기준)"},
                "content": {"type": "string", "description": "파일에 쓸 내용"},
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "overwrite: 전체 교체, append: 기존 내용 뒤에 추가. 기본값: overwrite",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_files",
        "description": "프로젝트 내 디렉토리의 파일 목록을 조회.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "조회할 디렉토리 경로 (프로젝트 루트 기준). 예: '.', 'adapters/', 'docs/'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "run_script",
        "description": "Mac Mini에서 프로젝트 내 Python 스크립트를 venv 환경으로 실행.",
        "input_schema": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "스크립트 경로 (프로젝트 루트 기준). 예: 'scripts/openclaw_bridge_heartbeat.py'",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "스크립트에 전달할 인자 목록",
                },
            },
            "required": ["script"],
        },
    },
    {
        "name": "send_slack",
        "description": "Slack 채널에 메시지를 전송. 채널: exec-president-decisions, vp-content-review, ops-incidents",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "채널명. 예: 'exec-president-decisions', 'vp-content-review', 'ops-incidents'",
                },
                "message": {"type": "string", "description": "전송할 메시지 내용 (Slack markdown 지원)"},
            },
            "required": ["channel", "message"],
        },
    },
    {
        "name": "render_pdf",
        "description": "마크다운 형식의 보고서를 PDF로 변환하고 지정된 Slack 채널/DM으로 전송.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "보고서 제목 (파일명에도 사용됨)"},
                "content": {"type": "string", "description": "마크다운 형식의 보고서 전체 내용"},
                "channel_id": {
                    "type": "string",
                    "description": "전송할 Slack 채널 또는 DM ID. 예: 'D0B2D63T3TM' (DM ID) 또는 채널명",
                },
            },
            "required": ["title", "content", "channel_id"],
        },
    },
    {
        "name": "fetch_url",
        "description": "실시간 웹페이지 내용을 가져와 텍스트로 정리. 공개 URL과 인증된 Substack publication URL을 지원.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "가져올 웹페이지 URL. 예: 'https://junti7.substack.com/publish/post/197214425'",
                }
            },
            "required": ["url"],
        },
    },
]


# ── Tool 실행 함수들 ────────────────────────────────────────────────────────────

def _resolve_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return PROJECT_ROOT / p


def tool_read_file(path: str) -> str:
    try:
        fp = _resolve_path(path)
        if not fp.exists():
            return f"❌ 파일 없음: {fp}"
        content = fp.read_text(encoding="utf-8")
        # .env 파일은 시크릿 마스킹
        if fp.name == ".env":
            lines = []
            for line in content.splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    masked = val[:4] + "***" if len(val) > 4 else "***"
                    lines.append(f"{key}={masked}")
                else:
                    lines.append(line)
            content = "\n".join(lines)
        return content
    except Exception as e:
        return f"❌ 읽기 실패: {e}"


def tool_write_file(path: str, content: str, mode: str = "overwrite") -> str:
    try:
        fp = _resolve_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with fp.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            fp.write_text(content, encoding="utf-8")
        return f"✅ 저장 완료: {fp} ({fp.stat().st_size} bytes)"
    except Exception as e:
        return f"❌ 쓰기 실패: {e}"


def tool_list_files(path: str) -> str:
    try:
        dp = _resolve_path(path)
        if not dp.exists():
            return f"❌ 디렉토리 없음: {dp}"
        items = sorted(dp.iterdir())
        lines = []
        for item in items:
            prefix = "📁 " if item.is_dir() else "📄 "
            lines.append(f"{prefix}{item.name}")
        return "\n".join(lines) or "(비어있음)"
    except Exception as e:
        return f"❌ 목록 조회 실패: {e}"


def tool_run_script(script: str, args: list | None = None) -> str:
    try:
        cmd = [str(VENV_PYTHON), str(PROJECT_ROOT / script)] + (args or [])
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, cwd=str(PROJECT_ROOT)
        )
        output = (result.stdout or "") + (result.stderr or "")
        status = "✅" if result.returncode == 0 else "❌"
        return f"{status} 종료코드: {result.returncode}\n{output[:1200]}"
    except subprocess.TimeoutExpired:
        return "❌ 시간 초과 (60초)"
    except Exception as e:
        return f"❌ 실행 오류: {e}"


def tool_send_slack(channel: str, message: str) -> str:
    channel_id = CHANNEL_MAP.get(channel.lower().lstrip("#"), channel)
    try:
        resp = httpx.post(
            "https://slack.com/api/chat.postMessage",
            json={"channel": channel_id, "text": message},
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return f"✅ 전송 완료 → {channel} ({channel_id})"
        return f"❌ 전송 실패: {data.get('error')}"
    except Exception as e:
        return f"❌ Slack 전송 오류: {e}"


def tool_fetch_url(url: str) -> str:
    try:
        publication_url = os.environ.get("SUBSTACK_PUBLICATION_URL", "").rstrip("/")
        substack_session_token = os.environ.get("SUBSTACK_SESSION_TOKEN", "")
        is_substack_private = (
            publication_url
            and url.startswith(publication_url)
            and ("/publish/" in url or "/publish/post/" in url)
        )

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        }

        if is_substack_private:
            match = re.search(r"/publish/post/(\d+)", url)
            if match:
                draft = fetch_draft_as_text(match.group(1), logger=HarnessLogger(tier=4))
                title = draft.get("title") or "Untitled draft"
                subtitle = draft.get("subtitle") or ""
                body_text = (draft.get("body_text") or "").strip()
                parts = [f"✅ Substack draft fetch 완료: {url}", f"\nTITLE: {title}"]
                if subtitle:
                    parts.append(f"\nSUBTITLE: {subtitle}")
                if body_text:
                    parts.append(f"\n\n{body_text[:12000]}")
                else:
                    parts.append("\n\n(본문이 비어 있거나 추출되지 않았습니다.)")
                return "".join(parts)
        if publication_url and url.startswith(publication_url) and substack_session_token:
            headers["Cookie"] = f"substack.sid={substack_session_token}"
            headers["Referer"] = f"{publication_url}/publish/posts"
            headers["Origin"] = publication_url

        resp = httpx.get(url, headers=headers, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        text = resp.text
        if "html" in content_type.lower():
            try:
                from bs4 import BeautifulSoup  # type: ignore
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
                body_text = "\n".join(
                    line.strip() for line in soup.get_text("\n").splitlines() if line.strip()
                )
                if title:
                    body_text = f"TITLE: {title}\n\n{body_text}"
                text = body_text
            except Exception:
                stripped = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
                stripped = re.sub(r"(?s)<[^>]+>", "\n", stripped)
                stripped = unescape(stripped)
                text = "\n".join(line.strip() for line in stripped.splitlines() if line.strip())

        text = text[:12000]
        return f"✅ URL fetch 완료: {url}\n\n{text}"
    except Exception as e:
        if is_substack_private and (
            "redirect" in str(e).lower() or "too many redirects" in str(e).lower()
        ):
            if not substack_session_token:
                return (
                    "❌ Substack draft 접근 실패: 이 URL은 로그인 세션이 필요한 private draft/publish 페이지입니다.\n"
                    "현재 `SUBSTACK_SESSION_TOKEN` 이 설정되어 있지 않아 내용을 가져올 수 없습니다.\n"
                    "권한이 생기면 같은 URL을 다시 읽을 수 있습니다."
                )
            return (
                "❌ Substack draft 접근 실패: 저장된 `SUBSTACK_SESSION_TOKEN` 이 만료되었거나 draft 접근 권한이 부족합니다.\n"
                "Substack 세션을 갱신한 뒤 다시 시도해야 합니다."
            )
        return f"❌ URL fetch 오류: {e}"


def _slack_api(endpoint: str, payload: dict) -> dict:
    """Slack API 호출 — form-encoded (파일 업로드 API 호환)"""
    resp = httpx.post(
        f"https://slack.com/api/{endpoint}",
        data=payload,
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _upload_file_to_slack(pdf_path: Path, title: str, channel_id: str) -> str:
    """3단계 Slack 파일 업로드: getUploadURLExternal → PUT → completeUploadExternal"""
    file_size = pdf_path.stat().st_size

    # 1단계: 업로드 URL 요청
    r1 = _slack_api("files.getUploadURLExternal", {
        "filename": pdf_path.name,
        "length": str(file_size),
    })
    if not r1.get("ok"):
        return f"❌ URL 요청 실패: {r1.get('error')} / {r1}"

    upload_url = r1["upload_url"]
    file_id = r1["file_id"]

    # 2단계: 파일 POST (Slack 업로드 API는 POST 사용)
    with pdf_path.open("rb") as f:
        put_resp = httpx.post(upload_url, content=f.read(),
                              headers={"Content-Type": "application/octet-stream"},
                              timeout=60)
    if put_resp.status_code not in (200, 201):
        return f"❌ 파일 업로드 실패: HTTP {put_resp.status_code} / {put_resp.text[:200]}"

    # 3단계: 업로드 완료 + 채널 공유
    r3 = _slack_api("files.completeUploadExternal", {
        "files": json.dumps([{"id": file_id, "title": title}]),
        "channel_id": channel_id,
        "initial_comment": f"📊 *{title}* — OpenClaw 생성 보고서",
    })
    if r3.get("ok"):
        return f"✅ PDF 전송 완료: {title}.pdf → {channel_id}"
    return f"❌ 업로드 완료 실패: {r3.get('error')} / {json.dumps(r3)[:300]}"


def tool_render_pdf(title: str, content: str, channel_id: str) -> str:
    try:
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in title)

        # 임시 디렉토리 대신 reports/ 폴더에 저장 (디버깅 용이)
        reports_dir = PROJECT_ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        md_path = reports_dir / f"{safe_title}.md"
        pdf_path = reports_dir / f"{safe_title}.pdf"

        md_path.write_text(content, encoding="utf-8")
        logger.info(f"[render_pdf] MD 저장: {md_path}")

        # Chrome headless PDF 변환
        result = subprocess.run(
            [str(VENV_PYTHON), str(PROJECT_ROOT / "scripts/render_markdown_pdf.py"),
             str(md_path), str(pdf_path)],
            capture_output=True, text=True, timeout=90, cwd=str(PROJECT_ROOT),
        )
        logger.info(f"[render_pdf] render rc={result.returncode} stdout={result.stdout[:200]}")
        if result.returncode != 0:
            return f"❌ PDF 생성 실패:\n{result.stderr[:500]}"

        logger.info(f"[render_pdf] PDF 크기: {pdf_path.stat().st_size} bytes")

        # Slack 파일 업로드
        return _upload_file_to_slack(pdf_path, title, channel_id)

    except Exception as e:
        logger.exception("[render_pdf] 오류")
        return f"❌ render_pdf 오류: {e}"


TOOL_EXECUTORS = {
    "read_file": lambda inp: tool_read_file(inp["path"]),
    "write_file": lambda inp: tool_write_file(inp["path"], inp["content"], inp.get("mode", "overwrite")),
    "list_files": lambda inp: tool_list_files(inp["path"]),
    "run_script": lambda inp: tool_run_script(inp["script"], inp.get("args")),
    "send_slack": lambda inp: tool_send_slack(inp["channel"], inp["message"]),
    "render_pdf": lambda inp: tool_render_pdf(inp["title"], inp["content"], inp["channel_id"]),
    "fetch_url": lambda inp: tool_fetch_url(inp["url"]),
}


# ── LLM 티어 라우팅 ────────────────────────────────────────────────────────────

def _needs_tools(message: str) -> bool:
    """도구 사용이 필요한 메시지인지 키워드로 판별"""
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in TOOL_KEYWORDS)


def _ollama_probe(host: str) -> bool:
    """Ollama 서버가 응답 가능한지 빠르게 확인 (OLLAMA_PROBE_TIMEOUT초 내)"""
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=OLLAMA_PROBE_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _ollama_chat(host: str, label: str, user_message: str) -> str | None:
    """지정한 Ollama 호스트로 채팅 요청. 실패 시 None 반환."""
    try:
        resp = httpx.post(
            f"{host}/api/chat",
            json={
                "model": OLLAMA_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
            },
            timeout=OLLAMA_CHAT_TIMEOUT,
        )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "")
        if content:
            logger.info(f"[router] {label}({OLLAMA_CHAT_MODEL}) 응답 완료")
            return content
        return None
    except Exception as e:
        logger.info(f"[router] {label} 실패: {type(e).__name__}: {e}")
        return None


def _run_ollama_chat(user_message: str) -> str:
    """
    Tier 0 무료 대화 처리 — 두 Ollama 호스트를 순서대로 시도.

    우선순위:
      Tier 0a: MBP Ollama (OLLAMA_REMOTE_HOST) — MBP 켜져 있을 때 우선 사용
      Tier 0b: Mac Mini Ollama (OLLAMA_HOST)   — MBP 꺼졌거나 느릴 때 fallback
      Tier 1 : Claude Haiku                    — 모든 Ollama 불가 시 fallback
    """
    candidates = []
    if OLLAMA_REMOTE_HOST:
        candidates.append((OLLAMA_REMOTE_HOST, "Tier0a/MBP-Ollama"))
    candidates.append((OLLAMA_HOST, "Tier0b/Local-Ollama"))

    for host, label in candidates:
        # 빠른 온라인 감지 먼저 (PROBE_TIMEOUT 이내)
        if not _ollama_probe(host):
            logger.info(f"[router] {label} 오프라인 → 다음 후보로")
            continue
        result = _ollama_chat(host, label, user_message)
        if result is not None:
            return result
        logger.info(f"[router] {label} 응답 실패 → 다음 후보로")

    # 모든 Ollama 실패 → Haiku
    logger.info("[router] 모든 Ollama 비활성 → Tier1/Haiku fallback")
    return _run_haiku_chat(user_message)


def _run_haiku_chat(user_message: str) -> str:
    """Tier 1: Claude Haiku (저비용 fallback 대화)"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "❌ ANTHROPIC_API_KEY가 설정되지 않았습니다."
    client = anthropic.Anthropic(api_key=api_key)
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=CHAT_SYSTEM_PROMPT + f"\n오늘 날짜: {today_str}",
        messages=[{"role": "user", "content": user_message}],
    )
    log_api_cost("claude-haiku-4-5", resp.usage.input_tokens, resp.usage.output_tokens)
    check_and_alert(get_today_cost(), DAILY_COST_LIMIT, logger)
    logger.info(
        f"[router] Tier1/Haiku 응답 tokens=in:{resp.usage.input_tokens}/out:{resp.usage.output_tokens}"
    )
    return resp.content[0].text if resp.content else "응답 없음"


# ── 에이전트 루프 (Tier 2: Claude Sonnet + Tools) ──────────────────────────────

def run(user_message: str, dm_channel_id: str | None = None) -> str:
    """
    CEO 메시지를 라우팅하여 최적 LLM으로 처리.

    Tier 0a (무료)  : MBP Ollama   — MBP 켜져 있으면 우선
    Tier 0b (무료)  : Local Ollama — MBP 꺼져 있을 때
    Tier 1  (저비용): Claude Haiku — 모든 Ollama 불가 시
    Tier 2  (프리미엄): Claude Sonnet — 도구 사용 필요 시
    """
    if not _needs_tools(user_message):
        logger.info(f"[router] 일반 대화 → Tier0/Ollama")
        return _run_ollama_chat(user_message)

    logger.info(f"[router] 도구 사용 감지 → Tier2/Sonnet")
    return _run_tool_agent(user_message, dm_channel_id)


def _run_tool_agent(user_message: str, dm_channel_id: str | None = None) -> str:
    """Tier 2: Claude Sonnet 4.5 + Tool Calling"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "❌ ANTHROPIC_API_KEY가 설정되지 않았습니다."

    client = anthropic.Anthropic(api_key=api_key)

    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    system = SYSTEM_PROMPT.format(today=today_str)
    if dm_channel_id:
        system += f"\n\nCurrent requester's DM channel ID: {dm_channel_id} — use this as default channel_id for render_pdf and file deliveries unless the user specifies otherwise."

    messages = [{"role": "user", "content": user_message}]

    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_log = []

    for turn in range(10):  # 최대 10 turn 안전장치
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        # 토큰 누적
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
        logger.info(f"[agent] stop_reason={response.stop_reason} tokens=in:{response.usage.input_tokens}/out:{response.usage.output_tokens}")

        if response.stop_reason == "end_turn":
            log_api_cost("claude-sonnet-4-5", total_input_tokens, total_output_tokens)
            check_and_alert(get_today_cost(), DAILY_COST_LIMIT, logger)
            logger.info(
                f"[agent] session_total tokens=input:{total_input_tokens} output:{total_output_tokens} "
                f"tools_called={tool_calls_log}"
            )
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "✅ 완료 (응답 없음)"

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.info(f"[agent] tool={block.name} input={json.dumps(block.input)[:200]}")
                    tool_calls_log.append(block.name)
                    result = TOOL_EXECUTORS.get(block.name, lambda _: "❌ 알 수 없는 tool")(block.input)
                    logger.info(f"[agent] tool_result={str(result)[:200]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result),
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return "❌ 에이전트 루프가 예상치 못하게 종료되었습니다."
