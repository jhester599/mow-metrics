from datetime import date

from app import build_user_config_row, count_confirmed_mows_for_month, filter_log_rows, pending_rows


def test_count_confirmed_mows_for_month_counts_only_yes_rows_in_selected_month():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-02", "Confirmed Status": "Yes"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-09", "Confirmed Status": "Pending"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-05-01", "Confirmed Status": "Yes"},
    ]

    total = count_confirmed_mows_for_month(rows, selected_year=2026, current_month=4)

    assert total == 1


def test_pending_rows_returns_only_pending_items():
    rows = [
        {"Confirmed Status": "Pending", "Date": "2026-04-09"},
        {"Confirmed Status": "Yes", "Date": "2026-04-16"},
    ]
    assert pending_rows(rows) == [{"Confirmed Status": "Pending", "Date": "2026-04-09"}]


def test_filter_log_rows_matches_selected_username_and_year():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-09"},
        {"Username": "amy", "Year": "2026", "Date": "2026-04-09"},
        {"Username": "jeff", "Year": "2025", "Date": "2025-04-09"},
    ]

    assert filter_log_rows(rows, username="jeff", year=2026) == [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-09"}
    ]


def test_build_user_config_row_includes_geocoded_coordinates_and_season_dates():
    row = build_user_config_row(
        username="jeff",
        active_year=2026,
        zip_code="44236",
        latitude=41.35,
        longitude=-81.44,
        expected_mow_day="Wednesday",
        season_start=date(2026, 4, 1),
        season_end=date(2026, 11, 30),
        timestamp="2026-04-24T12:00:00",
    )

    assert row["Username"] == "jeff"
    assert row["Zip Code"] == "44236"
    assert row["Latitude"] == "41.35"
    assert row["Season Start"] == "2026-04-01"
