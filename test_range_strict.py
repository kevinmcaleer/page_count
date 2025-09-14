import requests
import pytest
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def insert_visit(url, ts):
    requests.post(f"{BASE_URL}/visit", json={"url": url})
    # Directly update the timestamp for test accuracy
    import sqlite3
    conn = sqlite3.connect("./data/visits.db")
    c = conn.cursor()
    c.execute("UPDATE visits SET timestamp=? WHERE url=?", (ts, url))
    conn.commit()
    conn.close()

@pytest.fixture(scope="function")
def setup_range_test_data():
    # Insert visits for 3 days, with 2 visits on day 2
    base_date = (datetime.now() - timedelta(days=365*10)).date()
    days = [base_date - timedelta(days=i) for i in range(3)]
    urls = [f"https://example.com/range-check-{i}" for i in range(3)]
    import sqlite3
    conn = sqlite3.connect("./data/visits.db")
    c = conn.cursor()
    for url in urls:
        c.execute("DELETE FROM visits WHERE url=?", (url,))
    conn.commit()
    conn.close()
    for i, (d, url) in enumerate(zip(days, urls)):
        ts = datetime.combine(d, datetime.min.time()).strftime("%Y-%m-%d %H:%M:%S")
        insert_visit(url, ts)
        if i == 1:
            insert_visit(url, ts)  # 2 visits on day 2
    return base_date, urls, days

def test_range_returns_only_in_range(setup_range_test_data):
    base_date, urls, days = setup_range_test_data
    # Query for only day 2
    start = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
    end = base_date.strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/all-visits?range={start},{end}")
    data = r.json()
    # Should only return visits for day 2
    for v in data['visits']:
        assert v['timestamp'].startswith(start), f"Visit {v} not in range {start} to {end}"
    assert int(data['total_count'].replace(',', '')) == 2

def test_range_excludes_out_of_range(setup_range_test_data):
    base_date, urls, days = setup_range_test_data
    # Query for a range with no visits
    start = (base_date - timedelta(days=10)).strftime("%Y-%m-%d")
    end = (base_date - timedelta(days=9)).strftime("%Y-%m-%d")
    r = requests.get(f"{BASE_URL}/all-visits?range={start},{end}")
    data = r.json()
    assert int(data['total_count'].replace(',', '')) == 0
    assert data['visits'] == []
