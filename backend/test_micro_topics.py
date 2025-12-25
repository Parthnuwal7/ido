"""
Test script for new micro topic extraction v2.
Uses the testing_json.json file.
"""

import sys
import io
import json
from pathlib import Path

# Fix Windows terminal encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.micro_topic_service import (
    extract_micro_topics_v2,
    process_events_batch,
    get_aggregated_topics,
    extract_hashtags,
    process_english_text,
    process_hinglish_text,
    process_hindi_text
)


def load_test_data():
    """Load the testing JSON file."""
    test_file = Path(__file__).parent.parent / "testing_json.json"
    if not test_file.exists():
        print(f"[ERROR] Test file not found: {test_file}")
        return None
    
    with open(test_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_hashtag_extraction():
    print("\n" + "="*60)
    print("TEST: Hashtag Extraction")
    print("="*60)
    
    test_cases = [
        "#familyguy #shorts",
        "Cabin crew layover in India #recommended #travel #cabincrew #emirates #india #kerala #kochi",
        "No hashtags here",
        "#हिंदी #test"  # Mixed
    ]
    
    for text in test_cases:
        hashtags = extract_hashtags(text)
        print(f"\nInput: {text}")
        print(f"Hashtags: {hashtags}")


def test_english_pipeline():
    print("\n" + "="*60)
    print("TEST: English Pipeline (NER + Nouns)")
    print("="*60)
    
    test_cases = [
        "this man wanted to break india | us sad over bangladeshi leader's death | by prashant dhawan",
        "india vs sri lanka | semi-final | highlights | dp world men's u-19 asia cup 2025",
        "drinking hot milk in india"
    ]
    
    for text in test_cases:
        ner, nouns = process_english_text(text)
        print(f"\nInput: {text}")
        print(f"NER: {ner}")
        print(f"Nouns: {nouns}")


def test_hinglish_pipeline():
    print("\n" + "="*60)
    print("TEST: Hinglish Pipeline (Remove Hindi -> English Pipeline)")
    print("="*60)
    
    test_cases = [
        "आखरी अमावस्या और विनाश ?|| swami yo",
        "भारत जोड़ो यात्रा | rahul gandhi | congress",
        "modi speech in hindi राम मंदिर #ayodhya"
    ]
    
    for text in test_cases:
        text_v1, ner, nouns = process_hinglish_text(text)
        print(f"\nInput: {text}")
        print(f"text_v1: {text_v1}")
        print(f"NER: {ner}")
        print(f"Nouns: {nouns}")


def test_full_pipeline():
    print("\n" + "="*60)
    print("TEST: Full Pipeline on testing_json.json")
    print("="*60)
    
    data = load_test_data()
    if not data:
        return
    
    events = data.get("events", [])
    print(f"\nLoaded {len(events)} events")
    
    # Process all events
    processed = process_events_batch(events)
    
    # Show results for each event
    for i, event in enumerate(processed):
        print(f"\n--- Event {i+1} ---")
        print(f"Type: {event.get('type')}, Engagement: {event.get('engagement')}")
        print(f"Language: {event.get('language_type')}")
        print(f"Text: {event.get('text_clean', '')[:80]}...")
        print(f"Hashtags: {event.get('hashtags', [])}")
        print(f"NER: {event.get('ner', [])}")
        print(f"Nouns: {event.get('nouns', [])}")
        if event.get('text_v1'):
            print(f"text_v1: {event.get('text_v1')}")
        print(f"Micro Topics: {event.get('micro_topics', [])}")
    
    # Aggregated stats
    print("\n" + "="*60)
    print("AGGREGATED RESULTS")
    print("="*60)
    
    aggregated = get_aggregated_topics(processed)
    
    print(f"\nStats: {aggregated['stats']}")
    print(f"\nTop Hashtags: {aggregated['top_hashtags'][:10]}")
    print(f"\nTop NER: {aggregated['top_ner'][:10]}")
    print(f"\nTop Nouns: {aggregated['top_nouns'][:10]}")
    print(f"\nTop Micro Topics: {aggregated['top_micro_topics'][:15]}")


if __name__ == "__main__":
    print("="*60)
    print("Micro Topic Extraction v2 - Test Suite")
    print("="*60)
    
    # Check if models are available
    print("\nChecking models...")
    
    try:
        import spacy
        nlp = spacy.load("en_core_web_md")
        print("[OK] spaCy en_core_web_md loaded")
    except:
        print("[X] spaCy en_core_web_md not available")
        print("    Run: python -m spacy download en_core_web_md")
    
    try:
        import stanza
        print("[OK] Stanza package available")
    except:
        print("[X] Stanza not installed")
        print("    Run: pip install stanza")
    
    # Run tests
    test_hashtag_extraction()
    test_english_pipeline()
    test_hinglish_pipeline()
    test_full_pipeline()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
