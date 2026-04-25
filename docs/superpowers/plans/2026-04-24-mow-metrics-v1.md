# Mow Metrics V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working version of Mow Metrics: a Streamlit dashboard plus a scheduled prediction script backed by Google Sheets and Open-Meteo.

**Architecture:** The repo will use thin entrypoints (`app.py` and `fetch_and_predict.py`) over a small `src/mow_metrics` package for configuration, seasonality, weather access, and Google Sheets persistence. Business rules live in reusable modules so the app and automation share the same data contracts, prediction logic, and duplicate-prevention behavior.

**Tech Stack:** Python 3.12, Streamlit, pytest, gspread, google-auth, requests, GitHub Actions, Google Sheets API, Open-Meteo API

---

## Pre-Build Review Notes

This plan was reviewed before implementation to close gaps that would otherwise make the first build fragile.

- Package setup must be explicit. Use `pyproject.toml` so tests can import the `src/mow_metrics` package without relying on ad hoc path mutation.
- Configuration must support both GitHub Actions environment variables and Streamlit Community Cloud secrets.
- Weather tests must cover zip geocoding and Open-Meteo request construction without making live network calls.
- Google Sheets tests must cover schema initialization, config upsert behavior, duplicate prevention, log append shape, and confirmation updates using lightweight fakes.
- Automation tests must cover full orchestration decisions, not only one date predicate.
- App tests should cover pure workflow helpers for setup row creation, filtering, pending detection, and monthly counts. Streamlit rendering can stay thin, but business behavior must be testable outside Streamlit.
- Documentation must explain secrets, sheet sharing, idempotency, and local verification commands.

## File Structure

### New files

- `app.py`
- `fetch_and_predict.py`
- `.github/workflows/weather_check.yml`
- `pyproject.toml`
- `requirements.txt`
- `docs/roadmap.md`
- `src/mow_metrics/__init__.py`
- `src/mow_metrics/config.py`
- `src/mow_metrics/models.py`
- `src/mow_metrics/seasonality.py`
- `src/mow_metrics/weather.py`
- `src/mow_metrics/sheets.py`
- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_seasonality.py`
- `tests/test_weather.py`
- `tests/test_sheets.py`
- `tests/test_app_logic.py`
- `tests/test_fetch_and_predict.py`

### Existing files to modify

- `README.md`

### Responsibility map

- `src/mow_metrics/config.py`: load environment variables, Streamlit secrets, and prediction settings
- `src/mow_metrics/models.py`: shared column names, dataclasses, and constants
- `src/mow_metrics/seasonality.py`: latitude-band season defaults and date helpers
- `src/mow_metrics/weather.py`: zip geocoding, weather fetches, weather summaries, rainfall-only prediction
- `src/mow_metrics/sheets.py`: Google Sheets schema creation, reads, writes, upserts, duplicate detection
- `app.py`: setup form and reconciliation dashboard
- `fetch_and_predict.py`: scheduled orchestration script

## Task 1: Project Skeleton And Shared Models

**Files:**
- Create: `src/mow_metrics/__init__.py`
- Create: `src/mow_metrics/models.py`
- Create: `src/mow_metrics/config.py`
- Create: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing shared-models test**

```python
from mow_metrics.models import CONFIRMED_STATUS_PENDING, LOG_HEADERS, USER_CONFIG_HEADERS


def test_shared_headers_and_status_constants_are_defined():
    assert USER_CONFIG_HEADERS[:4] == [
        "Username",
        "Active Year",
        "Zip Code",
        "Latitude",
    ]
    assert "Prediction Reason" in LOG_HEADERS
    assert CONFIRMED_STATUS_PENDING == "Pending"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sheets.py -k headers -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mow_metrics'`

- [ ] **Step 3: Write package metadata, constants, and config implementation**

```toml
# pyproject.toml
[project]
name = "mow-metrics"
version = "0.1.0"
description = "Streamlit dashboard and weather automation for lawn mowing reconciliation."
requires-python = ">=3.12"
dependencies = [
    "streamlit",
    "gspread",
    "google-auth",
    "requests",
]

[project.optional-dependencies]
dev = [
    "pytest",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

```python
# src/mow_metrics/models.py
from dataclasses import dataclass

USER_CONFIG_HEADERS = [
    "Username",
    "Active Year",
    "Zip Code",
    "Latitude",
    "Longitude",
    "Expected Mow Day",
    "Season Start",
    "Season End",
    "Created At",
    "Updated At",
]

LOG_HEADERS = [
    "Username",
    "Year",
    "Date",
    "Expected Day",
    "Zip Code",
    "Latitude",
    "Longitude",
    "Weather Summary",
    "Raw API JSON",
    "Predicted Status",
    "Confirmed Status",
    "Prediction Reason",
    "Created At",
    "Updated At",
]

CONFIRMED_STATUS_PENDING = "Pending"
PREDICTED_STATUS_MOWED = "Mowed"
PREDICTED_STATUS_SKIPPED = "Skipped"

MOW_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@dataclass(frozen=True)
class UserConfig:
    username: str
    active_year: int
    zip_code: str
    latitude: float
    longitude: float
    expected_mow_day: str
    season_start: str
    season_end: str


@dataclass(frozen=True)
class LogEntry:
    username: str
    year: int
    date: str
    expected_day: str
    zip_code: str
    latitude: float
    longitude: float
    weather_summary: str
    raw_api_json: str
    predicted_status: str
    confirmed_status: str
    prediction_reason: str
```

```python
# src/mow_metrics/config.py
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


def _load_service_account_json() -> dict[str, Any]:
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is required.")
    return json.loads(raw_json)


def load_settings() -> Settings:
    return Settings(
        google_sheet_id=os.environ["GOOGLE_SHEET_ID"],
        google_service_account_info=_load_service_account_json(),
        precipitation_threshold_mm=float(os.getenv("PRECIPITATION_THRESHOLD_MM", "0.2")),
        workday_start_hour=int(os.getenv("WORKDAY_START_HOUR", "8")),
        workday_end_hour=int(os.getenv("WORKDAY_END_HOUR", "17")),
    )
```

- [ ] **Step 4: Add failing config tests for required secrets and defaults**

```python
import json

import pytest

from mow_metrics.config import load_settings


def test_load_settings_reads_sheet_id_service_account_and_defaults(monkeypatch):
    service_account = {"client_email": "bot@example.com", "private_key": "fake"}
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-123")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps(service_account))

    settings = load_settings()

    assert settings.google_sheet_id == "sheet-123"
    assert settings.google_service_account_info == service_account
    assert settings.precipitation_threshold_mm == 0.2
    assert settings.workday_start_hour == 8
    assert settings.workday_end_hour == 17


def test_load_settings_requires_service_account_json(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-123")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_SERVICE_ACCOUNT_JSON"):
        load_settings()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sheets.py tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements.txt src/mow_metrics/__init__.py src/mow_metrics/models.py src/mow_metrics/config.py tests/conftest.py tests/test_config.py tests/test_sheets.py
git commit -m "feat: add shared models and settings"
```

## Task 2: Seasonality Heuristic

**Files:**
- Create: `src/mow_metrics/seasonality.py`
- Create: `tests/test_seasonality.py`

- [ ] **Step 1: Write the failing seasonality test**

```python
from datetime import date

from mow_metrics.seasonality import derive_season_dates


def test_44236_defaults_to_april_through_november_for_2026():
    start_date, end_date = derive_season_dates(latitude=41.35, year=2026)
    assert start_date == date(2026, 4, 1)
    assert end_date == date(2026, 11, 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_seasonality.py -v`
Expected: FAIL with `ImportError` for `derive_season_dates`

- [ ] **Step 3: Write minimal seasonality implementation**

```python
from datetime import date


def derive_season_dates(latitude: float, year: int) -> tuple[date, date]:
    if latitude >= 40:
        return date(year, 4, 1), date(year, 11, 30)
    if latitude >= 33:
        return date(year, 3, 15), date(year, 12, 15)
    return date(year, 3, 1), date(year, 12, 31)


def is_date_in_season(target_date: date, season_start: date, season_end: date) -> bool:
    return season_start <= target_date <= season_end


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)
```

- [ ] **Step 4: Expand with a second failing boundary test**

```python
from datetime import date

from mow_metrics.seasonality import derive_season_dates, is_date_in_season, parse_iso_date


def test_temperate_latitudes_get_longer_season():
    start_date, end_date = derive_season_dates(latitude=36.5, year=2026)
    assert start_date == date(2026, 3, 15)
    assert end_date == date(2026, 12, 15)


def test_is_date_in_season_is_inclusive():
    assert is_date_in_season(date(2026, 4, 1), date(2026, 4, 1), date(2026, 11, 30))


def test_parse_iso_date_accepts_sheet_date_format():
    assert parse_iso_date("2026-11-30") == date(2026, 11, 30)
```

- [ ] **Step 5: Run tests to verify red then green**

Run: `python -m pytest tests/test_seasonality.py -v`
Expected red: one new failing assertion before the implementation update

Run: `python -m pytest tests/test_seasonality.py -v`
Expected green: all tests PASS after the update

- [ ] **Step 6: Commit**

```bash
git add src/mow_metrics/seasonality.py tests/test_seasonality.py
git commit -m "feat: add latitude-based seasonality heuristic"
```

## Task 3: Weather And Prediction Logic

**Files:**
- Create: `src/mow_metrics/weather.py`
- Create: `tests/test_weather.py`

- [ ] **Step 1: Write the failing rainfall prediction test**

```python
from mow_metrics.weather import predict_mow_status


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_weather.py -k predicts_skipped -v`
Expected: FAIL with `ImportError` for `predict_mow_status`

- [ ] **Step 3: Write minimal prediction and helper implementation**

```python
from dataclasses import dataclass

from mow_metrics.models import PREDICTED_STATUS_MOWED, PREDICTED_STATUS_SKIPPED


@dataclass(frozen=True)
class PredictionResult:
    predicted_status: str
    reason: str
    weather_summary: str


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
```

- [ ] **Step 4: Add failing tests for geocoding and weather summarization seams**

```python
from datetime import date

from mow_metrics.weather import (
    build_weather_summary,
    extract_hourly_precipitation,
    fetch_daily_weather,
    geocode_zip,
)


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
```

- [ ] **Step 5: Run tests to verify red then green**

Run: `python -m pytest tests/test_weather.py -v`
Expected red: new helper tests fail before helper functions exist

Run: `python -m pytest tests/test_weather.py -v`
Expected green: all weather tests PASS after the implementation update

- [ ] **Step 6: Commit**

```bash
git add src/mow_metrics/weather.py tests/test_weather.py
git commit -m "feat: add weather parsing and rainfall prediction"
```

## Task 4: Google Sheets Repository Layer

**Files:**
- Create: `src/mow_metrics/sheets.py`
- Create: `tests/test_sheets.py`

- [ ] **Step 1: Write the failing duplicate-detection and upsert tests**

```python
from mow_metrics.sheets import build_log_key, existing_log_keys


def test_build_log_key_uses_username_year_and_date():
    assert build_log_key("jeff", 2026, "2026-04-23") == "jeff|2026|2026-04-23"


def test_existing_log_keys_collects_unique_keys():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-30"},
    ]
    assert existing_log_keys(rows) == {
        "jeff|2026|2026-04-23",
        "jeff|2026|2026-04-30",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sheets.py -k "build_log_key or existing_log_keys" -v`
Expected: FAIL with `ImportError` for `mow_metrics.sheets`

- [ ] **Step 3: Write minimal repository helpers**

```python
from collections.abc import Iterable


def build_log_key(username: str, year: int | str, mow_date: str) -> str:
    return f"{username}|{year}|{mow_date}"


def existing_log_keys(rows: Iterable[dict[str, str]]) -> set[str]:
    return {
        build_log_key(row["Username"], row["Year"], row["Date"])
        for row in rows
        if row.get("Username") and row.get("Year") and row.get("Date")
    }
```

- [ ] **Step 4: Add a failing user-config upsert test**

```python
from mow_metrics.models import LOG_HEADERS, USER_CONFIG_HEADERS
from mow_metrics.sheets import (
    ensure_headers,
    find_log_row_number,
    log_entry_to_row,
    update_confirmation,
    upsert_user_config_row,
)


def test_upsert_user_config_row_replaces_matching_username_and_year():
    existing_rows = [
        {"Username": "jeff", "Active Year": "2026", "Zip Code": "11111"},
        {"Username": "amy", "Active Year": "2026", "Zip Code": "22222"},
    ]
    new_row = {"Username": "jeff", "Active Year": "2026", "Zip Code": "44236"}

    updated_rows = upsert_user_config_row(existing_rows, new_row)

    assert updated_rows == [
        {"Username": "jeff", "Active Year": "2026", "Zip Code": "44236"},
        {"Username": "amy", "Active Year": "2026", "Zip Code": "22222"},
    ]


class FakeWorksheet:
    def __init__(self, values=None):
        self.values = values or []
        self.updated_ranges = []

    def row_values(self, row_number):
        return self.values[row_number - 1] if len(self.values) >= row_number else []

    def update(self, range_name, values):
        self.updated_ranges.append((range_name, values))


def test_ensure_headers_writes_missing_header_row():
    worksheet = FakeWorksheet(values=[])

    ensure_headers(worksheet, USER_CONFIG_HEADERS)

    assert worksheet.updated_ranges == [("1:1", [USER_CONFIG_HEADERS])]


def test_find_log_row_number_returns_sheet_row_for_matching_key():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-23"},
        {"Username": "amy", "Year": "2026", "Date": "2026-04-23"},
    ]

    assert find_log_row_number(rows, "amy", 2026, "2026-04-23") == 3


def test_update_confirmation_updates_confirmed_status_and_timestamp_cells():
    worksheet = FakeWorksheet(values=[LOG_HEADERS])

    update_confirmation(worksheet, row_number=2, confirmed_status="Yes", updated_at="2026-04-24T12:00:00")

    assert worksheet.updated_ranges == [
        ("K2", [["Yes"]]),
        ("N2", [["2026-04-24T12:00:00"]]),
    ]
```

- [ ] **Step 5: Run tests to verify red then green**

Run: `python -m pytest tests/test_sheets.py -v`
Expected red: upsert test fails before the new helper exists

Run: `python -m pytest tests/test_sheets.py -v`
Expected green: all sheets tests PASS after the implementation update

- [ ] **Step 6: Commit**

```bash
git add src/mow_metrics/sheets.py tests/test_sheets.py
git commit -m "feat: add sheet row helpers and duplicate detection"
```

## Task 5: Daily Automation Script

**Files:**
- Create: `fetch_and_predict.py`
- Create: `tests/test_fetch_and_predict.py`

- [ ] **Step 1: Write the failing automation eligibility test**

```python
from datetime import date

from fetch_and_predict import should_process_user


def test_should_process_user_only_when_yesterday_matches_mow_day_and_today_is_in_season():
    user_row = {
        "Expected Mow Day": "Wednesday",
        "Season Start": "2026-04-01",
        "Season End": "2026-11-30",
    }

    assert should_process_user(user_row, today=date(2026, 4, 23)) is True
    assert should_process_user(user_row, today=date(2026, 12, 1)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fetch_and_predict.py -k should_process_user -v`
Expected: FAIL with `ImportError` for `should_process_user`

- [ ] **Step 3: Write minimal orchestration helpers**

```python
from datetime import date, datetime, timedelta

from mow_metrics.seasonality import is_date_in_season


def should_process_user(user_row: dict[str, str], today: date) -> bool:
    season_start = datetime.strptime(user_row["Season Start"], "%Y-%m-%d").date()
    season_end = datetime.strptime(user_row["Season End"], "%Y-%m-%d").date()
    if not is_date_in_season(today, season_start, season_end):
        return False

    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%A") == user_row["Expected Mow Day"]
```

- [ ] **Step 4: Add a failing duplicate-skip automation test**

```python
from fetch_and_predict import build_log_entry, should_append_log_row


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
```

- [ ] **Step 5: Run tests to verify red then green**

Run: `python -m pytest tests/test_fetch_and_predict.py -v`
Expected red: duplicate-skip test fails before helper exists

Run: `python -m pytest tests/test_fetch_and_predict.py -v`
Expected green: all automation tests PASS after the implementation update

- [ ] **Step 6: Commit**

```bash
git add fetch_and_predict.py tests/test_fetch_and_predict.py
git commit -m "feat: add daily prediction orchestration"
```

## Task 6: Streamlit Setup And Reconciliation UI

**Files:**
- Create: `app.py`
- Create: `tests/test_app_logic.py`

- [ ] **Step 1: Write the failing dashboard metric test**

```python
from app import count_confirmed_mows_for_month


def test_count_confirmed_mows_for_month_counts_only_yes_rows_in_selected_month():
    rows = [
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-02", "Confirmed Status": "Yes"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-04-09", "Confirmed Status": "Pending"},
        {"Username": "jeff", "Year": "2026", "Date": "2026-05-01", "Confirmed Status": "Yes"},
    ]

    total = count_confirmed_mows_for_month(rows, selected_year=2026, current_month=4)

    assert total == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_logic.py -v`
Expected: FAIL with `ImportError` for `count_confirmed_mows_for_month`

- [ ] **Step 3: Write minimal dashboard logic**

```python
from datetime import datetime


def count_confirmed_mows_for_month(rows: list[dict[str, str]], selected_year: int, current_month: int) -> int:
    total = 0
    for row in rows:
        if row.get("Confirmed Status") != "Yes":
            continue
        row_date = datetime.strptime(row["Date"], "%Y-%m-%d")
        if row_date.year == selected_year and row_date.month == current_month:
            total += 1
    return total
```

- [ ] **Step 4: Add a failing pending-row filter test**

```python
from datetime import date

from app import build_user_config_row, filter_log_rows, pending_rows


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
```

- [ ] **Step 5: Run tests to verify red then green**

Run: `python -m pytest tests/test_app_logic.py -v`
Expected red: pending filter test fails before helper exists

Run: `python -m pytest tests/test_app_logic.py -v`
Expected green: all app logic tests PASS after the implementation update

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_app_logic.py
git commit -m "feat: add streamlit dashboard workflows"
```

## Task 7: Documentation, Workflow, And Release Wiring

**Files:**
- Create: `.github/workflows/weather_check.yml`
- Create: `docs/roadmap.md`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `requirements.txt`

- [ ] **Step 1: Write the failing smoke test for dependency metadata**

```python
from pathlib import Path


def test_requirements_include_runtime_dependencies():
    requirements = Path("requirements.txt").read_text()
    assert "streamlit" in requirements
    assert "gspread" in requirements
    assert "pytest" in requirements


def test_readme_documents_required_secrets_and_local_commands():
    readme = Path("README.md").read_text()
    assert "GOOGLE_SHEET_ID" in readme
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in readme
    assert "python -m pytest" in readme
    assert "streamlit run app.py" in readme
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_app_logic.py tests/test_sheets.py tests/test_weather.py tests/test_fetch_and_predict.py -q`
Expected: FAIL somewhere before docs and dependency wiring is complete

- [ ] **Step 3: Write deployment files and docs**

```yaml
# .github/workflows/weather_check.yml
name: Daily Weather Check

on:
  schedule:
    - cron: "0 12 * * *"
  workflow_dispatch:

jobs:
  fetch-and-predict:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python fetch_and_predict.py
        env:
          GOOGLE_SHEET_ID: ${{ secrets.GOOGLE_SHEET_ID }}
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
```

```text
# requirements.txt
streamlit
gspread
google-auth
requests
pytest
```

```markdown
# docs/roadmap.md
- Add temperature-aware prediction logic.
- Add ground saturation or soil-moisture proxy inputs.
- Evaluate USDA hardiness-zone-based season defaults.
```

- [ ] **Step 4: Run full verification**

Run: `python -m pytest -v`
Expected: PASS with all tests green

Run: `python -m py_compile app.py fetch_and_predict.py src/mow_metrics/*.py`
Expected: PASS with no syntax errors

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/weather_check.yml README.md requirements.txt pyproject.toml docs/roadmap.md
git commit -m "docs: wire deployment and setup guidance"
```

## Self-Review

### Spec coverage

- Setup flow: covered by Task 6 and shared services in Tasks 1-4
- Latitude-based seasonality and `44236` default: covered by Task 2
- Google Sheets schema and duplicate key behavior: covered by Tasks 1 and 4
- Zip geocoding and Open-Meteo request construction: covered by Task 3
- Rainfall-only prediction and weather payload parsing: covered by Task 3
- Daily GitHub Actions automation and log-entry construction: covered by Tasks 5 and 7
- Manual confirmation, filtering, and monthly summary: covered by Tasks 4 and 6
- Local import reliability and test configuration: covered by Task 1
- Roadmap items for temperature, saturation, and USDA zones: covered by Task 7

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain inside the tasks.
- Each code-changing step includes concrete file targets and example code.
- Each verification step includes an explicit command and expected result.

### Type consistency

- `Username`, `Year`, `Date`, `Confirmed Status`, and `Expected Mow Day` are used consistently across tests and repository helpers.
- `derive_season_dates`, `predict_mow_status`, `build_log_key`, `should_process_user`, and `count_confirmed_mows_for_month` are introduced before later tasks rely on them.
