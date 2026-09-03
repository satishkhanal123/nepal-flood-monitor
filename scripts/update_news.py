#!/usr/bin/env python3

"""
Trishuli Pulse · Kathmandu Post RSS updater

Purpose:
    Fetch flood/disaster-related stories from The Kathmandu Post RSS feed
    and safely update data/news.json.

Design goals:
    - Standard library only
    - No external Python packages
    - Never destroy a known-good news.json on failure
    - Only accept Kathmandu Post URLs
    - Filter out unrelated RSS stories
    - Deduplicate articles
    - Produce frontend-compatible JSON
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

RSS_URL = "https://kathmandupost.com/rss"
OUTPUT_FILE = ROOT / "data" / "news.json"

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; TrishuliPulse/1.0; +https://github.com/)"
)

MAX_ITEMS = 20

FETCH_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Flood relevance
# ---------------------------------------------------------------------------

RELEVANCE_TERMS = [
    "flood",
    "floods",
    "flooding",
    "flash flood",
    "bhote koshi",
    "bhotekoshi",
    "trishuli",
    "rasuwa",
    "nuwakot",
    "dhading",
    "chitwan",
    "nawalparasi",
    "narayani",
    "langtang",
    "lhende",
    "glacier",
    "glacial",
    "landslide",
    "disaster",
    "rescue",
    "relief",
    "missing",
    "unaccounted",
    "stranded",
    "hydropower",
    "emergency",
    "ndr rma",
    "ndrrma",
    "telecom",
    "communications",
    "early warning",
    "warning system",
    "evacuation",
    "reconstruction",
]


# ---------------------------------------------------------------------------
# Tag classification
# ---------------------------------------------------------------------------

WARNING_TERMS = [
    "warning",
    "alert",
    "early warning",
    "forecast",
    "evacuation",
    "glacier",
    "glacial",
]

ACCESS_TERMS = [
    "road",
    "roads",
    "highway",
    "bridge",
    "bridges",
    "cut off",
    "cut-off",
    "stranded",
    "access",
    "telecom",
    "tower",
    "communications",
    "airport",
    "helicopter",
    "supply",
    "supplies",
    "route",
]

PEOPLE_TERMS = [
    "student",
    "students",
    "women",
    "girls",
    "girl",
    "survivor",
    "survivors",
    "family",
    "families",
    "victim",
    "victims",
    "tourist",
    "tourists",
    "pilgrim",
    "pilgrims",
    "community",
    "mental health",
    "psychological",
]

OPS_TERMS = [
    "rescue",
    "rescued",
    "relief",
    "response",
    "security",
    "army",
    "police",
    "government",
    "officials",
    "reconstruction",
    "finance",
    "fund",
    "funds",
    "aid",
    "hydropower",
    "ndr rma",
    "ndrrma",
    "emergency",
]


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

def local_name(tag: str) -> str:
    """Return an XML tag without namespace information."""
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]

    if ":" in tag:
        return tag.rsplit(":", 1)[-1]

    return tag


def child_text(element: ET.Element, names: list[str]) -> str:
    """Find the first matching child element and return its text."""

    wanted = {name.lower() for name in names}

    for child in element.iter():
        if child is element:
            continue

        if local_name(child.tag).lower() in wanted:
            text = "".join(child.itertext()).strip()

            if text:
                return text

    return ""


def child_link(element: ET.Element) -> str:
    """
    Extract a link from RSS or Atom.

    Supports:
        <link>https://...</link>
        <link href="https://..." />
    """

    for child in element.iter():
        if child is element:
            continue

        if local_name(child.tag).lower() != "link":
            continue

        href = child.attrib.get("href", "").strip()

        if href:
            return href

        text = "".join(child.itertext()).strip()

        if text:
            return text

    return ""


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def strip_html(value: str) -> str:
    """Remove HTML markup and decode entities."""

    if not value:
        return ""

    value = html.unescape(value)

    value = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    value = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )

    value = re.sub(r"<[^>]+>", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_title(value: str) -> str:
    """Clean an RSS title."""

    value = strip_html(value)

    # Remove common author suffixes sometimes included by RSS.
    value = re.sub(
        r"\s+by\s+[^|]+$",
        "",
        value,
        flags=re.IGNORECASE,
    )

    return value.strip()


def make_blurb(value: str, maximum: int = 220) -> str:
    """Create a short description without inventing information."""

    value = strip_html(value)

    if not value:
        return ""

    if len(value) <= maximum:
        return value

    shortened = value[:maximum].rsplit(" ", 1)[0].strip()

    return shortened + "…"


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def format_date(value: str) -> str:
    """
    Convert RSS publication date to:
        3 Sep 2026
    """

    if not value:
        return ""

    try:
        dt = parsedate_to_datetime(value)

        # Avoid platform-specific %-d formatting.
        return f"{dt.day} {dt.strftime('%b %Y')}"

    except (TypeError, ValueError, OverflowError):
        return ""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_kathmandu_post_url(url: str) -> bool:
    """Accept only HTTPS Kathmandu Post article URLs."""

    try:
        parsed = urlparse(url)

        if parsed.scheme != "https":
            return False

        hostname = (parsed.hostname or "").lower()

        if hostname not in {
            "kathmandupost.com",
            "www.kathmandupost.com",
        }:
            return False

        if not parsed.path or parsed.path == "/":
            return False

        return True

    except ValueError:
        return False


def is_relevant(title: str, description: str) -> bool:
    """Return True if the article appears related to the flood response."""

    text = f"{title} {description}".lower()

    return any(term in text for term in RELEVANCE_TERMS)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_tag(title: str, description: str) -> str:
    """Classify a story into one of the dashboard's existing tabs."""

    text = f"{title} {description}".lower()

    if any(term in text for term in WARNING_TERMS):
        return "warning"

    if any(term in text for term in ACCESS_TERMS):
        return "access"

    if any(term in text for term in PEOPLE_TERMS):
        return "people"

    if any(term in text for term in OPS_TERMS):
        return "ops"

    return "sitrep"


# ---------------------------------------------------------------------------
# RSS fetching
# ---------------------------------------------------------------------------

def fetch_rss() -> bytes:
    """Download Kathmandu Post RSS feed."""

    request = Request(
        RSS_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "application/rss+xml, "
                "application/atom+xml, "
                "application/xml, "
                "text/xml, "
                "*/*"
            ),
        },
    )

    try:
        with urlopen(request, timeout=FETCH_TIMEOUT) as response:
            data = response.read()

    except HTTPError as exc:
        raise RuntimeError(
            f"Kathmandu Post RSS returned HTTP {exc.code}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Could not reach Kathmandu Post RSS: {exc.reason}"
        ) from exc

    except TimeoutError as exc:
        raise RuntimeError(
            "Kathmandu Post RSS request timed out"
        ) from exc

    if not data:
        raise RuntimeError("Kathmandu Post RSS returned an empty response")

    return data


# ---------------------------------------------------------------------------
# RSS parsing
# ---------------------------------------------------------------------------

def parse_feed(data: bytes) -> list[dict]:
    """Parse RSS or Atom feed into normalized article records."""

    try:
        root = ET.fromstring(data)

    except ET.ParseError as exc:
        raise RuntimeError(
            f"Could not parse Kathmandu Post RSS XML: {exc}"
        ) from exc

    records = []

    # RSS normally uses <item>.
    # Atom normally uses <entry>.
    candidates = []

    for element in root.iter():
        name = local_name(element.tag).lower()

        if name in {"item", "entry"}:
            candidates.append(element)

    for item in candidates:
        title = clean_title(
            child_text(item, ["title"])
        )

        url = child_link(item)

        description = child_text(
            item,
            [
                "description",
                "summary",
                "content",
                "encoded",
            ],
        )

        pub_date = child_text(
            item,
            [
                "pubDate",
                "published",
                "updated",
                "date",
            ],
        )

        if not title or not url:
            continue

        if not is_kathmandu_post_url(url):
            continue

        if not is_relevant(title, description):
            continue

        records.append(
            {
                "tag": classify_tag(title, description),
                "date": format_date(pub_date),
                "title": title,
                "blurb": make_blurb(description),
                "url": url,
                "_pub_date": pub_date,
            }
        )

    return records


# ---------------------------------------------------------------------------
# Deduplication and sorting
# ---------------------------------------------------------------------------

def deduplicate(records: list[dict]) -> list[dict]:
    """Remove duplicate article URLs."""

    seen = set()
    result = []

    for record in records:
        url = record["url"].rstrip("/")

        if url in seen:
            continue

        seen.add(url)
        result.append(record)

    return result


def sort_records(records: list[dict]) -> list[dict]:
    """Sort newest articles first when RSS dates are available."""

    def sort_key(record: dict):
        raw = record.get("_pub_date", "")

        if not raw:
            return datetime.min.replace(tzinfo=timezone.utc)

        try:
            return parsedate_to_datetime(raw)

        except (TypeError, ValueError, OverflowError):
            return datetime.min.replace(tzinfo=timezone.utc)

    return sorted(
        records,
        key=sort_key,
        reverse=True,
    )


# ---------------------------------------------------------------------------
# JSON validation
# ---------------------------------------------------------------------------

def validate_records(records: list[dict]) -> None:
    """
    Ensure the generated data is safe for the frontend.

    We intentionally require at least one relevant story.
    This prevents an unexpected RSS/feed change from replacing
    the existing known-good snapshot with an empty feed.
    """

    if not records:
        raise RuntimeError(
            "No relevant Kathmandu Post flood/disaster stories were found"
        )

    for record in records:
        required = {
            "tag",
            "date",
            "title",
            "blurb",
            "url",
        }

        if not required.issubset(record.keys()):
            raise RuntimeError(
                "Generated article is missing required fields"
            )

        if not record["title"]:
            raise RuntimeError(
                "Generated article has an empty title"
            )

        if not is_kathmandu_post_url(record["url"]):
            raise RuntimeError(
                f"Unsafe article URL rejected: {record['url']}"
            )


# ---------------------------------------------------------------------------
# Safe file writing
# ---------------------------------------------------------------------------

def write_json_atomically(payload: dict) -> None:
    """
    Write news.json atomically.

    The existing file remains untouched if anything goes wrong.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_path = tempfile.mkstemp(
        prefix="news-",
        suffix=".json",
        dir=str(OUTPUT_FILE.parent),
        text=True,
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

            handle.write("\n")

            handle.flush()

            os.fsync(handle.fileno())

        os.replace(
            temporary_path,
            OUTPUT_FILE,
        )

    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass

        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("Trishuli Pulse · Kathmandu Post RSS updater")
    print(f"RSS:    {RSS_URL}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    try:
        print("1. Fetching Kathmandu Post RSS...")
        rss_data = fetch_rss()

        print(
            f"   Downloaded {len(rss_data):,} bytes."
        )

        print("2. Parsing RSS feed...")
        records = parse_feed(rss_data)

        print(
            f"   Found {len(records)} relevant flood/disaster stories."
        )

        print("3. Deduplicating...")
        records = deduplicate(records)

        print(
            f"   {len(records)} unique stories remain."
        )

        print("4. Sorting...")
        records = sort_records(records)

        records = records[:MAX_ITEMS]

        print(
            f"   Keeping newest {len(records)} stories."
        )

        print("5. Validating...")
        validate_records(records)

        # Remove internal fields before writing.
        clean_records = []

        for record in records:
            clean_records.append(
                {
                    "tag": record["tag"],
                    "date": record["date"],
                    "title": record["title"],
                    "blurb": record["blurb"],
                    "url": record["url"],
                }
            )

        payload = {
            "source": "The Kathmandu Post",
            "source_url": RSS_URL,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "items": clean_records,
        }

        print("6. Writing news.json safely...")
        write_json_atomically(payload)

        print()
        print("SUCCESS")
        print(
            f"Updated: {OUTPUT_FILE}"
        )
        print(
            f"Articles: {len(clean_records)}"
        )

        return 0

    except Exception as exc:
        print()
        print("UPDATE FAILED")
        print(str(exc))
        print()
        print(
            "The existing data/news.json was left unchanged."
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
