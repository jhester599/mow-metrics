from datetime import date

from mow_metrics.weather import (
    build_weather_summary,
    extract_hourly_precipitation,
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


def test_extract_hourly_precipitation_reads_open_meteo_payload():
    payload = {"hourly": {"precipitation": [0.0, 0.1, 0.2]}}
    assert extract_hourly_precipitation(payload) == [0.0, 0.1, 0.2]


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
    assert session.calls[0]["params"]["start_date"] == "2026-04-22"
    assert session.calls[0]["params"]["end_date"] == "2026-04-22"
    assert session.calls[0]["params"]["hourly"] == "precipitation"
