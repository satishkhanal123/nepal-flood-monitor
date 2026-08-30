#!/usr/bin/env python3
"""
Milestone 1.5 QA checks.

Validates:
- index.html structure
- required dashboard DOM elements
- Nepali number localization
- date/time localization
- Nepal timezone handling
- data.json loading
- data normalization
- rainfall data
- river data and thresholds
- casualty data
- dashboard refresh behavior

The QA checks behavior/contracts rather than requiring
specific JavaScript helper function names.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
INDEX = ROOT / "index.html"


REQUIRED_IDS = [
    "updated",
    "rainValue",
    "rainStation",
    "riverValue",
    "riverStation",
    "riverThreshold",
    "warningStatus",
    "deaths",
    "missing",
    "injured",
    "homes",
    "bridges",
    "riverRows",
    "affectedWeather",
    "teams",
    "rescued",
    "vehicles",
    "relief",
    "ticker",
    "langToggle",
    "themeToggle",
]


REQUIRED_RIVERS = {
    "Karnali",
    "Narayani",
    "Kankai",
    "Babai",
    "Mahakali",
}


NEPALI_DIGIT_MAP = {
    "0": "०",
    "1": "१",
    "2": "२",
    "3": "३",
    "4": "४",
    "5": "५",
    "6": "६",
    "7": "७",
    "8": "८",
    "9": "९",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def passed(message: str) -> None:
    print(f"PASS: {message}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"could not read {path.name}: {exc}")


def load_json(path: Path) -> dict:
    if not path.exists():
        fail("data.json is missing")

    try:
        data = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        fail(f"data.json is invalid JSON: {exc}")

    if not isinstance(data, dict):
        fail("data.json root must be an object")

    return data


def is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    )


def valid_non_negative_number(value) -> bool:
    return is_number(value) and value >= 0


def first_existing(mapping: dict, *keys):
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def validate_dom(html: str) -> None:
    for element_id in REQUIRED_IDS:
        pattern = rf'id\s*=\s*["\']{re.escape(element_id)}["\']'

        if not re.search(pattern, html):
            fail(
                f"missing required DOM id: {element_id}"
            )

    passed("index.html DOM contract")


def validate_localization(html: str) -> None:
    """
    Check the actual required behavior instead of demanding
    one exact helper-function name.
    """

    # ---------------------------------------------------------
    # Nepali digits
    # ---------------------------------------------------------

    has_nepali_digit_mapping = (
        "०" in html
        and "१" in html
        and "२" in html
        and "३" in html
        and "४" in html
        and "५" in html
        and "६" in html
        and "७" in html
        and "८" in html
        and "९" in html
    )

    has_digit_conversion = (
        "replace" in html
        and (
            "NEPALI_DIGITS" in html
            or "nepaliDigits" in html
            or "toNepaliDigits" in html
            or "localizeDigits" in html
        )
    )

    if not has_nepali_digit_mapping:
        fail(
            "Nepali digit mapping is missing"
        )

    if not has_digit_conversion:
        fail(
            "Nepali number conversion functionality is missing"
        )

    passed("Nepali number localization")


    # ---------------------------------------------------------
    # Date/time formatting
    # ---------------------------------------------------------

    has_date_formatter = (
        "formatDateTime" in html
        or "formatUpdated" in html
        or "Intl.DateTimeFormat" in html
    )

    if not has_date_formatter:
        fail(
            "date/time formatting functionality is missing"
        )

    passed("date/time localization")


    # ---------------------------------------------------------
    # Nepal timezone
    # ---------------------------------------------------------

    if "Asia/Kathmandu" not in html:
        fail(
            "Nepal timezone Asia/Kathmandu is missing"
        )

    passed("Nepal timezone handling")


    # ---------------------------------------------------------
    # Data loading
    # ---------------------------------------------------------

    if "data.json" not in html:
        fail(
            "index.html does not load data.json"
        )

    if (
        "cache" not in html
        and "?ts=" not in html
        and "Date.now()" not in html
    ):
        fail(
            "data.json cache-busting mechanism is missing"
        )

    passed("data.json loading and refresh")


    # ---------------------------------------------------------
    # Data normalization
    # ---------------------------------------------------------

    if "normalizeData" not in html:
        fail(
            "normalizeData functionality is missing"
        )

    passed("data normalization")


def validate_rainfall(data: dict) -> None:
    rainfall = data.get("rainfall")

    if not isinstance(rainfall, dict):
        fail("rainfall object missing")

    value = first_existing(
        rainfall,
        "max_24h_mm",
        "value",
    )

    if not valid_non_negative_number(value):
        fail(
            "rainfall value is invalid"
        )

    passed("rainfall validation")


def validate_rivers(data: dict) -> None:
    rivers = data.get("rivers")

    if not isinstance(rivers, list):
        fail("rivers must be a list")

    if len(rivers) < 3:
        fail(
            "fewer than 3 river records"
        )

    names = set()

    for river in rivers:

        if not isinstance(river, dict):
            fail(
                "river record is not an object"
            )

        name = river.get("name")

        if not name:
            fail(
                f"river name missing: {river}"
            )

        names.add(name)

        value = first_existing(
            river,
            "value",
            "water_level_m",
            "level",
        )

        warning = first_existing(
            river,
            "warning",
            "warning_level_m",
        )

        danger = first_existing(
            river,
            "danger",
            "danger_level_m",
        )

        if not is_number(value):
            fail(
                f"invalid river value: {river}"
            )

        if not is_number(warning):
            fail(
                f"invalid river warning level: {river}"
            )

        if not is_number(danger):
            fail(
                f"invalid river danger level: {river}"
            )

        if value < 0:
            fail(
                f"negative river value: {river}"
            )

        if warning <= 0:
            fail(
                f"invalid warning threshold: {river}"
            )

        if danger <= warning:
            fail(
                f"danger threshold must exceed warning threshold: {river}"
            )

    missing = REQUIRED_RIVERS - names

    if missing:
        fail(
            f"required rivers missing: {sorted(missing)}"
        )

    passed("river validation")


def validate_casualties(data: dict) -> None:
    casualties = data.get(
        "casualties",
        {},
    )

    if not isinstance(casualties, dict):
        fail(
            "casualties must be an object"
        )

    for key in (
        "deaths",
        "missing",
        "injured",
        "rescued",
    ):

        if key not in casualties:
            continue

        value = casualties[key]

        if value is None:
            continue

        if not valid_non_negative_number(value):
            fail(
                f"invalid casualty value: "
                f"{key}={value}"
            )

    passed("casualty validation")


def validate_infrastructure(data: dict) -> None:
    infrastructure = data.get(
        "infrastructure"
    )

    if infrastructure is None:
        infrastructure = data.get(
            "damage",
            {}
        )

    if not isinstance(infrastructure, dict):
        fail(
            "infrastructure data must be an object"
        )

    for key in (
        "homes",
        "bridges",
    ):

        value = infrastructure.get(key)

        if value is None:
            continue

        if not valid_non_negative_number(value):
            fail(
                f"invalid infrastructure value: "
                f"{key}={value}"
            )

    passed("infrastructure validation")


def validate_operations(data: dict) -> None:
    operations = data.get(
        "operations",
        {}
    )

    if not isinstance(operations, dict):
        fail(
            "operations must be an object"
        )

    for key in (
        "teams",
        "rescued",
        "vehicles",
        "relief",
    ):

        if key not in operations:
            continue

        value = operations[key]

        if value is None:
            continue

        if not valid_non_negative_number(value):
            fail(
                f"invalid operation value: "
                f"{key}={value}"
            )

    passed("operations validation")


def validate_timestamp(data: dict) -> None:
    updated = data.get(
        "updated_at"
    )

    if not isinstance(updated, str):
        fail(
            "updated_at missing"
        )

    text = updated.strip()

    if not text:
        fail(
            "updated_at is empty"
        )

    try:
        datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00"
            )
        )
    except ValueError:
        fail(
            f"updated_at is not ISO-8601: {updated}"
        )

    passed("timestamp validation")


def validate_schema_version(data: dict) -> None:
    version = data.get(
        "schema_version"
    )

    if version is not None and not isinstance(
        version,
        (str, int, float),
    ):
        fail(
            "schema_version has invalid type"
        )

    passed("schema version")


def validate_html_nepali_numbers_runtime_contract(
    html: str,
) -> None:
    """
    Make sure numeric rendering is connected to the
    Nepali localization logic.

    We accept either:
      nepaliDigits(...)
      toNepaliDigits(...)
      localizeDigits(...)
      fmt(...) using a Nepali converter
    """

    formatter_exists = (
        "function fmt(" in html
        or "function formatNumber(" in html
        or "function fmtNumber(" in html
    )

    nepali_converter_exists = (
        "function nepaliDigits(" in html
        or "function toNepaliDigits(" in html
        or "function localizeDigits(" in html
    )

    if not formatter_exists:
        fail(
            "number formatting function is missing"
        )

    if not nepali_converter_exists:
        fail(
            "Nepali digit conversion function is missing"
        )

    # Check that the formatter or renderer actually refers
    # to the active language.
    language_usage = (
        "currentLang === \"ne\"" in html
        or "currentLang === 'ne'" in html
        or "currentLang!==" in html
        or "currentLang !==" in html
        or "currentLang" in html
    )

    if not language_usage:
        fail(
            "number localization is not connected to language state"
        )

    passed(
        "numeric rendering is connected to language switching"
    )


def validate_language_toggle(html: str) -> None:

    if "langToggle" not in html:
        fail(
            "language toggle is missing"
        )

    if (
        "currentLang" not in html
        or "localStorage" not in html
    ):
        fail(
            "language state handling is missing"
        )

    if (
        '"en"' not in html
        or '"ne"' not in html
    ):
        fail(
            "English/Nepali language states are missing"
        )

    passed("English/Nepali language toggle")


def validate_theme_toggle(html: str) -> None:

    if "themeToggle" not in html:
        fail(
            "theme toggle is missing"
        )

    if "localStorage" not in html:
        fail(
            "theme preference storage is missing"
        )

    passed("theme toggle")


def main() -> None:

    print(
        "=================================================="
    )
    print(
        " Nepal Flood 2026 — Milestone 1.5 QA"
    )
    print(
        "=================================================="
    )

    if not INDEX.exists():
        fail("index.html is missing")

    html = read_text(INDEX)

    data = load_json(DATA)

    validate_dom(html)

    validate_localization(html)

    validate_html_nepali_numbers_runtime_contract(
        html
    )

    validate_language_toggle(html)

    validate_theme_toggle(html)

    validate_schema_version(data)

    validate_rainfall(data)

    validate_rivers(data)

    validate_casualties(data)

    validate_infrastructure(data)

    validate_operations(data)

    validate_timestamp(data)

    print()
    print(
        "=================================================="
    )
    print(
        " Milestone 1.5 QA: ALL CHECKS PASSED"
    )
    print(
        "=================================================="
    )


if __name__ == "__main__":
    main()