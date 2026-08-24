"""The intro card must report the year the cards actually cover.

It previously used datetime.now().year as a label while every card summarised all-time
data, so the year shown and the data shown could disagree.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.wrapped_service import generate_intro_card  # noqa: E402


def test_intro_reports_the_year_the_cards_cover():
    assert generate_intro_card({"year": 2025})["year"] == 2025


def test_intro_falls_back_to_current_year_when_unset():
    assert generate_intro_card({})["year"] == datetime.now().year


def test_intro_falls_back_when_year_is_none():
    assert generate_intro_card({"year": None})["year"] == datetime.now().year
