#!/usr/bin/env python3

"""
Trishuli Pulse · Kathmandu Post RSS updater

Fetches flood/disaster-related stories from The Kathmandu Post RSS feed
and safely updates data/news.json.

Safety rules:
    - Only Kathmandu Post HTTPS URLs are accepted.
    - Unrelated RSS stories are filtered out.
    - Duplicate stories are removed.
    - Malformed XML characters/entities are repaired before parsing.
    - The existing news.json is never replaced if the update fails.
    - The generated JSON is validated before being written.
    - Standard Python library only.
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


# ============================================================
# Configuration
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

RSS_URL = "https://kathmandupost.com/rss"
OUTPUT_FILE = ROOT / "data" / "news.json"

USER_AGENT = (
    "Mozilla/5.0 "
    "(compatible; TrishuliPulse/1.0)"
)

FETCH_TIMEOUT = 30

MAX_ITEMS = 20


# ============================================================
# Flood / disaster relevance
# ============================================================

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
    "ndrrma",
    "telecom",
    "communications",
    "early warning",
    "warning system",
    "evacuation",
    "reconstruction",
]


# ============================================================
# Story classification
# ============================================================

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
    "ndrrma",
    "emergency",
]


# ============================================================
# XML helpers
# ============================================================

def local_name(tag: str) -> str:
    """
    Return an XML tag name without namespace information.
    """

    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]

    if ":" in tag:
        tag = tag.rsplit(":", 1)[-1]

    return tag


def child_text(
    element: ET.Element,
    names: list[str],
) -> str:
    """
    Return text from the first matching child element.
    """

    wanted = {
        name.lower()
        for name in names
    }

    for child in element.iter():

        if child is element:
            continue

        if (
            local_name(child.tag).lower()
            in wanted
        ):
            text = "".join(
                child.itertext()
            ).strip()

            if text:
                return text

    return ""


def child_link(
    element: ET.Element,
) -> str:
    """
    Extract a URL from RSS or Atom.

    Supports:

        <link>https://...</link>

    and:

        <link href="https://..." />
    """

    for child in element.iter():

        if child is element:
            continue

        if (
            local_name(child.tag).lower()
            != "link"
        ):
            continue

        href = child.attrib.get(
            "href",
            "",
        ).strip()

        if href:
            return html.unescape(
                href
            )

        text = "".join(
            child.itertext()
        ).strip()

        if text:
            return html.unescape(
                text
            )

    return ""


# ============================================================
# XML repair
# ============================================================

def repair_xml_entities(
    data: bytes,
) -> bytes:
    """
    Repair common malformed XML problems before parsing.

    Kathmandu Post's RSS response can contain malformed XML content,
    including bare ampersands. XML parsers reject these characters.

    This function:

        1. Decodes the feed safely.
        2. Removes XML 1.0-invalid control characters.
        3. Converts bare '&' characters to '&amp;'.
        4. Preserves valid XML entities.
    """

    text = data.decode(
        "utf-8",
        errors="replace",
    )

    # --------------------------------------------------------
    # Remove characters forbidden by XML 1.0.
    # --------------------------------------------------------

    def valid_xml_character(
        char: str,
    ) -> bool:

        code = ord(char)

        return (
            code == 0x9
            or code == 0xA
            or code == 0xD
            or 0x20 <= code <= 0xD7FF
            or 0xE000 <= code <= 0xFFFD
            or 0x10000 <= code <= 0x10FFFF
        )

    text = "".join(
        char
        for char in text
        if valid_xml_character(char)
    )

    # --------------------------------------------------------
    # Repair bare ampersands.
    #
    # Keep valid XML entities such as:
    #
    #   &amp;
    #   &lt;
    #   &gt;
    #   &quot;
    #   &apos;
    #   &#123;
    #   &#x1F600;
    #
    # --------------------------------------------------------

    text = re.sub(
        r"&(?!(?:amp|lt|gt|quot|apos);|#\d+;|#x[0-9A-Fa-f]+;)",
        "&amp;",
        text,
    )

    return text.encode(
        "utf-8"
    )


# ============================================================
# Text helpers
# ============================================================

def strip_html(
    value: str,
) -> str:
    """
    Remove HTML markup and decode HTML entities.
    """

    if not value:
        return ""

    value = html.unescape(
        value
    )

    value = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    value = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        value,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def clean_title(
    value: str,
) -> str:
    """
    Clean an RSS article title.
    """

    return strip_html(
        value
    ).strip()


def make_blurb(
    value: str,
    maximum: int = 220,
) -> str:
    """
    Create a short description from the RSS feed.

    No information is invented.
    """

    value = strip_html(
        value
    )

    if not value:
        return ""

    if len(value) <= maximum:
        return value

    shortened = (
        value[:maximum]
        .rsplit(" ", 1)[0]
        .strip()
    )

    return shortened + "…"


# ============================================================
# Date helpers
# ============================================================

def format_date(
    value: str,
) -> str:
    """
    Convert an RSS date into:

        3 Sep 2026
    """

    if not value:
        return ""

    try:

        dt = parsedate_to_datetime(
            value
        )

        return (
            f"{dt.day} "
            f"{dt.strftime('%b %Y')}"
        )

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return ""


def date_sort_value(
    value: str,
) -> datetime:
    """
    Convert RSS date into a sortable datetime.
    """

    if not value:
        return datetime.min.replace(
            tzinfo=timezone.utc
        )

    try:

        dt = parsedate_to_datetime(
            value
        )

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return datetime.min.replace(
            tzinfo=timezone.utc
        )


# ============================================================
# URL validation
# ============================================================

def is_kathmandu_post_url(
    url: str,
) -> bool:
    """
    Accept only HTTPS Kathmandu Post URLs.
    """

    try:

        parsed = urlparse(
            url
        )

        if parsed.scheme != "https":
            return False

        hostname = (
            parsed.hostname or ""
        ).lower()

        if hostname not in {
            "kathmandupost.com",
            "www.kathmandupost.com",
        }:
            return False

        if not parsed.path:
            return False

        if parsed.path == "/":
            return False

        return True

    except ValueError:
        return False


# ============================================================
# Relevance
# ============================================================

def is_relevant(
    title: str,
    description: str,
) -> bool:
    """
    Determine whether an article is related to the
    Nepal flood/disaster situation.
    """

    text = (
        f"{title} "
        f"{description}"
    ).lower()

    return any(
        term in text
        for term in RELEVANCE_TERMS
    )


# ============================================================
# Classification
# ============================================================

def classify_tag(
    title: str,
    description: str,
) -> str:
    """
    Assign an existing Trishuli Pulse news category.
    """

    text = (
        f"{title} "
        f"{description}"
    ).lower()

    if any(
        term in text
        for term in WARNING_TERMS
    ):
        return "warning"

    if any(
        term in text
        for term in ACCESS_TERMS
    ):
        return "access"

    if any(
        term in text
        for term in PEOPLE_TERMS
    ):
        return "people"

    if any(
        term in text
        for term in OPS_TERMS
    ):
        return "ops"

    return "sitrep"


# ============================================================
# Fetch RSS
# ============================================================

def fetch_rss() -> bytes:
    """
    Download the Kathmandu Post RSS feed.
    """

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

        with urlopen(
            request,
            timeout=FETCH_TIMEOUT,
        ) as response:

            data = response.read()

    except HTTPError as exc:

        raise RuntimeError(
            "Kathmandu Post RSS returned "
            f"HTTP {exc.code}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            "Could not reach Kathmandu Post RSS: "
            f"{exc.reason}"
        ) from exc

    except TimeoutError as exc:

        raise RuntimeError(
            "Kathmandu Post RSS request timed out"
        ) from exc

    if not data:

        raise RuntimeError(
            "Kathmandu Post RSS returned "
            "an empty response"
        )

    return data


# ============================================================
# Parse RSS
# ============================================================

def parse_feed(
    data: bytes,
) -> list[dict]:
    """
    Parse the Kathmandu Post RSS/Atom feed.
    """

    cleaned_data = repair_xml_entities(
        data
    )

    try:

        root = ET.fromstring(
            cleaned_data
        )

    except ET.ParseError as exc:

        raise RuntimeError(
            "Kathmandu Post RSS could not "
            "be parsed after XML repair: "
            f"{exc}"
        ) from exc

    records = []

    for element in root.iter():

        element_name = (
            local_name(
                element.tag
            ).lower()
        )

        if element_name not in {
            "item",
            "entry",
        }:
            continue

        title = clean_title(
            child_text(
                element,
                ["title"],
            )
        )

        url = child_link(
            element
        )

        description = child_text(
            element,
            [
                "description",
                "summary",
                "content",
                "encoded",
            ],
        )

        pub_date = child_text(
            element,
            [
                "pubDate",
                "published",
                "updated",
                "date",
            ],
        )

        # ----------------------------------------------------
        # Basic validation
        # ----------------------------------------------------

        if not title:
            continue

        if not url:
            continue

        if not is_kathmandu_post_url(
            url
        ):
            continue

        # ----------------------------------------------------
        # Flood relevance filter
        # ----------------------------------------------------

        if not is_relevant(
            title,
            description,
        ):
            continue

        records.append(
            {
                "tag": classify_tag(
                    title,
                    description,
                ),
                "date": format_date(
                    pub_date
                ),
                "title": title,
                "blurb": make_blurb(
                    description
                ),
                "url": url,
                "_pub_date": pub_date,
            }
        )

    return records


# ============================================================
# Deduplication
# ============================================================

def deduplicate(
    records: list[dict],
) -> list[dict]:
    """
    Remove duplicate article URLs.
    """

    seen = set()
    result = []

    for record in records:

        url = (
            record["url"]
            .strip()
            .rstrip("/")
        )

        if url in seen:
            continue

        seen.add(url)

        result.append(
            record
        )

    return result


# ============================================================
# Validation
# ============================================================

def validate_records(
    records: list[dict],
) -> None:
    """
    Validate all generated article records.

    At least one relevant article must exist.
    """

    if not records:

        raise RuntimeError(
            "No relevant Kathmandu Post "
            "flood/disaster stories were found"
        )

    required_fields = {
        "tag",
        "date",
        "title",
        "blurb",
        "url",
    }

    allowed_tags = {
        "sitrep",
        "access",
        "warning",
        "people",
        "ops",
    }

    for record in records:

        if not required_fields.issubset(
            record.keys()
        ):
            raise RuntimeError(
                "An article is missing "
                "required fields"
            )

        if not record["title"].strip():

            raise RuntimeError(
                "An article has an empty title"
            )

        if record["tag"] not in allowed_tags:

            raise RuntimeError(
                "Invalid article tag: "
                f"{record['tag']}"
            )

        if not is_kathmandu_post_url(
            record["url"]
        ):

            raise RuntimeError(
                "Unsafe URL rejected: "
                f"{record['url']}"
            )


# ============================================================
# Atomic JSON write
# ============================================================

def write_json_atomically(
    payload: dict,
) -> None:
    """
    Safely replace news.json.

    If writing fails, the original file remains intact.
    """

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_descriptor, temporary_path = (
        tempfile.mkstemp(
            prefix="news-",
            suffix=".json",
            dir=str(
                OUTPUT_FILE.parent
            ),
            text=True,
        )
    )

    try:

        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        ) as handle:

            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                indent=2,
            )

            handle.write(
                "\n"
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary_path,
            OUTPUT_FILE,
        )

    except Exception:

        try:
            os.unlink(
                temporary_path
            )
        except OSError:
            pass

        raise


# ============================================================
# Main
# ============================================================

def main() -> int:

    print(
        "Trishuli Pulse · "
        "Kathmandu Post RSS updater"
    )

    print(
        f"RSS:    {RSS_URL}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()

    try:

        # ----------------------------------------------------
        # 1. Fetch
        # ----------------------------------------------------

        print(
            "1. Fetching Kathmandu Post RSS..."
        )

        rss_data = fetch_rss()

        print(
            f"   Downloaded "
            f"{len(rss_data):,} bytes."
        )

        # ----------------------------------------------------
        # 2. Clean + parse
        # ----------------------------------------------------

        print(
            "2. Cleaning and parsing RSS feed..."
        )

        records = parse_feed(
            rss_data
        )

        print(
            f"   Found {len(records)} "
            f"relevant stories."
        )

        # ----------------------------------------------------
        # 3. Deduplicate
        # ----------------------------------------------------

        print(
            "3. Removing duplicates..."
        )

        records = deduplicate(
            records
        )

        print(
            f"   {len(records)} "
            f"unique stories remain."
        )

        # ----------------------------------------------------
        # 4. Sort newest first
        # ----------------------------------------------------

        print(
            "4. Sorting newest first..."
        )

        records.sort(
            key=lambda record:
                date_sort_value(
                    record.get(
                        "_pub_date",
                        "",
                    )
                ),
            reverse=True,
        )

        records = records[
            :MAX_ITEMS
        ]

        print(
            f"   Keeping {len(records)} stories."
        )

        # ----------------------------------------------------
        # 5. Validate
        # ----------------------------------------------------

        print(
            "5. Validating generated data..."
        )

        validate_records(
            records
        )

        # ----------------------------------------------------
        # 6. Remove internal fields
        # ----------------------------------------------------

        clean_items = []

        for record in records:

            clean_items.append(
                {
                    "tag": record["tag"],
                    "date": record["date"],
                    "title": record["title"],
                    "blurb": record["blurb"],
                    "url": record["url"],
                }
            )

        # ----------------------------------------------------
        # 7. Build final JSON
        # ----------------------------------------------------

        payload = {
            "source": "The Kathmandu Post",
            "source_url": RSS_URL,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "items": clean_items,
        }

        # ----------------------------------------------------
        # 8. Write safely
        # ----------------------------------------------------

        print(
            "6. Writing data/news.json..."
        )

        write_json_atomically(
            payload
        )

        print()

        print(
            "========================================"
        )

        print(
            "SUCCESS"
        )

        print(
            "========================================"
        )

        print(
            f"Articles updated: "
            f"{len(clean_items)}"
        )

        print(
            f"Output: {OUTPUT_FILE}"
        )

        return 0

    except Exception as exc:

        print()

        print(
            "========================================"
        )

        print(
            "UPDATE FAILED"
        )

        print(
            "========================================"
        )

        print(
            str(exc)
        )

        print()

        print(
            "The existing data/news.json "
            "was left unchanged."
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())