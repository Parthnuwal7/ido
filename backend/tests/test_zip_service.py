"""Tests for zip_service discovery.

The admin scanner previously hard-coded a JSON-only lookup, so it reported every
HTML export as missing its history. It now shares history_locator with the wrapped
path so there is one discovery implementation.

The response contract is deliberately unchanged: the frontend maps over found_files
keys and posts them back to /extract, so the canonical key names are preserved even
when the located member is an .html file. The added `formats` map is what tells a
caller which format was actually found.
"""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.zip_service import read_zip_for_files  # noqa: E402

BASE = "Takeout/YouTube and YouTube Music"


def make_zip(names):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in names:
            z.writestr(name, "x")
    return buf.getvalue()


def test_finds_html_watch_history():
    """This is the case that previously reported 'missing'."""
    content = make_zip([f"{BASE}/history/watch-history.html"])

    result = read_zip_for_files(content)

    assert result["found_files"]["watch-history.json"] == (
        f"{BASE}/history/watch-history.html"
    )
    assert result["formats"]["watch-history.json"] == "html"
    assert "watch-history.json" not in result["missing_files"]


def test_prefers_json_when_both_present():
    content = make_zip([
        f"{BASE}/history/watch-history.html",
        f"{BASE}/history/watch-history.json",
    ])

    result = read_zip_for_files(content)

    assert result["found_files"]["watch-history.json"].endswith(".json")
    assert result["formats"]["watch-history.json"] == "json"


def test_reports_missing_files():
    content = make_zip([f"{BASE}/history/watch-history.html"])

    result = read_zip_for_files(content)

    assert set(result["missing_files"]) == {"search-history.json", "subscriptions.csv"}


def test_finds_search_history_and_subscriptions():
    content = make_zip([
        f"{BASE}/history/search-history.html",
        f"{BASE}/subscriptions/subscriptions.csv",
    ])

    result = read_zip_for_files(content)

    assert result["found_files"]["search-history.json"].endswith("search-history.html")
    assert result["found_files"]["subscriptions.csv"].endswith("subscriptions.csv")
    assert result["formats"]["subscriptions.csv"] == "csv"


def test_counts_total_files():
    content = make_zip([f"{BASE}/history/watch-history.html", f"{BASE}/a.csv"])

    assert read_zip_for_files(content)["total_files_in_zip"] == 2


def test_invalid_zip_raises_value_error():
    import pytest

    with pytest.raises(ValueError):
        read_zip_for_files(b"not a zip")


# --- the admin scan -> extract -> preprocess round trip ----------------------------

def test_html_export_survives_the_whole_admin_flow():
    """The regression: scan finds watch-history.html, files it under the canonical
    .json key, and preprocess then runs json.loads() on HTML, catches the error and
    returns []. The admin page reports 0 events while the file is sitting right there
    -- worse than the old "missing file", because it is silent."""
    import os

    from services.preprocess_service import preprocess_all_files
    from services.zip_service import extract_files_by_paths

    demo = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo_takeout.zip")
    with open(demo, "rb") as fh:
        raw = fh.read()

    scan = read_zip_for_files(raw)
    paths = {k: v for k, v in scan["found_files"].items() if v}
    files, _missing = extract_files_by_paths(raw, paths)

    result = preprocess_all_files(files, "UTC")

    assert result["stats"]["total_watch"] > 0, "HTML watch history silently produced 0 events"
    assert result["stats"]["total_search"] > 0


def test_extracted_html_is_tagged_as_html_not_json():
    """content_type must describe the bytes, not the canonical key they arrived under."""
    import os

    from services.zip_service import extract_files_by_paths

    demo = os.path.join(os.path.dirname(__file__), "..", "fixtures", "demo_takeout.zip")
    with open(demo, "rb") as fh:
        raw = fh.read()

    scan = read_zip_for_files(raw)
    paths = {k: v for k, v in scan["found_files"].items() if v}
    files, _ = extract_files_by_paths(raw, paths)

    by_name = {f["filename"]: f for f in files}
    assert by_name["watch-history.json"]["content_type"] == "html"
    assert by_name["subscriptions.csv"]["content_type"] == "csv"
