#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

import httpx


def _status(name: str) -> tuple[str, str]:
    value = os.getenv(name, "").strip()
    return name, "SET" if value else "MISSING"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Reddit runtime credentials and token exchange.")
    parser.add_argument("--token-only", action="store_true", help="Fail if token exchange does not succeed.")
    args = parser.parse_args()

    statuses = dict(_status(key) for key in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT"))
    for key, status in statuses.items():
        print(f"{key}={status}")

    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "").strip() or "harness-edu-research/0.1"

    if not client_id or not client_secret:
        print("token_exchange=SKIPPED (credentials missing)")
        return 1 if args.token_only else 0

    try:
        resp = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": user_agent},
            timeout=20,
        )
        print(f"token_http_status={resp.status_code}")
        if resp.status_code != 200:
            body = (resp.text or "")[:200].replace("\n", " ")
            print(f"token_exchange=FAILED body={body}")
            return 1
        token = resp.json().get("access_token", "")
        print(f"token_exchange={'OK' if token else 'FAILED'}")
        return 0 if token else 1
    except Exception as exc:
        print(f"token_exchange=ERROR error={exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
