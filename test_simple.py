#!/usr/bin/env python3
"""
Simple test script for the Page Visit Counter API
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("🚀 Testing Simple Page Visit Counter API")
    print("=" * 50)
    
    # Test health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   ✅ Health: {response.json()['status']}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test recording visits
    print("\n2. Recording some visits...")
    test_urls = [
        "https://example.com/home",
        "https://example.com/about",
        "https://example.com/contact",
        "https://example.com/home"  # Duplicate to test counting
    ]
    
    for url in test_urls:
        try:
            response = requests.post(
                f"{BASE_URL}/visit",
                json={"url": url}
            )
            if response.status_code == 200:
                print(f"   ✅ Recorded: {url}")
            else:
                print(f"   ❌ Failed to record: {url}")
        except Exception as e:
            print(f"   ❌ Error recording {url}: {e}")
    
    # Test simple GET endpoint
    print("\n3. Testing simple GET endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/?url=https://example.com/simple-test")
        if response.status_code == 200:
            print(f"   ✅ Simple GET: {response.json()['message']}")
    except Exception as e:
        print(f"   ❌ Simple GET failed: {e}")
    
    # Wait a moment
    time.sleep(1)
    
    # Get statistics
    print("\n4. Getting statistics...")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"   📊 Total visits: {stats['total_visits']}")
            print(f"   👥 Unique visitors: {stats['unique_visitors']}")
            print(f"   📈 Popular pages:")
            for url, count in stats['popular_pages'].items():
                print(f"      - {url}: {count} visits")
            
            print(f"   ⏰ Recent visits:")
            for visit in stats['recent_visits'][:3]:  # Show only first 3
                print(f"      - {visit['url']} at {visit['timestamp']}")
        else:
            print(f"   ❌ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Stats failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    print("\n💡 Try these URLs in your browser:")
    print(f"   - API Docs: {BASE_URL}/docs")
    print(f"   - Health: {BASE_URL}/health")
    print(f"   - Stats: {BASE_URL}/stats")
    print(f"   - Record visit: {BASE_URL}/?url=https://yoursite.com")

if __name__ == "__main__":
    test_api()
