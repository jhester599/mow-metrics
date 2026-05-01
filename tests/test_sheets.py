from mow_metrics.models import (
    CONFIRMED_STATUS_MOWED,
    CONFIRMED_STATUS_PENDING,
    CONFIRMED_STATUS_SKIPPED,
    LOG_HEADERS,
    USER_CONFIG_HEADERS,
)
from mow_metrics.sheets import (
    build_log_key,
    ensure_headers,
    existing_log_keys,
    find_log_row_number,
    update_confirmation,
    upsert_user_config_row,
)


def test_shared_headers_and_status_constants_are_defined():
    assert USER_CONFIG_HEADERS[:4] == [
        "Username",
        "Active Year",
        "Zip Code",
        "Latitude",
    ]
    assert "Prediction Reason" in LOG_HEADERS
    assert CONFIRMED_STATUS_PENDING == "Pending"
    assert CONFIRMED_STATUS_MOWED == "Mowed"
    assert CONFIRMED_STATUS_SKIPPED == "Skipped"


def test_build_log_key_uses_username_year_and_date():
    assert build_log_key("jeff", 2026, "2026-04-23") == "jeff|2026|2026-04-23"


def test_existing_log_keys_collects_unique_keys():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-30"},
    ]
    assert existing_log_keys(rows) == {
        "jeff|2026|2026-04-23",
        "jeff|2026|2026-04-30",
    }


def test_upsert_user_config_row_replaces_matching_username_and_year():
    existing_rows = [
        {"Username": "jeff", "Active Year": "2026", "Zip Code": "11111"},
        {"Username": "amy", "Active Year": "2026", "Zip Code": "22222"},
    ]
    new_row = {"Username": "jeff", "Active Year": "2026", "Zip Code": "44236"}

    updated_rows = upsert_user_config_row(existing_rows, new_row)

    assert updated_rows == [
        {"Username": "jeff", "Active Year": "2026", "Zip Code": "44236"},
        {"Username": "amy", "Active Year": "2026", "Zip Code": "22222"},
    ]


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.updated_ranges = []

    def row_values(self, row_number):
        return self.values[row_number - 1] if len(self.values) >= row_number else []

    def update(self, range_name, values):
        self.updated_ranges.append((range_name, values))


def test_ensure_headers_writes_missing_header_row():
    worksheet = FakeWorksheet(values=[])

    ensure_headers(worksheet, USER_CONFIG_HEADERS)

    assert worksheet.updated_ranges == [("1:1", [USER_CONFIG_HEADERS])]


def test_find_log_row_number_returns_sheet_row_for_matching_key():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "amy", "Year": "2026", "Date": "2026-04-23"},
    ]

    assert find_log_row_number(rows, "amy", 2026, "2026-04-23") == 3


def test_update_confirmation_updates_confirmed_status_and_timestamp_cells():
    worksheet = FakeWorksheet(values=[LOG_HEADERS])

    update_confirmation(worksheet, row_number=2, confirmed_status="Mowed", updated_at="2026-04-24T12:00:00")

    assert worksheet.updated_ranges == [
        ("K2", [["Mowed"]]),
        ("N2", [["2026-04-24T12:00:00"]]),
    ]
