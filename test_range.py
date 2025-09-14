import requests
import pytest
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

@pytest.fixture(scope="function")
def setup_test_data():
    # Insert visits for 5 days, with 2 visits on day 2
    base_date = (datetime.now() - timedelta(days=365*10)).date()
    days = [base_date - timedelta(days=i) for i in range(5)]
    urls = [f"https://example.com/range-test-{i}" for i in range(5)]
    import sqlite3
    conn = sqlite3.connect("./data/visits.db")
    c = conn.cursor()
    # Clean up any old test data for these URLs
    for url in urls:
        c.execute("DELETE FROM visits WHERE url=?", (url,))
    conn.commit()
    conn.close()

    # Insert 2 visits on day 2, 1 visit on other days
    for i, (d, url) in enumerate(zip(days, urls)):
        ts = datetime.combine(d, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        requests.post(f"{BASE_URL}/visit", json={"url": url})
        # Insert a second visit for day 2
        if i == 2:
            requests.post(f"{BASE_URL}/visit", json={"url": url})
        # Directly update the timestamp for test accuracy
        conn = sqlite3.connect("./data/visits.db")
        c = conn.cursor()
        c.execute("UPDATE visits SET timestamp=? WHERE url=?", (ts, url))
        conn.commit()
        conn.close()
    return base_date, urls

def test_range_day_2(setup_test_data):
    base_date, urls = setup_test_data
    # Test: range covering only day 2 (should return 2 visits)
    start = (base_date - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/all-visits?range={start},{end}")
    data = r.json()
    assert int(data['total_count'].replace(',', '')) == 2, f"Expected 2 visits, got {data['total_count']}"
    # Optionally, check that both visits are for the correct url
    for v in data['visits']:
        assert v['url'] == urls[2]

def test_range_all_days(setup_test_data):
    base_date, urls = setup_test_data
    # Test: range covering all 5 days (should return 6 visits)
    start = (base_date - timedelta(days=4)).strftime("%Y-%m-%d")
    end = (base_date + timedelta(days=1)).strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/all-visits?range={start},{end}")
    data = r.json()
    assert int(data['total_count'].replace(',', '')) == 6, f"Expected 6 visits, got {data['total_count']}"
    # Optionally, check that all expected urls are present
    returned_urls = [v['url'] for v in data['visits']]
    for url in urls:
        assert url in returned_urls
