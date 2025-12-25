"""Test video category scraper"""
import sys
sys.path.insert(0, '.')

from services.video_service import get_video_metadata
import json

# Test with a real video
test_url = "https://www.youtube.com/watch?v=GopDfbvyY0k"
print(f"Testing with: {test_url}")

# print("\n--- Category only ---")
# category = get_video_category(test_url)
# print(f"Category: {category}")

print("\n--- Full metadata ---")
metadata = get_video_metadata(test_url)
print(json.dumps(metadata, indent=2, default=str))

# Extract just the category
category = metadata.get("category")
print(f"\n✅ Category: {category}")
