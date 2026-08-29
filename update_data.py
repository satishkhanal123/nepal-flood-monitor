import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURATION
# ============================================================

DHM_HOME_URL = "https://www.dhm.gov.np/"

OUTPUT_FILE = Path(__file__).with_name("data.json")

TIMEOUT = 30


# Stations used by our dashboard
TARGET_RIVERS = {
    "Karnali": {
        "station": "Chisapani",
        "warning": 10.0,
        "danger": 10.8,
    },
    "Narayani": {
        "station": "Devghat",
        "warning": 7.3,
        "danger": 9.0,
    },
    "Kankai": {
        "station": "Mainachuli",
        "warning": 3.8,
        "danger": 4.3,
    },
    "Babai": {
        "station": "Chepang",
        "warning": 5.5,
        "danger": 6.8,
    },
    "Mahakali": {
        "station": "Parigaon",
        "warning": 6.8,
        "danger": 8.0,
    },
}


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    """Remove extra spaces and line breaks."""
    return re.sub(r"\s+", " ", text or "").strip()


def to_number(value):
    """Convert text to float when possible."""
    if value is None:
        return None

    value = str(value).strip()

    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def format_number(value):
    """Return an integer when possible, otherwise one decimal."""
    if value is None:
        return None

    if float(value).is_integer():
        return int(value)

    return round(float(value), 1)


def get_status(level, warning, danger):
    """Calculate river warning status."""
    if level is None:
        return "UNKNOWN"

    if level >= danger:
        return "DANGER"

    if level >= warning:
        return "WATCH"

    return "NORMAL"


# ============================================================
# FETCH DHM
# ============================================================

def fetch_dhm_homepage():
    print("Opening DHM homepage...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }

    response = requests.get(
        DHM_HOME_URL,
        headers=headers,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    print(f"DHM response: HTTP {response.status_code}")

    return response.text


# ============================================================
# PARSE RAINFALL
# ============================================================

def extract_max_rainfall(text):
    """
    Extract the maximum 24-hour rainfall shown by DHM.

    Example:
        Max 24hr: 117 mm Gobre
    """

    patterns = [
        r"Max\s*24\s*hr\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z .'-]+)",
        r"Max\s*24hr\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z .'-]+)",
        r"Max\s*24\s*hour\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*mm\s*([A-Za-z .'-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            amount = to_number(match.group(1))
            station = clean_text(match.group(2))

            return {
                "value_mm": format_number(amount),
                "station": station,
                "source": "DHM rainfall monitoring",
            }

    print("WARNING: Could not find Max 24hr rainfall.")

    return {
        "value_mm": None,
        "station": None,
        "source": "DHM rainfall monitoring",
    }


# ============================================================
# PARSE RIVER LEVELS
# ============================================================

def extract_river_levels(text):
    """
    Extract the target river readings from the DHM homepage.

    DHM currently exposes lines similar to:

    Karnali at Chisapani WL: 7.2 m WR: 10.0 m DL: 10.8 m
    """

    results = {}

    for basin, config in TARGET_RIVERS.items():

        station = config["station"]

        # Try the most common DHM format.
        pattern = (
            rf"{re.escape(basin)}"
            rf"(?:\s+River)?"
            rf"\s+at\s+"
            rf"{re.escape(station)}"
            rf"\s+WL\s*:\s*"
            rf"([0-9]+(?:\.[0-9]+)?)"
            rf"\s*m"
            rf"\s*WR\s*:\s*"
            rf"([0-9]+(?:\.[0-9]+)?)"
            rf"\s*m"
            rf"\s*DL\s*:\s*"
            rf"([0-9]+(?:\.[0-9]+)?)"
            rf"\s*m"
        )

        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            print(
                f"WARNING: Could not find "
                f"{basin} at {station}."
            )

            results[basin] = {
                "basin": basin,
                "station": station,
                "water_level_m": None,
                "warning_level_m": config["warning"],
                "danger_level_m": config["danger"],
                "status": "UNKNOWN",
                "source": "DHM River Watch",
            }

            continue

        water_level = to_number(match.group(1))
        warning_level = to_number(match.group(2))
        danger_level = to_number(match.group(3))

        status = get_status(
            water_level,
            warning_level,
            danger_level,
        )

        results[basin] = {
            "basin": basin,
            "station": station,
            "water_level_m": format_number(water_level),
            "warning_level_m": format_number(warning_level),
            "danger_level_m": format_number(danger_level),
            "status": status,
            "source": "DHM River Watch",
        }

        print(
            f"{basin} at {station}: "
            f"{water_level} m "
            f"(Warning {warning_level} m / "
            f"Danger {danger_level} m)"
        )

    return results


# ============================================================
# DETERMINE DASHBOARD WARNING
# ============================================================

def calculate_overall_warning(rivers):
    """
    Overall dashboard warning:

    DANGER -> if any river is above danger
    WATCH  -> if any river is above warning
    NORMAL -> if all known readings are below warning
    UNKNOWN -> if no readings are available
    """

    statuses = [
        item["status"]
        for item in rivers.values()
        if item.get("status")
    ]

    if "DANGER" in statuses:
        return "DANGER"

    if "WATCH" in statuses:
        return "WATCH"

    if "NORMAL" in statuses:
        return "NORMAL"

    return "UNKNOWN"


# ============================================================
# FIND HIGHEST RIVER LEVEL
# ============================================================

def find_max_river(rivers):
    valid = [
        item
        for item in rivers.values()
        if item.get("water_level_m") is not None
    ]

    if not valid:
        return {
            "value_m": None,
            "basin": None,
            "station": None,
        }

    highest = max(
        valid,
        key=lambda item: item["water_level_m"],
    )

    return {
        "value_m": highest["water_level_m"],
        "basin": highest["basin"],
        "station": highest["station"],
    }


# ============================================================
# BUILD DATA.JSON
# ============================================================

def build_data(rainfall, rivers):
    now = datetime.now(timezone.utc)

    overall_warning = calculate_overall_warning(rivers)

    max_river = find_max_river(rivers)

    data = {
        "updated_at": now.isoformat(),
        "updated_at_npt": now.astimezone().isoformat(),

        "status": "LIVE",

        "sources": {
            "rainfall": "DHM",
            "river": "DHM",
            "casualties": "NDRRMA / Nepal Police",
            "damage": "NDRRMA / Nepal Police",
        },

        "rainfall": {
            "max_24h_mm": rainfall["value_mm"],
            "station": rainfall["station"],
            "source": rainfall["source"],
        },

        "river": {
            "max_level_m": max_river["value_m"],
            "basin": max_river["basin"],
            "station": max_river["station"],
            "overall_warning": overall_warning,
        },

        "rivers": rivers,

        # ----------------------------------------------------
        # These are intentionally NOT invented.
        # They remain null until we have a trusted live source.
        # ----------------------------------------------------

        "impact": {
            "confirmed_deaths": None,
            "missing_persons": None,
            "injured_persons": None,
            "source": "NDRRMA / Nepal Police",
        },

        "damage": {
            "homes_damaged": None,
            "bridges_damaged": None,
            "source": "NDRRMA / Nepal Police",
        },
    }

    return data


# ============================================================
# VALIDATE DATA
# ============================================================

def validate_data(data):
    if not isinstance(data, dict):
        raise RuntimeError("Generated data is not an object.")

    if "updated_at" not in data:
        raise RuntimeError("Missing updated_at.")

    if "rainfall" not in data:
        raise RuntimeError("Missing rainfall section.")

    if "river" not in data:
        raise RuntimeError("Missing river section.")

    if "rivers" not in data:
        raise RuntimeError("Missing rivers section.")

    if not data["rivers"]:
        raise RuntimeError("No river data was collected.")

    valid_rivers = [
        river
        for river in data["rivers"].values()
        if river.get("water_level_m") is not None
    ]

    if not valid_rivers:
        raise RuntimeError(
            "DHM returned no valid target river readings."
        )

    return True


# ============================================================
# SAFE WRITE
# ============================================================

def write_data(data):
    """
    Write data.json only after validation succeeds.
    """

    validate_data(data)

    temporary_file = OUTPUT_FILE.with_suffix(".tmp")

    with open(
        temporary_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    temporary_file.replace(OUTPUT_FILE)

    print()
    print(f"Successfully wrote: {OUTPUT_FILE}")
    print()


# ============================================================
# MAIN
# ============================================================

def main():

    print("========================================")
    print("NEPAL FLOOD 2026 DATA COLLECTION")
    print("========================================")
    print()

    print("Starting DHM data collection...")
    print()

    html = fetch_dhm_homepage()

    soup = BeautifulSoup(html, "html.parser")

    # Convert the page into clean text.
    text = clean_text(soup.get_text(" ", strip=True))

    print()
    print("Parsing rainfall...")
    rainfall = extract_max_rainfall(text)

    print()
    print("Parsing river levels...")
    rivers = extract_river_levels(text)

    print()
    print("Building dashboard data...")

    data = build_data(
        rainfall,
        rivers,
    )

    print()
    print("Validating data...")

    validate_data(data)

    print()
    print("Writing data.json...")

    write_data(data)

    print("========================================")
    print("UPDATE SUCCESSFUL")
    print("========================================")
    print()

    print(
        f"Max 24h rainfall: "
        f"{data['rainfall']['max_24h_mm']} mm "
        f"{data['rainfall']['station'] or ''}"
    )

    print(
        f"Highest river: "
        f"{data['river']['max_level_m']} m "
        f"{data['river']['station'] or ''}"
    )

    print(
        f"Overall warning: "
        f"{data['river']['overall_warning']}"
    )


if __name__ == "__main__":
    main() 
