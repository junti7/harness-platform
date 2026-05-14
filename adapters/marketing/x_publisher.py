"""
T-07: X (구 Twitter) API v2 포스터

필요 환경 변수:
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
"""
import os
import time
import hashlib
import hmac
import base64
import urllib.parse
from typing import Optional

import httpx

_X_TWEET_URL = "https://api.twitter.com/2/tweets"


def _oauth1_header(method: str, url: str, params: dict) -> str:
    api_key = os.getenv("X_API_KEY", "")
    api_secret = os.getenv("X_API_SECRET", "")
    access_token = os.getenv("X_ACCESS_TOKEN", "")
    access_secret = os.getenv("X_ACCESS_SECRET", "")

    if not all([api_key, api_secret, access_token, access_secret]):
        raise EnvironmentError("X API 자격증명 미설정 (.env: X_API_KEY/SECRET, X_ACCESS_TOKEN/SECRET)")

    nonce = base64.b64encode(os.urandom(16)).decode().rstrip("=")
    timestamp = str(int(time.time()))

    oauth_params = {
        "oauth_consumer_key": api_key,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp,
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }

    all_params = {**oauth_params, **params}
    sorted_params = "&".join(
        f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )

    base_string = "&".join([
        method.upper(),
        urllib.parse.quote(url, safe=""),
        urllib.parse.quote(sorted_params, safe=""),
    ])

    signing_key = f"{urllib.parse.quote(api_secret, safe='')}&{urllib.parse.quote(access_secret, safe='')}"
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = sig
    header_value = "OAuth " + ", ".join(
        f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return header_value


def post_tweet(text: str) -> dict:
    """X에 트윗 게시. 응답 dict 반환 (id, text 포함)."""
    auth_header = _oauth1_header("POST", _X_TWEET_URL, {})
    resp = httpx.post(
        _X_TWEET_URL,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    tweet_id = data.get("data", {}).get("id", "")
    return {
        "id": tweet_id,
        "url": f"https://x.com/i/web/status/{tweet_id}",
        "platform": "x",
    }
