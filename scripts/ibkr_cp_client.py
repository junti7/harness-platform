"""
IBKR Client Portal API (CP API) thin client.

Purpose
- Resolve symbols into IBKR contracts (conid) with minimal assumptions.
- Support a conservative "candidate list + human confirm" workflow.

Notes
- CP API typically runs behind "IBKR Client Portal Gateway" (local service).
- Authentication/session/2FA constraints are real; this client surfaces status
  rather than pretending results exist.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx
from urllib.parse import urlparse


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


@dataclass(frozen=True)
class IbkrCpConfig:
    base_url: str
    timeout_s: float
    tls_verify: bool

    @staticmethod
    def from_env() -> "IbkrCpConfig":
        # Common default for IBKR Client Portal Gateway.
        base_url = (os.getenv("IBKR_CP_API_BASE_URL") or "https://localhost:5000/v1/api").rstrip("/")
        timeout_s = float(os.getenv("IBKR_CP_TIMEOUT_S") or "12")
        tls_verify = _env_bool("IBKR_CP_TLS_VERIFY", default=False)
        return IbkrCpConfig(base_url=base_url, timeout_s=timeout_s, tls_verify=tls_verify)


class IbkrCpClient:
    def __init__(self, cfg: IbkrCpConfig | None = None) -> None:
        self.cfg = cfg or IbkrCpConfig.from_env()
        # Safety: when TLS verification is disabled, only allow local gateway endpoints.
        if not self.cfg.tls_verify:
            host = (urlparse(self.cfg.base_url).hostname or "").strip().lower()
            if host not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError(
                    "IBKR_CP_TLS_VERIFY=false is only allowed for local gateway endpoints "
                    f"(localhost/127.0.0.1/::1). base_url host={host!r}"
                )
        self._client = httpx.Client(
            base_url=self.cfg.base_url,
            timeout=self.cfg.timeout_s,
            verify=self.cfg.tls_verify,
            headers={
                "Accept": "application/json",
                "User-Agent": "harness-platform/ibkr-cp-client",
            },
        )

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any | None = None) -> dict[str, Any]:
        url = path if path.startswith("/") else f"/{path}"
        r = self._client.request(method.upper(), url, params=params, json=json)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            return data
        return {"data": data}

    def auth_status(self) -> dict[str, Any]:
        # Expected to return {"authenticated": bool, ...} when gateway is alive.
        return self.request("GET", "/iserver/auth/status")

    def accounts(self) -> dict[str, Any]:
        # Useful to confirm account visibility.
        return self.request("GET", "/iserver/accounts")

    def secdef_search(self, symbol: str) -> dict[str, Any]:
        # Security definition search. Returns candidates; shape varies by deployment.
        # We keep the raw response and let the bridge normalize it.
        # CP API docs often show: POST /iserver/secdef/search {"symbol":"AAPL"}
        return self.request("POST", "/iserver/secdef/search", json={"symbol": symbol})

    def secdef_info(self, *, conid: str, sectype: str | None = None) -> dict[str, Any]:
        # Contract details. Many deployments support GET /iserver/secdef/info?conid=...&sectype=...
        params: dict[str, Any] = {"conid": conid}
        if sectype:
            params["sectype"] = sectype
        return self.request("GET", "/iserver/secdef/info", params=params)

    def marketdata_snapshot(self, conids: list[str], fields: list[str] | None = None) -> dict[str, Any]:
        if not conids:
            return {"data": []}
        params: dict[str, Any] = {"conids": ",".join(conids)}
        if fields:
            params["fields"] = ",".join(fields)
        return self.request("GET", "/iserver/marketdata/snapshot", params=params)


def safe_check_connectivity() -> dict[str, Any]:
    """
    Non-throwing preflight used by the bridge.
    Returns:
      { ok: bool, error: str|None, auth: dict|None }
    """
    client = IbkrCpClient()
    try:
        auth = client.auth_status()
        return {"ok": True, "error": None, "auth": auth, "base_url": client.cfg.base_url, "tls_verify": client.cfg.tls_verify}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "auth": None, "base_url": client.cfg.base_url, "tls_verify": client.cfg.tls_verify}
    finally:
        client.close()
