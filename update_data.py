#!/usr/bin/env python3
"""
Nepal Flood 2026 — verified data updater

Purpose:
- Pull current rainfall and river observations from the official DHM site.
- Keep casualty/impact figures only when they already exist as verified data.
- Never replace a good value with null, zero, or an unverified guess.
- Write one stable JSON shape that the locked dashboard can read.
- Use only Python standard-library modules.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"

DHM_URL = "https://www.dhm.gov.np/?locale=en"
TIMEOUT = 25

NPT = timezone(timedelta(hours=5, minutes=45))

RIVER_PATTERNS = [
    ("Narayani", "Devghat", r"Narayani at Devghat WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"),
    ("Karnali", "Chisapani", r"Karnali at Chisapani WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"),
    ("Kankai", "Mainachuli", r"Kankai River at Mainachuli WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"),
    ("Babai", "Chepang", r"Babai at Chepang WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"),
    ("Mahakali", "Parigaon", r"Mahakali at Parigaon WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"),
]


def now_npt() -> datetime:
    return datetime.now(NPT)


def iso_now() -> str:
    return now_npt().isoformat(timespec="seconds")


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Nepal-Flood-Monitor/1.5",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def read_existing() -> dict:
    if not DATA_FILE.exists():
        return {}
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except Exception as exc:
        raise RuntimeError(f"data.json is invalid: {exc}") from exc


def number(value):
    if value is None:
        return None
    try:
        value = float(value)
        if value < 0:
            return None
        return int(value) if value.is_integer() else value
    except (TypeError, ValueError):
        return None


def extract_dhm(text: str) -> dict:
    rainfall_match = re.search(
        r"Max 24hr:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z][A-Za-z ()_-]*)",
        text,
        flags=re.I,
    )

    rainfall = {
        "max_24h_mm": number(rainfall_match.group(1)) if rainfall_match else None,
        "station": rainfall_match.group(2).strip() if rainfall_match else None,
        "source": "DHM",
        "source_url": DHM_URL,
        "as_of": iso_now(),
    }

    rivers = []
    for name, station, pattern in RIVER_PATTERNS:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            continue

        value = number(match.group(1))
        warning = number(match.group(2))
        danger = number(match.group(3))

        if value is None or warning is None or danger is None:
            continue

        if warning <= 0 or danger <= warning:
            raise RuntimeError(
                f"Invalid DHM threshold order for {name}: "
                f"value={value}, warning={warning}, danger={danger}"
            )

        if value >= danger:
            status = "Above Danger Level"
        elif value >= warning:
            status = "Above Warning Level"
        else:
            status = "Below Warning Level"

        rivers.append(
            {
                "name": name,
                "station": station,
                "value": value,
                "warning": warning,
                "danger": danger,
                "status": status,
                "source": "DHM",
                "source_url": "https://dhm.gov.np/hydrology/river-watch",
                "as_of": iso_now(),
            }
        )

    if rainfall["max_24h_mm"] is None:
        raise RuntimeError("DHM rainfall value was not found")

    if len(rivers) < 3:
        raise RuntimeError(
            f"DHM returned too few river observations: {len(rivers)}"
        )

    return {"rainfall": rainfall, "rivers": rivers}


def preserve_impact(existing: dict) -> dict:
    """
    Preserve already verified impact figures.
    This updater does NOT scrape news sites or Wikipedia for casualties.
    """

    old = existing.get("casualties")
    if not isinstance(old, dict):
        old = {}

    # Support the older nested stats shape too.
    stats = existing.get("stats") if isinstance(existing.get("stats"), dict) else {}

    def keep(key):
        direct = old.get(key)
        if direct is not None:
            return number(direct)

        stat = stats.get(key)
        if isinstance(stat, dict):
            return number(stat.get("value"))

        direct_old = existing.get(key)
        return number(direct_old)

    return {
        "deaths": keep("deaths"),
        "missing": keep("missing"),
        "injured": keep("injured"),
        "rescued": keep("rescued"),
        "source": old.get("source") or existing.get("impact_source"),
        "as_of": old.get("as_of") or existing.get("impact_as_of"),
    }


def validate_output(data: dict):
    rainfall = data.get("rainfall", {})
    if not isinstance(rainfall, dict):
        raise RuntimeError("rainfall must be an object")

    if number(rainfall.get("max_24h_mm")) is None:
        raise RuntimeError("rainfall.max_24h_mm is missing")

    rivers = data.get("rivers")
    if not isinstance(rivers, list) or len(rivers) < 3:
        raise RuntimeError("At least three river observations are required")

    for river in rivers:
        value = number(river.get("value"))
        warning = number(river.get("warning"))
        danger = number(river.get("danger"))

        if value is None or warning is None or danger is None:
            raise RuntimeError(f"Incomplete river record: {river}")

        if warning <= 0 or danger <= warning:
            raise RuntimeError(f"Bad river thresholds: {river}")

    casualties = data.get("casualties", {})
    for key in ("deaths", "missing", "injured", "rescued"):
        value = casualties.get(key)
        if value is not None and number(value) is None:
            raise RuntimeError(f"Invalid casualty value: {key}={value}")


def main():
    print("Starting verified Nepal Flood data update...")

    existing = read_existing()

    try:
        dhm_text = fetch_text(DHM_URL)
        dhm = extract_dhm(dhm_text)
    except Exception as exc:
        print(f"DHM update failed: {exc}", file=sys.stderr)
        raise SystemExit(1)

    casualties = preserve_impact(existing)

    output = {
        "schema_version": "1.5",
        "status": "LIVE",
        "updated_at": iso_now(),
        "updated_at_npt": now_npt().strftime("%d %b %Y | %H:%M:%S NPT"),
        "sources": {
            "rainfall": {
                "name": "DHM",
                "url": DHM_URL,
                "as_of": dhm["rainfall"]["as_of"],
            },
            "river": {
                "name": "DHM River Watch",
                "url": "https://dhm.gov.np/hydrology/river-watch",
                "as_of": iso_now(),
            },
            "casualties": {
                "name": casualties.get("source") or "NDRRMA / Nepal Police",
                "as_of": casualties.get("as_of"),
            },
        },
        "rainfall": dhm["rainfall"],
        "rivers": dhm["rivers"],
        "casualties": casualties,
        "infrastructure": {
            "homes": existing.get("infrastructure", {}).get("homes")
            if isinstance(existing.get("infrastructure"), dict) else existing.get("homes"),
            "bridges": existing.get("infrastructure", {}).get("bridges")
            if isinstance(existing.get("infrastructure"), dict) else existing.get("bridges"),
        },
        "operations": {
            "teams": existing.get("operations", {}).get("teams")
            if isinstance(existing.get("operations"), dict) else existing.get("teams"),
            "rescued": casualties.get("rescued"),
            "vehicles": existing.get("operations", {}).get("vehicles")
            if isinstance(existing.get("operations"), dict) else existing.get("vehicles"),
            "relief": existing.get("operations", {}).get("relief")
            if isinstance(existing.get("operations"), dict) else existing.get("relief"),
        },
        "weather": existing.get("weather") if isinstance(existing.get("weather"), list) else [],
        "ticker": existing.get("ticker"),
    }

    validate_output(output)

    tmp = DATA_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(DATA_FILE)

    print(f"Updated data.json at {output['updated_at_npt']}")
    print(f"DHM rainfall: {output['rainfall']['max_24h_mm']} mm at {output['rainfall']['station']}")
    for river in output["rivers"]:
        print(
            f"{river['name']} ({river['station']}): "
            f"{river['value']} m | warning {river['warning']} | danger {river['danger']}"
        )

    if casualties["deaths"] is not None:
        print(f"Preserved verified deaths: {casualties['deaths']}")
    if casualties["missing"] is not None:
        print(f"Preserved verified missing: {casualties['missing']}")
    if casualties["injured"] is not None:
        print(f"Preserved verified injured: {casualties['injured']}")
    if casualties["rescued"] is not None:
        print(f"Preserved verified rescued: {casualties['rescued']}")


if __name__ == "__main__":
    main()
