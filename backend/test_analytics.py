"""Test analytics API"""
import sys
sys.path.insert(0, '.')

from services.analytics_service import get_channel_analytics
import json

token = "692d50d2-16a3-4e33-9e67-01a4d2124d4b"

print("=== Testing 'all' filter ===")
result_all = get_channel_analytics(token, 5, "all")
print(f"Total count: {result_all.get('total_count')}")
print(f"View distribution: {result_all.get('view_distribution')}")
print(f"Engagement summary: {result_all.get('engagement_summary')}")

print("\n=== Testing 'watch' filter ===")
result_watch = get_channel_analytics(token, 5, "watch")
print(f"Total count: {result_watch.get('total_count')}")
print(f"View distribution: {result_watch.get('view_distribution')}")

print("\n=== Testing 'view' filter ===")
result_view = get_channel_analytics(token, 5, "view")
print(f"Total count: {result_view.get('total_count')}")
print(f"View distribution: {result_view.get('view_distribution')}")
