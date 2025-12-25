"""Test script for channel metadata extraction"""
import sys
sys.path.insert(0, '.')

from services.channel_service import get_channel_metadata
import json

test_url = "https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw"
print(f"Testing with: {test_url}")
result = get_channel_metadata(test_url)
print(json.dumps(result, indent=2, default=str))
