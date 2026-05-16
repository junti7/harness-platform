import argparse
import json
import mimetypes
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from adapters.content.slack_router import ROUTES
from adapters.content.slack_router import _active_route


load_dotenv()


def slack_post(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")

    response = httpx.post(
        f"https://slack.com/api/{endpoint}",
        data=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error at {endpoint}: {data.get('error')}")
    return data


def upload_file(path: Path, route: str, title: str | None, comment: str | None) -> None:
    if route not in ROUTES:
        raise ValueError(f"Unknown Slack route: {route}")
    if not path.exists():
        raise FileNotFoundError(path)

    active_route = _active_route(route)
    channel_id = os.getenv(ROUTES[active_route]["channel_env"], "")
    if not channel_id:
        raise RuntimeError(f"{ROUTES[active_route]['channel_env']} is not configured")

    file_size = path.stat().st_size
    file_title = title or path.name
    upload = slack_post(
        "files.getUploadURLExternal",
        {"filename": path.name, "length": file_size},
    )

    upload_url = upload["upload_url"]
    file_id = upload["file_id"]
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    with path.open("rb") as file_handle:
        response = httpx.post(
            upload_url,
            content=file_handle.read(),
            headers={"Content-Type": content_type},
            timeout=60.0,
        )
    response.raise_for_status()

    slack_post(
        "files.completeUploadExternal",
        {
            "files": json.dumps([{"id": file_id, "title": file_title}], ensure_ascii=False),
            "channel_id": channel_id,
            "initial_comment": comment or "",
        },
    )
    print(json.dumps({"ok": True, "route": active_route, "file": str(path)}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a file to a configured Slack route.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--route", default="vp_content_review")
    parser.add_argument("--title", default=None)
    parser.add_argument("--comment", default=None)
    args = parser.parse_args()

    upload_file(args.file, args.route, args.title, args.comment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
