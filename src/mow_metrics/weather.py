from dataclasses import dataclass
from datetime import date, timedelta

import requests

from mow_metrics.models import PREDICTED_STATUS_MOWED, PREDICTED_STATUS_SKIPPED


@dataclass(frozen=True)
class PredictionResult:
    predicted_status: str
    reason: str
    weather_summary: str


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    name: str


def predict_mow_status(
    hourly_precipitation: list[float],
    threshold_mm: float,
    workday_start_hour: int,
    workday_end_hour: int,
    previous_day_hourly_precipitation: list[float] | None = None,
    saturation_threshold_mm: float = 5.0,
    saturation_start_hour: int = 18,
    saturation_end_hour: int = 23,
    morning_start_hour: int = 6,
    morning_end_hour: int = 12,
) -> PredictionResult:
    previous_day_hourly_precipitation = previous_day_hourly_precipitation or [0.0] * 24
    saturation_total = sum(previous_day_hourly_precipitation[saturation_start_hour : saturation_end_hour + 1])
    morning_total = sum(hourly_precipitation[morning_start_hour : morning_end_hour + 1])
    workday_total = sum(hourly_precipitation[workday_start_hour : workday_end_hour + 1])
    evening_total = sum(hourly_precipitation[workday_end_hour + 1 :])
    weather_summary = (
        f"Prior evening rainfall: {saturation_total:.2f} mm; "
        f"morning rainfall: {morning_total:.2f} mm; "
        f"workday rainfall: {workday_total:.2f} mm; "
        f"evening rainfall: {evening_total:.2f} mm"
    )
    if saturation_total >= saturation_threshold_mm:
        return PredictionResult(
            predicted_status=PREDICTED_STATUS_SKIPPED,
            reason=f"Skipped because the ground was likely saturated by {saturation_total:.2f} mm of prior evening rain.",
            weather_summary=weather_summary,
        )
    if morning_total >= threshold_mm:
        return PredictionResult(
            predicted_status=PREDICTED_STATUS_SKIPPED,
            reason=f"Skipped because {morning_total:.2f} mm of rain fell during the mowing-day morning.",
            weather_summary=weather_summary,
        )
    if workday_total >= threshold_mm:
        return PredictionResult(
            predicted_status=PREDICTED_STATUS_SKIPPED,
            reason=f"Skipped because {workday_total:.2f} mm of rain fell during work hours.",
            weather_summary=weather_summary,
        )
    return PredictionResult(
        predicted_status=PREDICTED_STATUS_MOWED,
        reason=(
            f"Mowed because prior evening, morning, and work-hour rainfall stayed below thresholds; "
            f"evening rainfall was {evening_total:.2f} mm and likely fell after mowing."
        ),
        weather_summary=weather_summary,
    )


def extract_hourly_precipitation(payload: dict) -> list[float]:
    return [float(value) for value in payload.get("hourly", {}).get("precipitation", [])]


def extract_hourly_precipitation_for_date(payload: dict, target_date: date) -> list[float]:
    target_prefix = target_date.isoformat()
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    precipitation = hourly.get("precipitation", [])
    return [
        float(value)
        for timestamp, value in zip(times, precipitation)
        if str(timestamp).startswith(target_prefix)
    ]


def build_weather_summary(hourly_precipitation: list[float]) -> str:
    return f"Daily rainfall: {sum(hourly_precipitation):.2f} mm"


def geocode_zip(zip_code: str, session=None) -> GeocodingResult:
    session = session or requests.Session()
    response = session.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": zip_code, "count": 1, "countryCode": "US", "language": "en", "format": "json"},
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        raise ValueError(f"No geocoding result found for zip code {zip_code}.")
    first = results[0]
    return GeocodingResult(
        latitude=float(first["latitude"]),
        longitude=float(first["longitude"]),
        name=str(first.get("name", zip_code)),
    )


def fetch_daily_weather(latitude: float, longitude: float, target_date: date, session=None) -> dict:
    session = session or requests.Session()
    date_text = target_date.isoformat()
    previous_date_text = (target_date - timedelta(days=1)).isoformat()
    response = session.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": previous_date_text,
            "end_date": date_text,
            "hourly": "precipitation",
            "timezone": "auto",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
