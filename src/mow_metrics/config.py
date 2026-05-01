from collections.abc import Mapping
from dataclasses import dataclass
import json
import os
from typing import Any


@dataclass(frozen=True)
class Settings:
    google_sheet_id: str
    google_service_account_info: dict[str, Any]
    precipitation_threshold_mm: float = 0.2
    workday_start_hour: int = 8
    workday_end_hour: int = 17
    saturation_threshold_mm: float = 5.0
    saturation_start_hour: int = 18
    saturation_end_hour: int = 23
    mow_day_morning_start_hour: int = 6
    mow_day_morning_end_hour: int = 12


def _load_service_account_json(source: Mapping[str, str]) -> dict[str, Any]:
    raw_json = source.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is required.")
    return json.loads(raw_json)


def load_settings_from_mapping(source: Mapping[str, str]) -> Settings:
    return Settings(
        google_sheet_id=source["GOOGLE_SHEET_ID"],
        google_service_account_info=_load_service_account_json(source),
        precipitation_threshold_mm=float(source.get("PRECIPITATION_THRESHOLD_MM", "0.2")),
        workday_start_hour=int(source.get("WORKDAY_START_HOUR", "8")),
        workday_end_hour=int(source.get("WORKDAY_END_HOUR", "17")),
        saturation_threshold_mm=float(source.get("SATURATION_THRESHOLD_MM", "5.0")),
        saturation_start_hour=int(source.get("SATURATION_START_HOUR", "18")),
        saturation_end_hour=int(source.get("SATURATION_END_HOUR", "23")),
        mow_day_morning_start_hour=int(source.get("MOW_DAY_MORNING_START_HOUR", "6")),
        mow_day_morning_end_hour=int(source.get("MOW_DAY_MORNING_END_HOUR", "12")),
    )


def load_settings() -> Settings:
    return load_settings_from_mapping(os.environ)
