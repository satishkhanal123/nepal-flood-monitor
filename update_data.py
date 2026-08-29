import json
import re
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright


# ============================================================
# CONFIG
# ============================================================

DHM_RIVER_URL = "https://dhm.gov.np/hydrology/river-watch"
DHM_RAIN_URL = "https://dhm.gov.np/hydrology/rainfall-watch-map"

OUTPUT_FILE = Path(__file__).with_name("data.json")

TARGET_RIVERS = {
    "Karnali": "Chisapani",
    "Narayani": "Devghat",
    "Kankai": "Mainachuli",
    "Babai": "Chepang",
    "Mahakali": "Parigaon",
}


# ============================================================
# HELPERS
# ============================================================

def clean(text):
    """Clean extra spaces and line breaks."""
    return re.sub(r"\s+", " ", (text or "")).strip()


def to_number(text):
    """Extract the first number from a string."""
    if not text:
        return None

    text = text.replace(",", "")

    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


# ============================================================
# RIVER DATA
# ============================================================

def get_river_data(page):
    """
    Read current river observations from DHM River Watch.
    """

    page.wait_for_timeout(5000)

    rivers = []

    rows = page.locator("table tbody tr").all()

    for row in rows:

        cells = [
            clean(cell.inner_text())
            for cell in row.locator("td").all()
        ]

        if len(cells) < 7:
            continue

        try:
            station = cells[2]

            matched_river = None
            matched_station = None

            for river_name, station_name in TARGET_RIVERS.items():

                if station_name.lower() in station.lower():

                    matched_river = river_name
                    matched_station = station_name

                    break

            if not matched_river:
                continue

            current = to_number(cells[4])
            warning = to_number(cells[5])
            danger = to_number(cells[6])

            trend = ""
            status = ""

            if len(cells) > 7:
                trend = cells[7]

            if len(cells) > 8:
                status = cells[8]

            rivers.append(
                {
                    "name": matched_river,
                    "station": matched_station,
                    "value": current,
                    "warning": warning,
                    "danger": danger,
                    "trend": trend,
                    "status": status,
                }
            )

        except Exception as error:

            print(
                f"Could not parse river row: {error}"
            )

    return rivers


# ============================================================
# RAINFALL DATA
# ============================================================

def get_max_rainfall(page):
    """
    Find the highest 24-hour rainfall value
    currently shown by DHM.
    """

    page.wait_for_timeout(5000)

    best = None

    rows = page.locator("table tbody tr").all()

    for row in rows:

        cells = [
            clean(cell.inner_text())
            for cell in row.locator("td").all()
        ]

        if len(cells) < 5:
            continue

        try:

            station = cells[2]

            # DHM rainfall tables contain several
            # rainfall periods. The final numeric field
            # is treated as the 24-hour value.

            candidates = []

            for cell in cells[4:]:

                value = to_number(cell)

                if value is not None:
                    candidates.append(value)

            if not candidates:
                continue

            rainfall_24h = candidates[-1]

            if (
                best is None
                or rainfall_24h > best["value"]
            ):

                best = {
                    "value": rainfall_24h,
                    "station": station,
                }

        except Exception as error:

            print(
                f"Could not parse rainfall row: {error}"
            )

    return best


# ============================================================
# MAIN
# ============================================================

def main():

    fetched_at = (
        datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds")
    )

    print("Starting DHM data collection...")
    print(f"Timestamp: {fetched_at}")

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        # ----------------------------------------------------
        # RIVER WATCH
        # ----------------------------------------------------

        river_page = browser.new_page()

        print("Opening DHM River Watch...")

        river_page.goto(
            DHM_RIVER_URL,
            wait_until="domcontentloaded",
            timeout=90000,
        )

        rivers = get_river_data(river_page)

        # ----------------------------------------------------
        # RAINFALL WATCH
        # ----------------------------------------------------

        rainfall_page = browser.new_page()

        print("Opening DHM Rainfall Watch...")

        rainfall_page.goto(
            DHM_RAIN_URL,
            wait_until="domcontentloaded",
            timeout=90000,
        )

        rainfall = get_max_rainfall(
            rainfall_page
        )

        browser.close()

    # ========================================================
    # VALIDATION
    # ========================================================

    if not rivers:

        raise RuntimeError(
            "DHM River Watch returned no matching "
            "target stations."
        )

    if rainfall is None:

        raise RuntimeError(
            "DHM Rainfall Watch returned no "
            "24-hour rainfall data."
        )

    print()
    print("DHM data successfully collected.")
    print(f"River stations: {len(rivers)}")
    print(
        f"Maximum rainfall: "
        f"{rainfall['value']} mm "
        f"at {rainfall['station']}"
    )

    # ========================================================
    # DATA.JSON
    # ========================================================

    data = {

        "updated": fetched_at,

        "rain": {
            "value": rainfall["value"],
            "station": rainfall["station"],
        },

        "rivers": rivers,

        # These remain empty until we verify
        # official live sources for them.

        "deaths": None,
        "missing": None,
        "injured": None,

        "homes": None,
        "bridges": None,

        "teams": None,
        "rescued": None,
        "vehicles": None,
        "relief": None,

        "affectedDistricts": None,

        "weather": [],

        "ticker": (
            "Live DHM rainfall and river "
            "observations successfully updated."
        ),

        "sources": {

            "dhm": {

                "status": "live",

                "updated": fetched_at,

                "riverWatch": DHM_RIVER_URL,

                "rainfallWatch": DHM_RAIN_URL,
            }
        },
    }

    # ========================================================
    # SAFE WRITE
    # ========================================================

    temporary_file = OUTPUT_FILE.with_suffix(
        ".tmp"
    )

    temporary_file.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Only replace data.json after successful
    # collection and JSON creation.

    temporary_file.replace(
        OUTPUT_FILE
    )

    print()
    print(
        f"Updated: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
