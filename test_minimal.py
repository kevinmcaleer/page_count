import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"


def test_health():
    print("Testing /health endpoint...")
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    print(r.json())


def test_post_visit():
    print("Testing POST /visit endpoint...")
    url = "https://example.com/test"
    r = requests.post(f"{BASE_URL}/visit", json={"url": url})
    assert r.status_code == 200
    data = r.json()
    print(data)
    assert data["url"] == url
    assert "ip" in data
    assert "timestamp" in data


def test_get_stats():
    print("Testing /stats endpoint...")
    r = requests.get(f"{BASE_URL}/stats")
    assert r.status_code == 200
    data = r.json()
    print(data)
    assert "total_visits" in data
    assert "unique_visitors" in data
    assert "popular_pages" in data


def test_simple_get():
    print("Testing simple GET / endpoint...")
    url = "https://example.com/simple"
    r = requests.get(f"{BASE_URL}/?url={url}")
    assert r.status_code == 200
    data = r.json()
    print(data)
    assert data["url"] == url
    assert "timestamp" in data


def test_all_visits_filters():
    print("Testing /all-visits endpoint with filters...")
    # Insert a visit for today
    url = "https://example.com/filter"
    requests.post(f"{BASE_URL}/visit", json={"url": url})
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # Test start_date
    r = requests.get(f"{BASE_URL}/all-visits?start_date={today}")
    assert r.status_code == 200
    data = r.json()
    print(f"Visits since {today}: {data['total_count']}")
    # Test end_date
    r = requests.get(f"{BASE_URL}/all-visits?end_date={today}")
    assert r.status_code == 200
    # Test since (should return at least one visit)
    since = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
    r = requests.get(f"{BASE_URL}/all-visits?since={since}")
    assert r.status_code == 200
    data = r.json()
    print(f"Visits since {since}: {data['total_count']}")
    # Test limit
    r = requests.get(f"{BASE_URL}/all-visits?limit=2")
    assert r.status_code == 200
    data = r.json()
    print(f"Visits (limit=2): {len(data['visits'])}")


def run_all():
    test_health()
    test_post_visit()
    test_get_stats()
    test_simple_get()
    test_all_visits_filters()
    print("All tests passed!")

if __name__ == "__main__":
    run_all()
