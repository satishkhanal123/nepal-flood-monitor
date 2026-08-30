#!/usr/bin/env python3
"""
Milestone 1.5 QA checks.
Fails the GitHub Action when the dashboard data contract is broken.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
INDEX = ROOT / "index.html"

REQUIRED_IDS = [
    "updated", "rainValue", "rainStation", "riverValue", "riverStation",
    "riverThreshold", "warningStatus", "deaths", "missing", "injured",
    "homes", "bridges", "riverRows", "affectedWeather", "teams",
    "rescued", "vehicles", "relief", "ticker", "langToggle", "themeToggle"
]

REQUIRED_RIVERS = {"Karnali", "Narayani", "Kankai", "Babai", "Mahakali"}


def fail(message):
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main():
    if not DATA.exists():
        fail("data.json is missing")
    if not INDEX.exists():
        fail("index.html is missing")

    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"data.json is invalid JSON: {exc}")

    html = INDEX.read_text(encoding="utf-8")

    for element_id in REQUIRED_IDS:
        if f'id="{element_id}"' not in html:
            fail(f"missing required DOM id: {element_id}")

    for token in (
        "nepaliDigits",
        "formatDateTime",
        "normalizeData",
        'Asia/Kathmandu',
        'data.json?ts=',
    ):
        if token not in html:
            fail(f"missing required functionality: {token}")

    if not isinstance(data, dict):
        fail("root JSON must be an object")

    rainfall = data.get("rainfall")
    if not isinstance(rainfall, dict):
        fail("rainfall object missing")

    rain = rainfall.get("max_24h_mm")
    if not isinstance(rain, (int, float)) or rain < 0:
        fail("rainfall.max_24h_mm is invalid")

    rivers = data.get("rivers")
    if not isinstance(rivers, list) or len(rivers) < 3:
        fail("fewer than 3 river records")

    names = set()
    for r in rivers:
        if not isinstance(r, dict):
            fail("river record is not an object")

        names.add(r.get("name"))

        value = r.get("value")
        warning = r.get("warning")
        danger = r.get("danger")

        if not all(isinstance(x, (int, float)) for x in (value, warning, danger)):
            fail(f"incomplete river record: {r}")

        if value < 0 or warning <= 0 or danger <= warning:
            fail(f"invalid river thresholds: {r}")

    missing_rivers = REQUIRED_RIVERS - names
    if missing_rivers:
        fail(f"required rivers missing: {sorted(missing_rivers)}")

    casualties = data.get("casualties", {})
    if not isinstance(casualties, dict):
        fail("casualties must be an object")

    for key in ("deaths", "missing", "injured", "rescued"):
        value = casualties.get(key)
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            fail(f"invalid casualty value: {key}={value}")

    updated = data.get("updated_at")
    if not isinstance(updated, str):
        fail("updated_at missing")

    try:
        datetime.fromisoformat(updated.replace("Z", "+00:00"))
    except ValueError:
        fail(f"updated_at is not ISO-8601: {updated}")

    print("PASS: index.html DOM contract")
    print("PASS: data.json schema")
    print("PASS: rainfall validation")
    print("PASS: river validation")
    print("PASS: casualty validation")
    print("PASS: timestamp validation")
    print("Milestone 1.5 QA: ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
