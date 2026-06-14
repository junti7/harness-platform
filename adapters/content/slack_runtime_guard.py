from __future__ import annotations

import os
from adapters.content.runtime_host import collect_hostnames, is_macbook_class_host, split_csv


def get_slack_runtime_guard_error() -> str | None:
    hostnames = collect_hostnames()
    allowed_hostnames = split_csv(os.getenv("HARNESS_SLACK_ALLOWED_HOSTNAMES"))

    if allowed_hostnames and not (hostnames & allowed_hostnames):
        return (
            "Slack listener startup blocked: this host is not in "
            "HARNESS_SLACK_ALLOWED_HOSTNAMES. OpenClaw Slack DM ingress must run only on the Mac Mini. "
            f"detected_hosts={sorted(hostnames)}"
        )

    if is_macbook_class_host(hostnames):
        return (
            "Slack listener startup blocked on a MacBook-class host. "
            "OpenClaw Slack DM ingress must run only on the Mac Mini. "
            f"detected_hosts={sorted(hostnames)}"
        )

    return None


def assert_slack_runtime_allowed() -> None:
    error = get_slack_runtime_guard_error()
    if error:
        raise RuntimeError(error)
