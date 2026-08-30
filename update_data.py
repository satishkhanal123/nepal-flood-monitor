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
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"

DHM_URL = "https://www.dhm.gov.np/?locale=en"
DHM_RIVER_URL = "https://dhm.gov.np/hydrology/river-watch"

TIMEOUT = 30

NPT = timezone(timedelta(hours=5, minutes=45))


# ============================================================
# KNOWN DHM RIVER OBSERVATIONS
# ============================================================

RIVER_PATTERNS = [
    (
        "Narayani",
        "Devghat",
        r"Narayani\s+at\s+Devghat\s+WL:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Karnali",
        "Chisapani",
        r"Karnali\s+at\s+Chisapani\s+WL:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Kankai",
        "Mainachuli",
        r"Kankai\s+River\s+at\s+Mainachuli\s+WL:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Babai",
        "Chepang",
        r"Babai\s+at\s+Chepang\s+WL:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Mahakali",
        "Parigaon",
        r"Mahakali\s+at\s+Parigaon\s+WL:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"WR:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s+"
        r"DL:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
]


# ============================================================
# HTML TEXT EXTRACTION
# ============================================================

class DHMTextParser(HTMLParser):
    """
    Extract visible text from DHM HTML.

    Script/style/noscript content is ignored so JavaScript or CSS
    cannot interfere with the data parser.
    """

    def __init__(self):
        super().__init__()
        self.parts = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "template"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "template"}:
            if self._ignored_depth > 0:
                self._ignored_depth -= 1

    def handle_data(self, data):
        if self._ignored_depth == 0:
            self.parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.parts)


def html_to_text(html: str) -> str:
    """
    Convert DHM HTML into normalized readable text.
    """

    parser = DHMTextParser()

    try:
        parser.feed(html)
        parser.close()
        text = parser.get_text()
    except Exception as exc:
        raise RuntimeError(
            f"Unable to parse DHM HTML: {exc}"
        ) from exc

    # Decode HTML entities such as &nbsp;
    text = unescape(text)

    # Normalize non-breaking spaces.
    text = text.replace("\xa0", " ")

    # Collapse all whitespace into single spaces.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# TIME HELPERS
# ============================================================

def now_npt() -> datetime:
    return datetime.now(NPT)


def iso_now() -> str:
    return now_npt().isoformat(timespec="seconds")


# ============================================================
# NETWORK
# ============================================================

def fetch_text(url: str) -> str:
    """
    Download the official DHM page.
    """

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; Nepal-Flood-Monitor/1.5; +https://github.com/)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )

    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()

            charset = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            return raw.decode(
                charset,
                errors="replace",
            )

    except Exception as exc:
        raise RuntimeError(
            f"Unable to fetch DHM page: {exc}"
        ) from exc


# ============================================================
# EXISTING DATA
# ============================================================

def read_existing() -> dict:
    """
    Read the existing data.json.

    Existing verified impact data is intentionally preserved.
    """

    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:
            value = json.load(f)

        if not isinstance(value, dict):
            raise RuntimeError(
                "data.json must contain a JSON object"
            )

        return value

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"data.json is invalid JSON: {exc}"
        ) from exc

    except OSError as exc:
        raise RuntimeError(
            f"Unable to read data.json: {exc}"
        ) from exc


# ============================================================
# NUMBER HELPERS
# ============================================================

def number(value):
    """
    Convert a value into a non-negative int/float.

    Invalid or negative values become None.
    """

    if value is None:
        return None

    try:
        value = float(value)

        if value < 0:
            return None

        if value.is_integer():
            return int(value)

        return value

    except (TypeError, ValueError):
        return None


# ============================================================
# DHM RAINFALL PARSER
# ============================================================

def extract_rainfall(text: str) -> dict:
    """
    Extract the current DHM maximum 24-hour rainfall.

    Current DHM format is similar to:

        Max 24hr: 120.4 mm Arughat (rainfall)

    The parser deliberately stops at '(rainfall)' so the station
    name does not accidentally include the following river data.
    """

    pattern = re.compile(
        r"Max\s+24\s*hr\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)"
        r"\s*mm\s*"
        r"(.+?)"
        r"\s*\(\s*rainfall\s*\)",
        flags=re.I,
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "DHM rainfall value was not found. "
            "Expected a line similar to "
            "'Max 24hr: 120.4 mm Station (rainfall)'."
        )

    rainfall_value = number(match.group(1))
    station = match.group(2).strip()

    if rainfall_value is None:
        raise RuntimeError(
            f"Invalid DHM rainfall value: {match.group(1)}"
        )

    if not station:
        raise RuntimeError(
            "DHM rainfall station name was empty"
        )

    return {
        "max_24h_mm": rainfall_value,
        "station": station,
        "source": "DHM",
        "source_url": DHM_URL,
        "as_of": iso_now(),
    }


# ============================================================
# RIVER PARSER
# ============================================================

def river_status(
    value: float,
    warning: float,
    danger: float,
) -> str:
    """
    Determine river status from DHM thresholds.
    """

    if value >= danger:
        return "Above Danger Level"

    if value >= warning:
        return "Above Warning Level"

    return "Below Warning Level"


def extract_rivers(text: str) -> list:
    """
    Extract known DHM river observations.
    """

    rivers = []

    for name, station, pattern in RIVER_PATTERNS:
        match = re.search(
            pattern,
            text,
            flags=re.I,
        )

        if not match:
            continue

        value = number(match.group(1))
        warning = number(match.group(2))
        danger = number(match.group(3))

        if (
            value is None
            or warning is None
            or danger is None
        ):
            raise RuntimeError(
                f"Incomplete DHM river record for {name}"
            )

        if warning <= 0:
            raise RuntimeError(
                f"Invalid warning level for {name}: "
                f"{warning}"
            )

        if danger <= warning:
            raise RuntimeError(
                f"Invalid threshold order for {name}: "
                f"warning={warning}, danger={danger}"
            )

        if value < 0:
            raise RuntimeError(
                f"Invalid river value for {name}: {value}"
            )

        rivers.append(
            {
                "name": name,
                "station": station,
                "value": value,
                "warning": warning,
                "danger": danger,
                "status": river_status(
                    value,
                    warning,
                    danger,
                ),
                "source": "DHM",
                "source_url": DHM_RIVER_URL,
                "as_of": iso_now(),
            }
        )

    return rivers


# ============================================================
# COMPLETE DHM EXTRACTION
# ============================================================

def extract_dhm(html: str) -> dict:
    """
    Extract rainfall and river data from the official DHM page.
    """

    if not html or not html.strip():
        raise RuntimeError(
            "DHM returned an empty response"
        )

    text = html_to_text(html)

    if len(text) < 100:
        raise RuntimeError(
            "DHM response contained too little readable text"
        )

    rainfall = extract_rainfall(text)
    rivers = extract_rivers(text)

    if len(rivers) < 3:
        raise RuntimeError(
            "DHM returned too few river observations: "
            f"{len(rivers)}. Expected at least 3."
        )

    return {
        "rainfall": rainfall,
        "rivers": rivers,
    }


# ============================================================
# VERIFIED IMPACT DATA
# ============================================================

def preserve_impact(existing: dict) -> dict:
    """
    Preserve already verified impact figures.

    This updater does NOT scrape casualties from news sites,
    social media, Wikipedia, or unofficial sources.
    """

    old = existing.get("casualties")

    if not isinstance(old, dict):
        old = {}

    # Support older nested stats format.
    stats = existing.get("stats")

    if not isinstance(stats, dict):
        stats = {}

    def keep(key):
        # Preferred current structure.
        direct = old.get(key)

        if direct is not None:
            return number(direct)

        # Older stats structure.
        stat = stats.get(key)

        if isinstance(stat, dict):
            return number(stat.get("value"))

        # Older top-level structure.
        direct_old = existing.get(key)

        return number(direct_old)

    return {
        "deaths": keep("deaths"),
        "missing": keep("missing"),
        "injured": keep("injured"),
        "rescued": keep("rescued"),
        "source": (
            old.get("source")
            or existing.get("impact_source")
        ),
        "as_of": (
            old.get("as_of")
            or existing.get("impact_as_of")
        ),
    }


# ============================================================
# OUTPUT VALIDATION
# ============================================================

def validate_output(data: dict):
    """
    Final safety checks before data.json is replaced.
    """

    if not isinstance(data, dict):
        raise RuntimeError(
            "Output must be a JSON object"
        )

    # --------------------------------------------------------
    # Rainfall
    # --------------------------------------------------------

    rainfall = data.get("rainfall")

    if not isinstance(rainfall, dict):
        raise RuntimeError(
            "rainfall must be an object"
        )

    rainfall_value = number(
        rainfall.get("max_24h_mm")
    )

    if rainfall_value is None:
        raise RuntimeError(
            "rainfall.max_24h_mm is missing or invalid"
        )

    if not rainfall.get("station"):
        raise RuntimeError(
            "rainfall.station is missing"
        )

    # --------------------------------------------------------
    # Rivers
    # --------------------------------------------------------

    rivers = data.get("rivers")

    if not isinstance(rivers, list):
        raise RuntimeError(
            "rivers must be an array"
        )

    if len(rivers) < 3:
        raise RuntimeError(
            "At least three river observations are required"
        )

    for river in rivers:
        if not isinstance(river, dict):
            raise RuntimeError(
                f"Invalid river record: {river}"
            )

        value = number(river.get("value"))
        warning = number(river.get("warning"))
        danger = number(river.get("danger"))

        if (
            value is None
            or warning is None
            or danger is None
        ):
            raise RuntimeError(
                f"Incomplete river record: {river}"
            )

        if warning <= 0:
            raise RuntimeError(
                f"Invalid warning threshold: {river}"
            )

        if danger <= warning:
            raise RuntimeError(
                f"Invalid danger threshold: {river}"
            )

    # --------------------------------------------------------
    # Casualties
    # --------------------------------------------------------

    casualties = data.get("casualties")

    if not isinstance(casualties, dict):
        raise RuntimeError(
            "casualties must be an object"
        )

    for key in (
        "deaths",
        "missing",
        "injured",
        "rescued",
    ):
        value = casualties.get(key)

        if (
            value is not None
            and number(value) is None
        ):
            raise RuntimeError(
                f"Invalid casualty value: "
                f"{key}={value}"
            )

    # --------------------------------------------------------
    # Required metadata
    # --------------------------------------------------------

    if data.get("schema_version") != "1.5":
        raise RuntimeError(
            "Unexpected schema_version"
        )

    if data.get("status") != "LIVE":
        raise RuntimeError(
            "Output status must be LIVE"
        )


# ============================================================
# DATA BUILDING
# ============================================================

def build_output(
    existing: dict,
    dhm: dict,
) -> dict:
    """
    Build the stable data.json structure used by the dashboard.
    """

    casualties = preserve_impact(existing)

    old_infrastructure = existing.get(
        "infrastructure"
    )

    if not isinstance(old_infrastructure, dict):
        old_infrastructure = {}

    old_operations = existing.get(
        "operations"
    )

    if not isinstance(old_operations, dict):
        old_operations = {}

    output = {
        "schema_version": "1.5",
        "status": "LIVE",

        "updated_at": iso_now(),

        "updated_at_npt": (
            now_npt().strftime(
                "%d %b %Y | %H:%M:%S NPT"
            )
        ),

        "sources": {
            "rainfall": {
                "name": "DHM",
                "url": DHM_URL,
                "as_of": dhm["rainfall"]["as_of"],
            },

            "river": {
                "name": "DHM River Watch",
                "url": DHM_RIVER_URL,
                "as_of": iso_now(),
            },

            "casualties": {
                "name": (
                    casualties.get("source")
                    or "NDRRMA / Nepal Police"
                ),
                "as_of": casualties.get("as_of"),
            },
        },

        "rainfall": dhm["rainfall"],

        "rivers": dhm["rivers"],

        "casualties": casualties,

        "infrastructure": {
            "homes": old_infrastructure.get(
                "homes"
            ),
            "bridges": old_infrastructure.get(
                "bridges"
            ),
        },

        "operations": {
            "teams": old_operations.get(
                "teams"
            ),
            "rescued": casualties.get(
                "rescued"
            ),
            "vehicles": old_operations.get(
                "vehicles"
            ),
            "relief": old_operations.get(
                "relief"
            ),
        },

        "weather": (
            existing.get("weather")
            if isinstance(
                existing.get("weather"),
                list,
            )
            else []
        ),

        "ticker": existing.get(
            "ticker"
        ),
    }

    return output


# ============================================================
# SAFE JSON WRITE
# ============================================================

def write_data(data: dict):
    """
    Validate and atomically replace data.json.
    """

    validate_output(data)

    tmp = DATA_FILE.with_suffix(
        ".json.tmp"
    )

    try:
        with tmp.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )
            f.write("\n")

        tmp.replace(DATA_FILE)

    except OSError as exc:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

        raise RuntimeError(
            f"Unable to write data.json: {exc}"
        ) from exc


# ============================================================
# MAIN
# ============================================================

def main():
    print(
        "Starting verified Nepal Flood data update..."
    )

    print(
        f"DHM source: {DHM_URL}"
    )

    # --------------------------------------------------------
    # Read existing data first.
    # --------------------------------------------------------

    existing = read_existing()

    # --------------------------------------------------------
    # Fetch official DHM data.
    # --------------------------------------------------------

    print(
        "Fetching official DHM data..."
    )

    try:
        dhm_html = fetch_text(
            DHM_URL
        )

        print(
            f"Received DHM response: "
            f"{len(dhm_html):,} bytes"
        )

        dhm = extract_dhm(
            dhm_html
        )

    except Exception as exc:
        print(
            f"DHM update failed: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # Build output.
    # --------------------------------------------------------

    output = build_output(
        existing,
        dhm,
    )

    # --------------------------------------------------------
    # Validate and write.
    # --------------------------------------------------------

    try:
        write_data(output)

    except Exception as exc:
        print(
            f"Data validation/write failed: {exc}",
            file=sys.stderr,
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # Print useful QA information.
    # --------------------------------------------------------

    print()
    print(
        "========================================"
    )
    print(
        " Nepal Flood data update successful"
    )
    print(
        "========================================"
    )

    print(
        f"Updated: "
        f"{output['updated_at_npt']}"
    )

    print(
        f"Rainfall: "
        f"{output['rainfall']['max_24h_mm']} mm"
    )

    print(
        f"Station: "
        f"{output['rainfall']['station']}"
    )

    print()

    print(
        f"River observations: "
        f"{len(output['rivers'])}"
    )

    for river in output["rivers"]:
        print(
            f"- {river['name']} "
            f"({river['station']}): "
            f"{river['value']} m | "
            f"warning {river['warning']} m | "
            f"danger {river['danger']} m | "
            f"{river['status']}"
        )

    print()

    casualties = output["casualties"]

    print(
        "Preserved verified impact data:"
    )

    print(
        f"- Deaths: "
        f"{casualties['deaths']}"
    )

    print(
        f"- Missing: "
        f"{casualties['missing']}"
    )

    print(
        f"- Injured: "
        f"{casualties['injured']}"
    )

    print(
        f"- Rescued: "
        f"{casualties['rescued']}"
    )

    print()

    print(
        "data.json validation: PASSED"
    )

    print(
        "Update complete."
    )


if __name__ == "__main__":
    main()