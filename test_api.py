#!/usr/bin/env python3
"""
Simple test script for the Page Visit Counter API
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code} - {response.json()}")

def test_record_visit():
    """Test recording a visit"""
    print("\nTesting visit recording...")
    visit_data = {
        "url": "https://example.com/page1"
    }
    response = requests.post(f"{BASE_URL}/visit", json=visit_data)
    print(f"Visit recording: {response.status_code} - {response.json()}")

def test_legacy_visit():
    """Test the legacy visit endpoint"""
    print("\nTesting legacy visit recording...")
    response = requests.get(f"{BASE_URL}/?url=https://example.com/page2")
    print(f"Legacy visit: {response.status_code} - {response.json()}")

def test_bulk_visits():
    """Test bulk visit recording"""
    print("\nTesting bulk visit recording...")
    visits = [
        {"url": "https://example.com/page3"},
        {"url": "https://example.com/page4"},
        {"url": "https://example.com/page5"}
    ]
    response = requests.post(f"{BASE_URL}/bulk-visits", json=visits)
    print(f"Bulk visits: {response.status_code} - {response.json()}")

def test_summary():
    """Test the summary endpoint"""
    print("\nTesting summary...")
    response = requests.get(f"{BASE_URL}/summary")
    print(f"Summary: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total entries: {data.get('total_entries', 0)}")
        print(f"URLs tracked: {len(data.get('data', {}))}")

def test_url_stats():
    """Test URL-specific statistics"""
    print("\nTesting URL stats...")
    url = "https://example.com/page1"
    response = requests.get(f"{BASE_URL}/stats/{url}")
    print(f"URL stats: {response.status_code}")
    if response.status_code == 200:
        print(f"Stats: {response.json()}")

def test_rate_limiting():
    """Test rate limiting"""
    print("\nTesting rate limiting...")
    visit_data = {"url": "https://example.com/rate-test"}
    
    # Make multiple requests quickly
    for i in range(15):
        response = requests.post(f"{BASE_URL}/visit", json=visit_data)
        if response.status_code == 429:
            print(f"Rate limited at request {i+1}")
            break
        elif i == 14:
            print("Rate limiting not triggered (this might be expected)")

if __name__ == "__main__":
    print("Testing Page Visit Counter API")
    print("=" * 40)
    
    try:
        test_health_check()
        test_record_visit()
        test_legacy_visit()
        test_bulk_visits()
        
        # Wait a moment for data to be processed
        time.sleep(1)
        
        test_summary()
        test_url_stats()
        test_rate_limiting()
        
        print("\n" + "=" * 40)
        print("Tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API server.")
        print("Make sure the server is running with: uvicorn page_count:app --reload")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
