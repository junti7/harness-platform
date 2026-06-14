from __future__ import annotations

import os
import socket


_DEFAULT_MACBOOK_MARKERS = ("macbook", "mbp")
_DEFAULT_MACMINI_MARKERS = ("macmini",)


def split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def collect_hostnames() -> set[str]:
    candidates = {
        socket.gethostname(),
        socket.getfqdn(),
    }
    try:
        candidates.add(os.uname().nodename)
    except AttributeError:
        pass

    normalized: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        lowered = candidate.strip().lower()
        if not lowered:
            continue
        normalized.add(lowered)
        normalized.add(lowered.split(".", 1)[0])
    return normalized


def _matches_any_marker(hostnames: set[str], markers: set[str]) -> bool:
    return any(marker and marker in hostname for marker in markers for hostname in hostnames)


def is_macbook_class_host(hostnames: set[str] | None = None) -> bool:
    hostnames = hostnames or collect_hostnames()
    markers = split_csv(os.getenv("HARNESS_MACBOOK_HOST_MARKERS")) or set(_DEFAULT_MACBOOK_MARKERS)
    return _matches_any_marker(hostnames, markers)


def is_macmini_host(hostnames: set[str] | None = None) -> bool:
    hostnames = hostnames or collect_hostnames()
    markers = split_csv(os.getenv("HARNESS_MACMINI_HOST_MARKERS")) or set(_DEFAULT_MACMINI_MARKERS)
    return _matches_any_marker(hostnames, markers)


def should_use_remote_ollama(remote_host: str | None) -> bool:
    if not remote_host:
        return False

    mode = os.getenv("OPENCLAW_REMOTE_OLLAMA_MODE", "auto").strip().lower()
    if mode in {"0", "false", "no", "off", "disabled"}:
        return False
    if mode == "always":
        return True

    return not is_macmini_host()
