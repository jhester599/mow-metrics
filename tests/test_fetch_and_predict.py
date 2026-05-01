from datetime import date

from fetch_and_predict import build_log_entry, process_users, should_append_log_row, should_process_user


class FakeSettings:
    precipitation_threshold_mm = 0.2
    workday_start_hour = 8
    workday_end_hour = 17
    saturation_threshold_mm = 5.0
    saturation_start_hour = 18
    saturation_end_hour = 23
    mow_day_morning_start_hour = 6
    mow_day_morning_end_hour = 12


def test_should_process_user_only_when_yesterday_matches_mow_day_and_today_is_in_season():
    user_row = {
        "Expected Mow Day": "Wednesday",
        "Season Start": "2026-04-01",
        "Season End": "2026-11-30",
    }

    assert should_process_user(user_row, today=date(2026, 4, 23)) is True
    assert should_process_user(user_row, today=date(2026, 12, 1)) is False


def test_should_append_log_row_skips_existing_key():
    existing_keys = {"jeff|2026|2026-04-23"}
    assert not should_append_log_row("jeff", 2026, "2026-04-23", existing_keys)
    assert should_append_log_row("jeff", 2026, "2026-04-30", existing_keys)


def test_build_log_entry_defaults_confirmation_to_pending():
    user_row = {
        "Username": "jeff",
        "Active Year": "2026",
        "Zip Code": "44236",
        "Latitude": "41.35",
        "Longitude": "-81.44",
        "Expected Mow Day": "Wednesday",
    }

    entry = build_log_entry(
        user_row=user_row,
        mow_date="2026-04-22",
        weather_summary="Workday rainfall: 0.00 mm",
        raw_api_json={"hourly": {"precipitation": [0.0] * 24}},
        predicted_status="Mowed",
        prediction_reason="Mowed because only 0.00 mm of rain fell during work hours.",
        created_at="2026-04-23T12:00:00",
    )

    assert entry["Username"] == "jeff"
    assert entry["Date"] == "2026-04-22"
    assert entry["Confirmed Status"] == "Pending"
    assert "precipitation" in entry["Raw API JSON"]


def test_process_users_uses_previous_day_saturation_for_prediction(monkeypatch):
    user_rows = [
        {
            "Username": "jeff",
            "Active Year": "2026",
            "Zip Code": "44236",
            "Latitude": "41.35",
            "Longitude": "-81.44",
            "Expected Mow Day": "Wednesday",
            "Season Start": "2026-04-01",
            "Season End": "2026-11-30",
        }
    ]
    payload = {
        "hourly": {
            "time": [f"2026-04-21T{hour:02d}:00" for hour in range(24)]
            + [f"2026-04-22T{hour:02d}:00" for hour in range(24)],
            "precipitation": ([0.0] * 20 + [5.5] + [0.0] * 3) + ([0.0] * 24),
        }
    }

    monkeypatch.setattr("fetch_and_predict.fetch_daily_weather", lambda **kwargs: payload)

    entries = process_users(
        user_rows=user_rows,
        log_rows=[],
        today=date(2026, 4, 23),
        settings=FakeSettings(),
    )

    assert entries[0]["Predicted Status"] == "Skipped"
    assert "saturated" in entries[0]["Prediction Reason"]
