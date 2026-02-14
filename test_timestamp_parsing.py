import pytest
from dateutil import parser as date_parser
from datetime import datetime

@pytest.mark.parametrize("input_ts,expected", [
    ("2025-09-14 10:30:00", "2025-09-14 10:30:00"),
    ("2025-09-14T10:30:00", "2025-09-14 10:30:00"),
    ("2025-09-14T10:30:00Z", "2025-09-14 10:30:00"),
    ("2025-09-14T10:30:00+00:00", "2025-09-14 10:30:00"),
    ("2025-09-14", "2025-09-14 00:00:00"),
    ("2025-09-14 5:7:2", "2025-09-14 05:07:02"),
    ("2025/09/14 10:30:00", "2025-09-14 10:30:00"),
])
def test_timestamp_parsing(input_ts, expected):
    dt = date_parser.parse(input_ts)
    norm = dt.strftime("%Y-%m-%d %H:%M:%S")
    assert norm == expected, f"Failed to parse '{input_ts}' as '{expected}', got '{norm}'"

@pytest.mark.parametrize("bad_ts", [
    "not-a-date",
    "2025-99-99",
    "",
    None,
])
def test_timestamp_parsing_failures(bad_ts):
    with pytest.raises(Exception):
        date_parser.parse(bad_ts)
