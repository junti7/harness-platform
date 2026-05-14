"""
T-07: LinkedIn API v2 포스터

필요 환경 변수:
  LINKEDIN_ACCESS_TOKEN
  LINKEDIN_PERSON_URN  (예: urn:li:person:AbCdEfGh)
"""
import os
from typing import Optional

import httpx

_LI_POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"
_LI_PROFILE_URL = "https://api.linkedin.com/v2/me"


def _get_person_urn() -> str:
    urn = os.getenv("LINKEDIN_PERSON_URN", "")
    if urn:
        return urn
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise EnvironmentError("LINKEDIN_ACCESS_TOKEN 미설정")
    resp = httpx.get(
        _LI_PROFILE_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return f"urn:li:person:{resp.json()['id']}"


def post_to_linkedin(text: str) -> dict:
    """LinkedIn에 텍스트 포스트 게시. 응답 dict 반환."""
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    if not token:
        raise EnvironmentError("LINKEDIN_ACCESS_TOKEN 미설정")

    author_urn = _get_person_urn()
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = httpx.post(
        _LI_POSTS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id", "")
    return {
        "id": post_id,
        "url": f"https://www.linkedin.com/feed/update/{post_id}/",
        "platform": "linkedin",
    }
