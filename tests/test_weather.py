from datetime import date

from mow_metrics.weather import (
    build_weather_summary,
    extract_daily_temperature_min,
    extract_daily_wind_gust_max,
    extract_extended_prior_precipitation,
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
    assert session.calls[0]["params"]["start_date"] == "2026-04-20"
    assert session.calls[0]["params"]["end_date"] == "2026-04-22"
    assert session.calls[0]["params"]["hourly"] == "precipitation"
    assert "temperature_2m_min" in session.calls[0]["params"]["daily"]
    assert "wind_gusts_10m_max" in session.calls[0]["params"]["daily"]


def test_extract_daily_temperature_min_reads_matching_day():
    payload = {
        "daily": {
            "time": ["2026-04-20", "2026-04-21", "2026-04-22"],
            "temperature_2m_min": [3.0, 7.5, 12.0],
        }
    }
    assert extract_daily_temperature_min(payload, date(2026, 4, 21)) == 7.5
    assert extract_daily_temperature_min(payload, date(2026, 4, 23)) is None


def test_extract_daily_wind_gust_max_reads_matching_day():
    payload = {
        "daily": {
            "time": ["2026-04-20", "2026-04-21", "2026-04-22"],
            "wind_gusts_10m_max": [20.0, 65.0, 15.0],
        }
    }
    assert extract_daily_wind_gust_max(payload, date(2026, 4, 21)) == 65.0
    assert extract_daily_wind_gust_max(payload, date(2026, 4, 23)) is None


def test_extract_extended_prior_precipitation_sums_two_prior_days():
    payload = {
        "hourly": {
            "time": [f"2026-04-20T{h:02d}:00" for h in range(24)]
            + [f"2026-04-21T{h:02d}:00" for h in range(24)]
            + [f"2026-04-22T{h:02d}:00" for h in range(24)],
            "precipitation": [0.0] * 20 + [8.0] + [0.0] * 3
            + [0.0] * 20 + [4.0] + [0.0] * 3
            + [0.0] * 24,
        }
    }
    result = extract_extended_prior_precipitation(payload, date(2026, 4, 22))
    assert len(result) == 48
    assert abs(sum(result) - 12.0) < 0.001


def test_predicts_skipped_on_low_temperature():
    result = predict_mow_status(
        hourly_precipitation=[0.0] * 24,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        min_temperature_c=3.5,
        min_temperature_threshold_c=5.0,
    )
    assert result.predicted_status == "Skipped"
    assert "3.5°C" in result.reason
    assert "min temp: 3.5°C" in result.weather_summary


def test_predicts_skipped_on_high_wind():
    result = predict_mow_status(
        hourly_precipitation=[0.0] * 24,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        max_wind_gust_kmh=75.0,
        max_wind_gust_threshold_kmh=60.0,
    )
    assert result.predicted_status == "Skipped"
    assert "75.0 km/h" in result.reason


def test_predicts_mowed_when_wind_below_threshold():
    result = predict_mow_status(
        hourly_precipitation=[0.0] * 24,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        max_wind_gust_kmh=40.0,
        max_wind_gust_threshold_kmh=60.0,
    )
    assert result.predicted_status == "Mowed"


def test_predicts_skipped_on_extended_saturation():
    extended = [0.0] * 40 + [8.0] * 8
    result = predict_mow_status(
        hourly_precipitation=[0.0] * 24,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        extended_prior_precipitation=extended,
        extended_saturation_threshold_mm=15.0,
    )
    assert result.predicted_status == "Skipped"
    assert "64.00 mm" in result.reason
    assert "48h prior rainfall" in result.weather_summary


def test_temperature_check_takes_precedence_over_rain_checks():
    mow_day = [0.0] * 24
    mow_day[9] = 5.0
    result = predict_mow_status(
        hourly_precipitation=mow_day,
        threshold_mm=0.2,
        workday_start_hour=8,
        workday_end_hour=17,
        min_temperature_c=2.0,
        min_temperature_threshold_c=5.0,
    )
    assert result.predicted_status == "Skipped"
    assert "temperature" in result.reason
