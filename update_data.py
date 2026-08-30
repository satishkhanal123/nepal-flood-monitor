#!/usr/bin/env python3
"""
Nepal Flood 2026 — verified data updater

Milestone 1.5

Purpose:
- Fetch current rainfall and river observations from official DHM.
- Retry temporary DHM/network failures.
- Never overwrite good data with incomplete data.
- Preserve verified casualty/impact figures.
- Keep the existing data.json if DHM is temporarily unavailable.
- Validate the complete output before replacing data.json.
- Use Python standard-library modules only.
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.json"


# =========================================================
# OFFICIAL DHM SOURCES
# =========================================================

DHM_URLS = [
    "https://www.dhm.gov.np/?locale=en",
    "https://www.dhm.gov.np/",
]

DHM_RIVER_URL = "https://dhm.gov.np/hydrology/river-watch"


# =========================================================
# NETWORK SETTINGS
# =========================================================

# A GitHub Actions runner may occasionally get a slow response
# from the DHM website. 25 seconds was too aggressive.
TIMEOUT = 60

# Number of attempts for each DHM URL.
MAX_ATTEMPTS = 3

# Seconds between retry attempts.
RETRY_DELAY = 5


# =========================================================
# TIMEZONE
# =========================================================

NPT = timezone(timedelta(hours=5, minutes=45))


# =========================================================
# EXPECTED RIVER OBSERVATIONS
# =========================================================

RIVER_PATTERNS = [
    (
        "Narayani",
        "Devghat",
        r"Narayani\s+at\s+Devghat\s+WL\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"WR\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"DL\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Karnali",
        "Chisapani",
        r"Karnali\s+at\s+Chisapani\s+WL\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"WR\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"DL\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Kankai",
        "Mainachuli",
        r"Kankai\s+River\s+at\s+Mainachuli\s+WL\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"WR\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"DL\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Babai",
        "Chepang",
        r"Babai\s+at\s+Chepang\s+WL\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"WR\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"DL\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
    (
        "Mahakali",
        "Parigaon",
        r"Mahakali\s+at\s+Parigaon\s+WL\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"WR\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m\s*"
        r"DL\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*m",
    ),
]


# =========================================================
# TIME HELPERS
# =========================================================

def now_npt() -> datetime:
    return datetime.now(NPT)


def iso_now() -> str:
    return now_npt().isoformat(timespec="seconds")


def formatted_npt() -> str:
    return now_npt().strftime("%d %b %Y | %H:%M:%S NPT")


# =========================================================
# GENERAL HELPERS
# =========================================================

def number(value):
    """
    Convert a value to a non-negative int/float.

    Returns None for invalid values.
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


def clean_text(text: str) -> str:
    """
    Convert DHM HTML into a reasonably clean searchable text string.
    """

    # Decode HTML entities.
    text = html.unescape(text)

    # Remove scripts and styles.
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        text,
        flags=re.I | re.S,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.I | re.S,
    )

    # Remove remaining HTML tags.
    text = re.sub(r"<[^>]+>", " ", text)

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# FILE HANDLING
# =========================================================

def read_existing() -> dict:
    """
    Read the existing data.json.

    An invalid existing file is a hard error because silently
    replacing or ignoring corrupted data would be unsafe.
    """

    if not DATA_FILE.exists():
        return {}

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            value = json.load(file)

        if not isinstance(value, dict):
            raise RuntimeError("data.json root must be an object")

        return value

    except Exception as exc:
        raise RuntimeError(
            f"data.json is invalid: {exc}"
        ) from exc


# =========================================================
# DHM NETWORK FETCH
# =========================================================

def fetch_text_once(url: str) -> str:
    """
    Fetch one DHM page.

    Raises an exception if the request fails.
    """

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; Nepal-Flood-Monitor/1.5; "
                "+https://github.com/)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    with urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read()

        charset = (
            response.headers.get_content_charset()
            or "utf-8"
        )

        return raw.decode(charset, errors="replace")


def fetch_dhm_page() -> tuple[str, str]:
    """
    Try the official DHM URLs several times.

    Returns:
        (clean_text, successful_url)

    Raises RuntimeError only after every attempt fails.
    """

    errors = []

    for url in DHM_URLS:

        for attempt in range(1, MAX_ATTEMPTS + 1):

            print(
                f"Fetching official DHM data "
                f"(attempt {attempt}/{MAX_ATTEMPTS}): {url}"
            )

            try:
                raw = fetch_text_once(url)

                if not raw.strip():
                    raise RuntimeError(
                        "DHM returned an empty response"
                    )

                text = clean_text(raw)

                # Basic sanity check before accepting the page.
                if "Max 24hr" not in text:
                    raise RuntimeError(
                        "DHM page did not contain the expected "
                        "rainfall section"
                    )

                if "Karnali at Chisapani" not in text:
                    raise RuntimeError(
                        "DHM page did not contain the expected "
                        "river section"
                    )

                print(
                    f"Successfully fetched DHM data from {url}"
                )

                return text, url

            except HTTPError as exc:
                message = (
                    f"HTTP {exc.code} {exc.reason}"
                )

                errors.append(
                    f"{url} attempt {attempt}: {message}"
                )

                print(
                    f"DHM request failed: {message}",
                    file=sys.stderr,
                )

            except URLError as exc:
                message = str(exc.reason)

                errors.append(
                    f"{url} attempt {attempt}: {message}"
                )

                print(
                    f"DHM network error: {message}",
                    file=sys.stderr,
                )

            except TimeoutError as exc:
                message = str(exc) or "timeout"

                errors.append(
                    f"{url} attempt {attempt}: {message}"
                )

                print(
                    f"DHM timeout: {message}",
                    file=sys.stderr,
                )

            except Exception as exc:
                message = str(exc)

                errors.append(
                    f"{url} attempt {attempt}: {message}"
                )

                print(
                    f"DHM request failed: {message}",
                    file=sys.stderr,
                )

            if attempt < MAX_ATTEMPTS:
                print(
                    f"Waiting {RETRY_DELAY}s before retry..."
                )
                time.sleep(RETRY_DELAY)

    error_text = "\n".join(errors)

    raise RuntimeError(
        "Unable to fetch official DHM data after all retries.\n"
        + error_text
    )


# =========================================================
# DHM DATA EXTRACTION
# =========================================================

def extract_dhm(text: str, source_url: str) -> dict:
    """
    Extract rainfall and river data from the official DHM page.
    """

    # -----------------------------------------------------
    # RAINFALL
    # -----------------------------------------------------

    rainfall_match = re.search(
        r"Max\s*24hr\s*:\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*mm\s+"
        r"([A-Za-z][A-Za-z0-9 ()_./-]*?)"
        r"(?=\s+Narayani\s+at|\s+Karnali\s+at|\s*$)",
        text,
        flags=re.I,
    )

    if not rainfall_match:

        # Slightly looser fallback for DHM formatting changes.
        rainfall_match = re.search(
            r"Max\s*24hr\s*:\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*mm\s+"
            r"([A-Za-z][A-Za-z0-9 ()_./-]*)",
            text,
            flags=re.I,
        )

    rainfall_value = (
        number(rainfall_match.group(1))
        if rainfall_match
        else None
    )

    rainfall_station = (
        rainfall_match.group(2).strip()
        if rainfall_match
        else None
    )

    if rainfall_value is None:
        raise RuntimeError(
            "DHM rainfall value was not found"
        )

    if not rainfall_station:
        raise RuntimeError(
            "DHM rainfall station was not found"
        )

    rainfall = {
        "max_24h_mm": rainfall_value,
        "station": rainfall_station,
        "source": "DHM",
        "source_url": source_url,
        "as_of": iso_now(),
    }


    # -----------------------------------------------------
    # RIVERS
    # -----------------------------------------------------

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
            continue

        if warning <= 0:
            raise RuntimeError(
                f"Invalid warning threshold for {name}: "
                f"{warning}"
            )

        if danger <= warning:
            raise RuntimeError(
                f"Invalid danger threshold for {name}: "
                f"warning={warning}, danger={danger}"
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
                "source_url": DHM_RIVER_URL,
                "as_of": iso_now(),
            }
        )

    if len(rivers) < 3:
        raise RuntimeError(
            "DHM returned too few valid river observations: "
            f"{len(rivers)}"
        )

    return {
        "rainfall": rainfall,
        "rivers": rivers,
    }


# =========================================================
# PRESERVE VERIFIED IMPACT DATA
# =========================================================

def preserve_impact(existing: dict) -> dict:
    """
    Preserve already verified casualty/impact figures.

    This updater does NOT scrape news sites, social media,
    Wikipedia, or other unofficial sources.
    """

    old = existing.get("casualties")

    if not isinstance(old, dict):
        old = {}

    stats = (
        existing.get("stats")
        if isinstance(existing.get("stats"), dict)
        else {}
    )

    def keep(key):
        # Preferred current structure.
        direct = old.get(key)

        if direct is not None:
            return number(direct)

        # Older nested structure.
        stat = stats.get(key)

        if isinstance(stat, dict):
            return number(stat.get("value"))

        # Older flat structure.
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


# =========================================================
# PRESERVE OTHER VERIFIED DATA
# =========================================================

def preserve_infrastructure(existing: dict) -> dict:
    infrastructure = existing.get("infrastructure")

    if isinstance(infrastructure, dict):
        return {
            "homes": number(infrastructure.get("homes")),
            "bridges": number(infrastructure.get("bridges")),
        }

    return {
        "homes": number(existing.get("homes")),
        "bridges": number(existing.get("bridges")),
    }


def preserve_operations(
    existing: dict,
    casualties: dict,
) -> dict:

    operations = existing.get("operations")

    if not isinstance(operations, dict):
        operations = {}

    return {
        "teams": number(
            operations.get("teams")
            if operations.get("teams") is not None
            else existing.get("teams")
        ),

        "rescued": casualties.get("rescued"),

        "vehicles": number(
            operations.get("vehicles")
            if operations.get("vehicles") is not None
            else existing.get("vehicles")
        ),

        "relief": operations.get(
            "relief",
            existing.get("relief")
        ),
    }


# =========================================================
# OUTPUT VALIDATION
# =========================================================

def validate_output(data: dict):
    """
    Validate the complete data structure before writing it.
    """

    if not isinstance(data, dict):
        raise RuntimeError(
            "Output root must be an object"
        )

    if data.get("schema_version") != "1.5":
        raise RuntimeError(
            "Unexpected schema_version"
        )

    if data.get("status") != "LIVE":
        raise RuntimeError(
            "Output status must be LIVE"
        )


    # -----------------------------------------------------
    # RAINFALL
    # -----------------------------------------------------

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
            "rainfall.max_24h_mm is missing"
        )

    if not rainfall.get("station"):
        raise RuntimeError(
            "rainfall.station is missing"
        )


    # -----------------------------------------------------
    # RIVERS
    # -----------------------------------------------------

    rivers = data.get("rivers")

    if not isinstance(rivers, list):
        raise RuntimeError(
            "rivers must be a list"
        )

    if len(rivers) < 3:
        raise RuntimeError(
            "At least three river observations are required"
        )

    seen = set()

    for river in rivers:

        if not isinstance(river, dict):
            raise RuntimeError(
                f"Invalid river record: {river}"
            )

        name = river.get("name")
        station = river.get("station")

        if not name or not station:
            raise RuntimeError(
                f"River name/station missing: {river}"
            )

        if name in seen:
            raise RuntimeError(
                f"Duplicate river record: {name}"
            )

        seen.add(name)

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


    # -----------------------------------------------------
    # CASUALTIES
    # -----------------------------------------------------

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

        if value is not None and number(value) is None:
            raise RuntimeError(
                f"Invalid casualty value: "
                f"{key}={value}"
            )


    # -----------------------------------------------------
    # SOURCES
    # -----------------------------------------------------

    sources = data.get("sources")

    if not isinstance(sources, dict):
        raise RuntimeError(
            "sources must be an object"
        )

    if not sources.get("rainfall"):
        raise RuntimeError(
            "rainfall source metadata missing"
        )

    if not sources.get("river"):
        raise RuntimeError(
            "river source metadata missing"
        )


# =========================================================
# ATOMIC JSON WRITE
# =========================================================

def write_json_atomic(data: dict):
    """
    Write data.json safely.

    The old data.json remains untouched if writing fails.
    """

    tmp = DATA_FILE.with_suffix(
        ".json.tmp"
    )

    try:

        with tmp.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

            file.write("\n")

        tmp.replace(DATA_FILE)

    except Exception:

        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

        raise


# =========================================================
# MAIN UPDATE
# =========================================================

def main():

    print(
        "Starting verified Nepal Flood data update..."
    )

    existing = read_existing()


    # -----------------------------------------------------
    # FETCH DHM
    # -----------------------------------------------------

    try:

        dhm_text, dhm_source_url = fetch_dhm_page()

        dhm = extract_dhm(
            dhm_text,
            dhm_source_url,
        )

    except Exception as exc:

        # -------------------------------------------------
        # IMPORTANT:
        #
        # A temporary DHM outage must NOT destroy the last
        # valid data.json.
        #
        # We deliberately leave data.json untouched.
        # QA will check the existing file.
        # -------------------------------------------------

        print(
            "",
            file=sys.stderr,
        )

        print(
            "WARNING: Official DHM data could not be "
            "refreshed during this run.",
            file=sys.stderr,
        )

        print(
            f"Reason: {exc}",
            file=sys.stderr,
        )

        print(
            "Keeping the existing verified data.json "
            "unchanged.",
            file=sys.stderr,
        )

        print(
            "The next scheduled run will try again.",
            file=sys.stderr,
        )

        # Exit successfully so the QA step can inspect
        # the last known-good data.json.
        return 0


    # -----------------------------------------------------
    # PRESERVE VERIFIED DATA
    # -----------------------------------------------------

    casualties = preserve_impact(existing)

    infrastructure = preserve_infrastructure(
        existing
    )

    operations = preserve_operations(
        existing,
        casualties,
    )


    # -----------------------------------------------------
    # BUILD OUTPUT
    # -----------------------------------------------------

    timestamp = iso_now()

    output = {
        "schema_version": "1.5",

        "status": "LIVE",

        "updated_at": timestamp,

        "updated_at_npt": formatted_npt(),

        "sources": {
            "rainfall": {
                "name": "DHM",
                "url": dhm_source_url,
                "as_of": dhm["rainfall"]["as_of"],
            },

            "river": {
                "name": "DHM River Watch",
                "url": DHM_RIVER_URL,
                "as_of": timestamp,
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

        "infrastructure": infrastructure,

        "operations": operations,

        "weather": (
            existing.get("weather")
            if isinstance(
                existing.get("weather"),
                list,
            )
            else []
        ),

        "ticker": existing.get("ticker"),
    }


    # -----------------------------------------------------
    # FINAL VALIDATION
    # -----------------------------------------------------

    validate_output(output)


    # -----------------------------------------------------
    # WRITE
    # -----------------------------------------------------

    write_json_atomic(output)


    # -----------------------------------------------------
    # LOG RESULTS
    # -----------------------------------------------------

    print("")
    print(
        "SUCCESS: data.json updated successfully."
    )

    print(
        f"Updated at: {output['updated_at_npt']}"
    )

    print(
        "DHM rainfall: "
        f"{output['rainfall']['max_24h_mm']} mm "
        f"at {output['rainfall']['station']}"
    )

    print("")
    print("River observations:")

    for river in output["rivers"]:

        print(
            f"- {river['name']} "
            f"({river['station']}): "
            f"{river['value']} m | "
            f"warning {river['warning']} m | "
            f"danger {river['danger']} m | "
            f"{river['status']}"
        )


    # -----------------------------------------------------
    # IMPACT DATA
    # -----------------------------------------------------

    print("")
    print("Preserved verified impact data:")

    if casualties["deaths"] is not None:
        print(
            f"- Deaths: {casualties['deaths']}"
        )
    else:
        print("- Deaths: not available")

    if casualties["missing"] is not None:
        print(
            f"- Missing: {casualties['missing']}"
        )
    else:
        print("- Missing: not available")

    if casualties["injured"] is not None:
        print(
            f"- Injured: {casualties['injured']}"
        )
    else:
        print("- Injured: not available")

    if casualties["rescued"] is not None:
        print(
            f"- Rescued: {casualties['rescued']}"
        )
    else:
        print("- Rescued: not available")


    print("")
    print("Milestone 1.5 data update completed.")

    return 0


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    raise SystemExit(main())