from datetime import date

from pathlib import Path

from app import (
    build_user_config_row,
    confirmation_updates,
    count_confirmed_mows_for_month,
    display_log_rows,
    expected_mow_dates,
    filter_log_rows,
    find_user_profile,
    missing_backfill_dates,
    normalize_confirmed_status,
    pending_rows,
    status_fill_color,
    sort_log_rows_by_date,
)


def test_count_confirmed_mows_for_month_counts_only_mowed_rows_in_selected_month():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-02", "Confirmed Status": "Mowed"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-09", "Confirmed Status": "Pending"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-16", "Confirmed Status": "Skipped"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-05-01", "Confirmed Status": "Mowed"},
    ]

    total = count_confirmed_mows_for_month(rows, selected_year=2026, current_month=4)

    assert total == 1


def test_app_bootstraps_src_package_path_before_importing_mow_metrics():
    app_source = Path("app.py").read_text()
    bootstrap_position = app_source.index("sys.path.insert")
    package_import_position = app_source.index("from mow_metrics.config")
    assert bootstrap_position < package_import_position


def test_pending_rows_returns_only_pending_items():
    rows = [
        {"Confirmed Status": "Pending", "Date": "2026-04-09"},
        {"Confirmed Status": "Mowed", "Date": "2026-04-16"},
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


def test_sort_log_rows_by_date_orders_oldest_to_newest():
    rows = [
        {"Date": "2026-04-22", "Confirmed Status": "Pending"},
        {"Date": "2026-04-01", "Confirmed Status": "Pending"},
        {"Date": "2026-04-15", "Confirmed Status": "Pending"},
    ]

    assert sort_log_rows_by_date(rows) == [
        {"Date": "2026-04-01", "Confirmed Status": "Pending"},
        {"Date": "2026-04-15", "Confirmed Status": "Pending"},
        {"Date": "2026-04-22", "Confirmed Status": "Pending"},
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


def test_expected_mow_dates_generates_weekday_dates_through_yesterday_and_caps_at_season_end():
    dates = expected_mow_dates(
        season_start=date(2026, 4, 1),
        season_end=date(2026, 4, 30),
        expected_mow_day="Wednesday",
        today=date(2026, 5, 10),
    )

    assert dates == [
        date(2026, 4, 1),
        date(2026, 4, 8),
        date(2026, 4, 15),
        date(2026, 4, 22),
        date(2026, 4, 29),
    ]


def test_missing_backfill_dates_skips_existing_log_keys():
    user_row = {
        "Username": "JRH",
        "Active Year": "2026",
        "Expected Mow Day": "Wednesday",
        "Season Start": "2026-04-01",
        "Season End": "2026-04-30",
    }
    log_rows = [
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-01"},
        {"Username": "Someone Else", "Year": "2026", "Date": "2026-04-08"},
    ]

    dates = missing_backfill_dates(user_row, log_rows, today=date(2026, 4, 16))

    assert dates == [date(2026, 4, 8), date(2026, 4, 15)]


def test_find_user_profile_matches_username_and_year():
    rows = [
        {"Username": "JRH", "Active Year": "2025"},
        {"Username": "JRH", "Active Year": "2026", "Expected Mow Day": "Wednesday"},
    ]

    assert find_user_profile(rows, "JRH", 2026) == rows[1]


def test_confirmation_updates_returns_only_changed_statuses():
    original_rows = [
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-01", "Confirmed Status": "Pending"},
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-08", "Confirmed Status": "Skipped"},
    ]
    edited_rows = [
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-01", "Confirmed Status": "Mowed"},
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-08", "Confirmed Status": "Skipped"},
    ]

    assert confirmation_updates(original_rows, edited_rows) == [
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-01", "Confirmed Status": "Mowed"}
    ]


def test_confirmation_updates_accepts_set_confirmed_status_editor_column():
    original_rows = [
        {"Username": "JRH", "Year": "2026", "Date": "2026-04-01", "Confirmed Status": "Pending"},
    ]
    edited_rows = [
        {
            "Username": "JRH",
            "Year": "2026",
            "Date": "2026-04-01",
            "Confirmed Status": "Pending",
            "Set Confirmed Status": "Skipped",
        },
    ]

    assert confirmation_updates(original_rows, edited_rows) == [
        {
            "Username": "JRH",
            "Year": "2026",
            "Date": "2026-04-01",
            "Confirmed Status": "Skipped",
            "Set Confirmed Status": "Skipped",
        }
    ]


def test_display_log_rows_hides_raw_json_and_adds_editable_status_column():
    rows = [
        {
            "Date": "2026-04-01",
            "Predicted Status": "Skipped",
            "Confirmed Status": "No",
            "Raw API JSON": "{}",
        }
    ]

    assert display_log_rows(rows) == [
        {
            "Date": "2026-04-01",
            "Predicted Status": "Skipped",
            "Confirmed Status": "Skipped",
            "Set Confirmed Status": "Skipped",
        }
    ]


def test_normalize_confirmed_status_maps_legacy_values_to_prediction_terms():
    assert normalize_confirmed_status("Yes") == "Mowed"
    assert normalize_confirmed_status("No") == "Skipped"
    assert normalize_confirmed_status("Pending") == "Pending"
    assert normalize_confirmed_status("Mowed") == "Mowed"


def test_status_fill_color_uses_green_for_mowed_red_for_skipped_and_blank_for_pending():
    assert status_fill_color("Mowed") == "background-color: #d9ead3"
    assert status_fill_color("Skipped") == "background-color: #f4cccc"
    assert status_fill_color("Pending") == ""
