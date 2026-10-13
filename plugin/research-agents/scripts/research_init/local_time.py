"""Read the executing machine's local IANA timezone without guessing abbreviations."""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo


def local_timezone() -> str:
    configured = os.environ.get("TZ", "").removeprefix(":")
    if configured:
        if "/zoneinfo/" in configured:
            configured = configured.split("/zoneinfo/", 1)[1]
        try:
            ZoneInfo(configured)
        except (ValueError, KeyError) as error:
            raise ValueError("machine TZ must identify a valid IANA timezone") from error
        return configured
    candidates = []
    localtime = Path("/etc/localtime").resolve()
    if "/zoneinfo/" in localtime.as_posix():
        candidates.append(localtime.as_posix().split("/zoneinfo/", 1)[1])
    timezone_file = Path("/etc/timezone")
    if timezone_file.is_file():
        candidates.append(timezone_file.read_text(encoding="utf-8").strip())
    for candidate in candidates:
        try:
            ZoneInfo(candidate)
        except (ValueError, KeyError):
            continue
        return candidate
    raise ValueError("cannot determine the machine's IANA timezone from TZ or local timezone configuration; configure the machine's TZ before initialization")
