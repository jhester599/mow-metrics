from datetime import date

from mow_metrics.weather import (
    build_weather_summary,
    extract_hourly_precipitation,
    extract_hourly_precipitation_for_date,
    fetch_daily_weather,
    geocode_zip,
    predict_mow_status,
)


def test_predicts_skipped_when_workday_rainfall_exceeds_threshold():
    hourly_precipitation = [0.0] * 24
    hourly_precipitation[9] = 0.35

    result = predict_mow_status(
        hourly_precipitation=hourly_precipitation,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
    )

    assert result.predicted_status == "Skipped"
    assert "0.35 mm" in result.reason


def test_predicts_skipped_when_previous_evening_rain_saturates_ground():
    previous_day = [0.0] * 24
    mow_day = [0.0] * 24
    previous_day[20] = 5.5

    result = predict_mow_status(
        hourly_precipitation=mow_day,
        previous_day_hourly_precipitation=previous_day,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        saturation_threshold_mm=5.0,
        saturation_start_hour=18,
        saturation_end_hour=23,
        morning_start_hour=6,
        morning_end_hour=12,
    )

    assert result.predicted_status == "Skipped"
    assert "saturated" in result.reason
    assert "5.50 mm" in result.reason


def test_predicts_skipped_when_mow_day_morning_rain_exceeds_threshold():
    previous_day = [0.0] * 24
    mow_day = [0.0] * 24
    mow_day[7] = 0.3

    result = predict_mow_status(
        hourly_precipitation=mow_day,
        previous_day_hourly_precipitation=previous_day,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        saturation_threshold_mm=5.0,
        saturation_start_hour=18,
        saturation_end_hour=23,
        morning_start_hour=6,
        morning_end_hour=12,
    )

    assert result.predicted_status == "Skipped"
    assert "morning" in result.reason
    assert "0.30 mm" in result.reason


def test_predicts_mowed_when_rain_falls_only_after_work_window():
    previous_day = [0.0] * 24
    mow_day = [0.0] * 24
    mow_day[21] = 4.0

    result = predict_mow_status(
        hourly_precipitation=mow_day,
        previous_day_hourly_precipitation=previous_day,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        saturation_threshold_mm=5.0,
        saturation_start_hour=18,
        saturation_end_hour=23,
        morning_start_hour=6,
        morning_end_hour=12,
    )

    assert result.predicted_status == "Mowed"
    assert "evening rainfall: 4.00 mm" in result.weather_summary


def test_extract_hourly_precipitation_reads_open_meteo_payload():
    payload = {"hourly": {"precipitation": [0.0, 0.1, 0.2]}}
    assert extract_hourly_precipitation(payload) == [0.0, 0.1, 0.2]


def test_extract_hourly_precipitation_for_date_reads_matching_day_from_multi_day_payload():
    payload = {
        "hourly": {
            "time": [
                "2026-04-21T00:00",
                "2026-04-21T01:00",
                "2026-04-22T00:00",
                "2026-04-22T01:00",
            ],
            "precipitation": [0.1, 0.2, 0.3, 0.4],
        }
    }

    assert extract_hourly_precipitation_for_date(payload, date(2026, 4, 22)) == [0.3, 0.4]


def test_build_weather_summary_formats_total_rainfall():
    assert build_weather_summary([0.0, 0.1, 0.2]) == "Daily rainfall: 0.30 mm"


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(self.payload)


def test_geocode_zip_uses_open_meteo_geocoding_response():
    payload = {"results": [{"latitude": 41.35, "longitude": -81.44, "name": "Hudson"}]}
    session = FakeSession(payload)

    result = geocode_zip("44236", session=session)

    assert result.latitude == 41.35
    assert result.longitude == -81.44
    assert session.calls[0]["params"]["name"] == "44236"


def test_fetch_daily_weather_builds_archive_request_for_target_date():
    payload = {"hourly": {"precipitation": [0.0] * 24}}
    session = FakeSession(payload)

    result = fetch_daily_weather(41.35, -81.44, date(2026, 4, 22), session=session)

    assert result == payload
    assert session.calls[0]["params"]["start_date"] == "2026-04-21"
    assert session.calls[0]["params"]["end_date"] == "2026-04-22"
    assert session.calls[0]["params"]["hourly"] == "precipitation"
