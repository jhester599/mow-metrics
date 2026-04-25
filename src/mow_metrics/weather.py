from dataclasses import dataclass
from datetime import date

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
) -> PredictionResult:
    workday_total = sum(hourly_precipitation[workday_start_hour : workday_end_hour + 1])
    if workday_total >= threshold_mm:
        return PredictionResult(
            predicted_status=PREDICTED_STATUS_SKIPPED,
            reason=f"Skipped because {workday_total:.2f} mm of rain fell during work hours.",
            weather_summary=f"Workday rainfall: {workday_total:.2f} mm",
        )
    return PredictionResult(
        predicted_status=PREDICTED_STATUS_MOWED,
        reason=f"Mowed because only {workday_total:.2f} mm of rain fell during work hours.",
        weather_summary=f"Workday rainfall: {workday_total:.2f} mm",
    )


def extract_hourly_precipitation(payload: dict) -> list[float]:
    return [float(value) for value in payload.get("hourly", {}).get("precipitation", [])]


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
    response = session.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "start_date": date_text,
            "end_date": date_text,
            "hourly": "precipitation",
            "timezone": "auto",
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
