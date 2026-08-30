#!/usr/bin/env python3
"""
Nepal Flood 2026 — verified data updater

Milestone 1.5 — Data Correctness

Rules:
- Read rainfall and river observations from official DHM pages.
- Never invent casualty, infrastructure, rescue, or relief numbers.
- Preserve previously verified non-null impact values when no new verified value is available.
- Fail the run if required DHM observations cannot be verified.
- Write the exact JSON shape expected by the locked index.html.
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

DHM_HOME = "https://www.dhm.gov.np/?locale=en"
DHM_RIVER_WATCH = "https://dhm.gov.np/hydrology/river-watch"
TIMEOUT = 30
NPT = timezone(timedelta(hours=5, minutes=45))

# These are the five stations used by the locked dashboard.
RIVER_PATTERNS = [
    (
        "Karnali",
        "Chisapani",
        r"Karnali\s+at\s+Chisapani\s+WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Narayani",
        "Devghat",
        r"Narayani\s+at\s+Devghat\s+WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Kankai",
        "Mainachuli",
        r"Kankai\s+River\s+at\s+Mainachuli\s+WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Babai",
        "Chepang",
        r"Babai\s+at\s+Chepang\s+WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Mahakali",
        "Parigaon",
        r"Mahakali\s+at\s+Parigaon\s+WL:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m"
        r"\s*DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
]


def now_npt() -> datetime:
    return datetime.now(NPT)


def iso_now() -> str:
    return now_npt().isoformat(timespec="seconds")


def display_time() -> str:
    return now_npt().strftime("%d %b %Y | %H:%M:%S NPT")


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Nepal-Flood-Monitor/1.5",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def clean_text(text: str) -> str:
    # HTML often contains tags/whitespace between the visible values.
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def read_existing() -> dict:
    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            value = json.load(f)
    except Exception as exc:
        raise RuntimeError(f"data.json is invalid JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise RuntimeError("data.json must contain a JSON object")

    return value


def number(value):
    if value is None:
        return None

    try:
        n = float(value)
    except (TypeError, ValueError):
        return None

    if n < 0:
        return None

    return int(n) if n.is_integer() else n


def first_number(*values):
    for value in values:
        n = number(value)
        if n is not None:
            return n
    return None


def extract_rainfall(text: str) -> dict:
    patterns = [
        r"Max\s*24hr\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z][A-Za-z0-9 ()_-]*)",
        r"Max\s*24\s*hr\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z][A-Za-z0-9 ()_-]*)",
        r"Maximum\s*24\s*Hour(?:\s*Rainfall)?\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z][A-Za-z0-9 ()_-]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            station = match.group(2).strip(" -:;,")
            return {
                "value": number(match.group(1)),
                "station": station or None,
                "source": "DHM",
                "source_url": DHM_HOME,
                "as_of": iso_now(),
            }

    raise RuntimeError("DHM maximum 24-hour rainfall value was not found")


def extract_rivers(text: str) -> list[dict]:
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
                "source_url": DHM_RIVER_WATCH,
                "as_of": iso_now(),
            }
        )

    if len(rivers) < 3:
        found = ", ".join(r["name"] for r in rivers) or "none"
        raise RuntimeError(
            f"DHM returned too few verified river observations: "
            f"{len(rivers)} ({found})"
        )

    return rivers


def preserve_impact(existing: dict) -> dict:
    """
    Preserve existing verified impact values.

    This updater does not guess casualty or damage figures.
    A null value remains null until a trusted source supplies a value.
    """

    old_casualties = existing.get("casualties")
    if not isinstance(old_casualties, dict):
        old_casualties = {}

    old_infrastructure = existing.get("infrastructure")
    if not isinstance(old_infrastructure, dict):
        old_infrastructure = {}

    old_operations = existing.get("operations")
    if not isinstance(old_operations, dict):
        old_operations = {}

    def keep(*values):
        for value in values:
            n = number(value)
            if n is not None:
                return n
        return None

    deaths = keep(
        old_casualties.get("deaths"),
        existing.get("deaths"),
    )
    missing = keep(
        old_casualties.get("missing"),
        existing.get("missing"),
    )
    injured = keep(
        old_casualties.get("injured"),
        existing.get("injured"),
    )
    rescued = keep(
        old_casualties.get("rescued"),
        old_operations.get("rescued"),
        existing.get("rescued"),
    )

    return {
        "deaths": deaths,
        "missing": missing,
        "injured": injured,
        "rescued": rescued,
        "source": (
            old_casualties.get("source")
            or existing.get("impact_source")
            or "Not verified"
        ),
        "as_of": old_casualties.get("as_of") or existing.get("impact_as_of"),
        "infrastructure": {
            "homes": keep(
                old_infrastructure.get("homes"),
                existing.get("homes"),
            ),
            "bridges": keep(
                old_infrastructure.get("bridges"),
                existing.get("bridges"),
            ),
        },
        "operations": {
            "teams": keep(
                old_operations.get("teams"),
                existing.get("teams"),
            ),
            "vehicles": keep(
                old_operations.get("vehicles"),
                existing.get("vehicles"),
            ),
            "relief": keep(
                old_operations.get("relief"),
                existing.get("relief"),
            ),
        },
    }


def validate_output(data: dict):
    required_top = {
        "schema_version",
        "status",
        "updated_at",
        "updated_at_npt",
        "rainfall",
        "rivers",
        "casualties",
        "infrastructure",
        "operations",
    }

    missing_top = required_top - set(data)
    if missing_top:
        raise RuntimeError(
            f"Missing required output fields: {', '.join(sorted(missing_top))}"
        )

    rainfall = data["rainfall"]
    if not isinstance(rainfall, dict):
        raise RuntimeError("rainfall must be an object")

    if number(rainfall.get("value")) is None:
        raise RuntimeError("rainfall.value is missing")

    if not rainfall.get("station"):
        raise RuntimeError("rainfall.station is missing")

    rivers = data["rivers"]
    if not isinstance(rivers, list) or len(rivers) < 3:
        raise RuntimeError("At least three river observations are required")

    seen = set()

    for river in rivers:
        for field in ("name", "station", "value", "warning", "danger"):
            if field not in river:
                raise RuntimeError(f"River field missing: {field}")

        key = (river["name"], river["station"])
        if key in seen:
            raise RuntimeError(f"Duplicate river station: {key}")
        seen.add(key)

        value = number(river["value"])
        warning = number(river["warning"])
        danger = number(river["danger"])

        if value is None or warning is None or danger is None:
            raise RuntimeError(f"Incomplete river record: {river}")

        if warning <= 0 or danger <= warning:
            raise RuntimeError(f"Bad river thresholds: {river}")

    casualties = data["casualties"]
    if not isinstance(casualties, dict):
        raise RuntimeError("casualties must be an object")

    for key in ("deaths", "missing", "injured", "rescued"):
        value = casualties.get(key)
        if value is not None and number(value) is None:
            raise RuntimeError(f"Invalid casualty value: {key}={value}")

    infrastructure = data["infrastructure"]
    if not isinstance(infrastructure, dict):
        raise RuntimeError("infrastructure must be an object")

    for key in ("homes", "bridges"):
        value = infrastructure.get(key)
        if value is not None and number(value) is None:
            raise RuntimeError(f"Invalid infrastructure value: {key}={value}")

    operations = data["operations"]
    if not isinstance(operations, dict):
        raise RuntimeError("operations must be an object")

    for key in ("teams", "rescued", "vehicles", "relief"):
        value = operations.get(key)
        if value is not None and number(value) is None:
            raise RuntimeError(f"Invalid operations value: {key}={value}")


def build_output(existing: dict, rainfall: dict, rivers: list[dict]) -> dict:
    impact = preserve_impact(existing)
    timestamp = iso_now()

    return {
        "schema_version": "1.5",
        "status": "LIVE",
        "updated_at": timestamp,
        "updated_at_npt": display_time(),

        "rain": {
            "value": rainfall["value"],
            "station": rainfall["station"],
            "source": "DHM",
            "source_url": rainfall["source_url"],
            "as_of": rainfall["as_of"],
        },

        "rivers": rivers,

        "deaths": impact["deaths"],
        "missing": impact["missing"],
        "injured": impact["injured"],

        "homes": impact["infrastructure"]["homes"],
        "bridges": impact["infrastructure"]["bridges"],

        "teams": impact["operations"]["teams"],
        "rescued": impact["rescued"],
        "vehicles": impact["operations"]["vehicles"],
        "relief": impact["operations"]["relief"],

        "casualties": {
            "deaths": impact["deaths"],
            "missing": impact["missing"],
            "injured": impact["injured"],
            "rescued": impact["rescued"],
            "source": impact["source"],
            "as_of": impact["as_of"],
        },

        "infrastructure": {
            "homes": impact["infrastructure"]["homes"],
            "bridges": impact["infrastructure"]["bridges"],
        },

        "operations": {
            "teams": impact["operations"]["teams"],
            "rescued": impact["rescued"],
            "vehicles": impact["operations"]["vehicles"],
            "relief": impact["operations"]["relief"],
        },

        "sources": {
            "rainfall": {
                "name": "DHM",
                "url": DHM_HOME,
                "as_of": rainfall["as_of"],
            },
            "river": {
                "name": "DHM River Watch",
                "url": DHM_RIVER_WATCH,
                "as_of": timestamp,
            },
            "casualties": {
                "name": impact["source"],
                "as_of": impact["as_of"],
            },
        },

        # Keep existing forecast/ticker content. Do not turn monitoring
        # observations into forecasts.
        "weather": (
            existing.get("weather")
            if isinstance(existing.get("weather"), list)
            else []
        ),
        "ticker": existing.get("ticker"),
    }


def write_json_atomic(data: dict):
    tmp = DATA_FILE.with_suffix(".json.tmp")

    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    tmp.replace(DATA_FILE)


def main() -> int:
    print("Starting Nepal Flood 2026 verified data update...")

    existing = read_existing()

    try:
        raw = fetch_text(DHM_HOME)
        text = clean_text(raw)

        rainfall = extract_rainfall(text)
        rivers = extract_rivers(text)

    except Exception as exc:
        print(f"DHM verification failed: {exc}", file=sys.stderr)
        return 1

    output = build_output(existing, rainfall, rivers)

    try:
        validate_output(output)
        write_json_atomic(output)
    except Exception as exc:
        print(f"Output validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Updated data.json: {output['updated_at_npt']}")
    print(
        f"Rainfall: {output['rain']['value']} mm "
        f"at {output['rain']['station']}"
    )

    for river in output["rivers"]:
        print(
            f"{river['name']} ({river['station']}): "
            f"{river['value']} m | "
            f"warning {river['warning']} | "
            f"danger {river['danger']} | "
            f"{river['status']}"
        )

    print(f"Deaths preserved: {output['deaths']}")
    print(f"Missing preserved: {output['missing']}")
    print(f"Injured preserved: {output['injured']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
