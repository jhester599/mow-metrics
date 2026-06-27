from datetime import date

from pathlib import Path

from app import (
    build_user_config_row,
    compute_accuracy_metrics,
    compute_monthly_accuracy,
    compute_optimal_thresholds,
    confirmation_updates,
    count_confirmed_mows_for_month,
    display_log_rows,
    expected_mow_dates,
    filter_log_rows,
    find_user_profile,
    missing_backfill_dates,
    normalize_confirmed_status,
    parse_weather_summary_values,
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


def test_compute_accuracy_metrics_counts_correct_and_incorrect_predictions():
    rows = [
        {"Predicted Status": "Mowed", "Confirmed Status": "Mowed"},
        {"Predicted Status": "Mowed", "Confirmed Status": "Skipped"},
        {"Predicted Status": "Skipped", "Confirmed Status": "Skipped"},
        {"Predicted Status": "Skipped", "Confirmed Status": "Mowed"},
        {"Predicted Status": "Mowed", "Confirmed Status": "Pending"},
    ]
    metrics = compute_accuracy_metrics(rows)
    assert metrics["total"] == 4
    assert metrics["correct"] == 2
    assert metrics["accuracy_pct"] == 50.0
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1


def test_compute_accuracy_metrics_returns_none_accuracy_when_no_confirmed_rows():
    rows = [{"Predicted Status": "Mowed", "Confirmed Status": "Pending"}]
    metrics = compute_accuracy_metrics(rows)
    assert metrics["total"] == 0
    assert metrics["accuracy_pct"] is None


def test_compute_monthly_accuracy_groups_by_month():
    rows = [
        {"Date": "2026-04-01", "Predicted Status": "Mowed", "Confirmed Status": "Mowed"},
        {"Date": "2026-04-08", "Predicted Status": "Mowed", "Confirmed Status": "Skipped"},
        {"Date": "2026-05-01", "Predicted Status": "Skipped", "Confirmed Status": "Skipped"},
    ]
    monthly = compute_monthly_accuracy(rows)
    assert len(monthly) == 2
    april = next(m for m in monthly if m["month"] == "2026-04")
    assert april["total"] == 2
    assert april["correct"] == 1
    assert april["accuracy_pct"] == 50.0
    may = next(m for m in monthly if m["month"] == "2026-05")
    assert may["accuracy_pct"] == 100.0


def test_parse_weather_summary_values_extracts_rainfall_windows():
    summary = (
        "Prior evening rainfall: 3.50 mm; morning rainfall: 0.00 mm; "
        "workday rainfall: 0.20 mm; evening rainfall: 1.00 mm"
    )
    values = parse_weather_summary_values(summary)
    assert values is not None
    assert values["saturation_mm"] == 3.50
    assert values["morning_mm"] == 0.00
    assert values["workday_mm"] == 0.20


def test_parse_weather_summary_values_returns_none_for_unrecognized_format():
    assert parse_weather_summary_values("Daily rainfall: 0.30 mm") is None


def test_compute_optimal_thresholds_returns_none_when_too_few_rows():
    rows = [
        {"Predicted Status": "Mowed", "Confirmed Status": "Mowed", "Weather Summary": "Prior evening rainfall: 0.00 mm; morning rainfall: 0.00 mm; workday rainfall: 0.00 mm; evening rainfall: 0.00 mm"},
        {"Predicted Status": "Mowed", "Confirmed Status": "Skipped", "Weather Summary": "Prior evening rainfall: 0.00 mm; morning rainfall: 0.00 mm; workday rainfall: 0.00 mm; evening rainfall: 0.00 mm"},
    ]
    assert compute_optimal_thresholds(rows) is None


def test_compute_optimal_thresholds_suggests_thresholds_from_confirmed_history():
    summary_dry = "Prior evening rainfall: 0.00 mm; morning rainfall: 0.00 mm; workday rainfall: 0.00 mm; evening rainfall: 0.00 mm"
    summary_wet = "Prior evening rainfall: 6.00 mm; morning rainfall: 0.50 mm; workday rainfall: 0.40 mm; evening rainfall: 0.00 mm"
    rows = [
        {"Predicted Status": "Mowed", "Confirmed Status": "Mowed", "Weather Summary": summary_dry},
        {"Predicted Status": "Mowed", "Confirmed Status": "Mowed", "Weather Summary": summary_dry},
        {"Predicted Status": "Mowed", "Confirmed Status": "Skipped", "Weather Summary": summary_wet},
    ]
    result = compute_optimal_thresholds(rows)
    assert result is not None
    assert result["sample_size"] == 3
    assert result["accuracy_pct"] == 100.0
    assert result["precipitation_threshold_mm"] <= 0.5
    assert result["saturation_threshold_mm"] <= 6.0
