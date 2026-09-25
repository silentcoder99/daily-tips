#!/usr/bin/env python3
"""Pick a random tip from a newline-separated file and publish it to ntfy.

Configuration comes from environment variables (normally injected by
`dotenvx run`), with a couple of CLI overrides:

    NTFY_TOPIC     required (unless --dry-run); the ntfy topic to publish to
    NTFY_SERVER    optional; defaults to https://ntfy.sh
    NTFY_TOKEN     optional; sent as a Bearer token for protected topics
    NTFY_TITLE     optional; notification title, defaults to "Daily Tip"
    NTFY_PRIORITY  optional; ntfy priority (1-5 or min, low, default, high, urgent)
    NTFY_TAGS      optional; comma-separated ntfy tags/emoji shortcodes
    TIPS_FILE      optional; defaults to tips.txt next to this script
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_SERVER = "https://ntfy.sh"
DEFAULT_TITLE = "Daily Tip"
DEFAULT_TIPS_FILE = Path(__file__).resolve().parent / "tips.txt"
TIMEOUT_SECONDS = 10


class TipError(Exception):
    """A user-facing error that should exit non-zero with a clear message."""


def load_tips(path: Path) -> list[str]:
    """Return non-blank, non-comment lines from the tips file."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise TipError(f"tips file not found: {path}") from None
    except OSError as e:
        raise TipError(f"could not read tips file {path}: {e}") from None

    tips = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            tips.append(line)
    if not tips:
        raise TipError(f"no tips found in {path}")
    return tips


def choose_tip(tips: list[str]) -> str:
    return random.SystemRandom().choice(tips)


PRIORITIES = {"min": 1, "low": 2, "default": 3, "high": 4, "max": 5, "urgent": 5}


def parse_priority(value: str) -> int:
    """Accept ntfy priority names or numbers 1-5."""
    value = value.strip().lower()
    if value in PRIORITIES:
        return PRIORITIES[value]
    if value.isdigit() and 1 <= int(value) <= 5:
        return int(value)
    raise TipError(f"invalid NTFY_PRIORITY {value!r}; use 1-5 or one of {', '.join(PRIORITIES)}")


def publish(
    server: str,
    topic: str,
    message: str,
    *,
    token: str | None = None,
    title: str | None = None,
    priority: str | None = None,
    tags: str | None = None,
) -> None:
    """Publish via ntfy's JSON API so every field (including title) is UTF-8 safe."""
    payload: dict[str, object] = {"topic": topic, "message": message}
    if title:
        payload["title"] = title
    if priority:
        payload["priority"] = parse_priority(priority)
    if tags:
        payload["tags"] = [t.strip() for t in tags.split(",") if t.strip()]

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        server.rstrip("/") + "/",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace").strip()
        raise TipError(f"ntfy returned HTTP {e.code}: {detail or e.reason}") from None
    except urllib.error.URLError as e:
        raise TipError(f"could not reach ntfy at {server}: {e.reason}") from None


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tips-file",
        type=Path,
        help=f"path to the tips file (default: $TIPS_FILE or {DEFAULT_TIPS_FILE.name})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the chosen tip without publishing (no secrets needed)",
    )
    return parser.parse_args(argv)


def env(name: str) -> str | None:
    """Return a stripped env var, treating empty strings as unset."""
    value = os.environ.get(name, "").strip()
    return value or None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tips_file = args.tips_file or Path(env("TIPS_FILE") or DEFAULT_TIPS_FILE)
    tips_file = tips_file.expanduser()

    try:
        tip = choose_tip(load_tips(tips_file))
        if args.dry_run:
            print(tip)
            return 0

        topic = env("NTFY_TOPIC")
        if not topic:
            raise TipError("NTFY_TOPIC is not set (run via `dotenvx run -- ...`)")
        server = env("NTFY_SERVER") or DEFAULT_SERVER
        publish(
            server,
            topic,
            tip,
            token=env("NTFY_TOKEN"),
            title=env("NTFY_TITLE") or DEFAULT_TITLE,
            priority=env("NTFY_PRIORITY"),
            tags=env("NTFY_TAGS"),
        )
    except TipError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"published: {tip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
