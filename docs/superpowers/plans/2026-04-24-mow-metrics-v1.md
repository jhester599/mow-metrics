# Mow Metrics V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working version of Mow Metrics: a Streamlit dashboard plus a scheduled prediction script backed by Google Sheets and Open-Meteo.

**Architecture:** The repo will use thin entrypoints (`app.py` and `fetch_and_predict.py`) over a small `src/mow_metrics` package for configuration, seasonality, weather access, and Google Sheets persistence. Business rules live in reusable modules so the app and automation share the same data contracts, prediction logic, and duplicate-prevention behavior.

**Tech Stack:** Python 3.12, Streamlit, pytest, gspread, google-auth, requests, GitHub Actions, Google Sheets API, Open-Meteo API

---

## File Structure

### New files

- `app.py`
- `fetch_and_predict.py`
- `.github/workflows/weather_check.yml`
- `requirements.txt`
- `docs/roadmap.md`
- `src/mow_metrics/__init__.py`
- `src/mow_metrics/config.py`
- `src/mow_metrics/models.py`
- `src/mow_metrics/seasonality.py`
- `src/mow_metrics/weather.py`
- `src/mow_metrics/sheets.py`
- `tests/conftest.py`
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
- Create: `tests/conftest.py`
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

- [ ] **Step 3: Write minimal package, constants, and config implementation**

```python
# src/mow_metrics/models.py
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
```

```python
# src/mow_metrics/config.py
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    google_sheet_id: str
    precipitation_threshold_mm: float = 0.2
    workday_start_hour: int = 8
    workday_end_hour: int = 17


def load_settings() -> Settings:
    return Settings(
        google_sheet_id=os.environ["GOOGLE_SHEET_ID"],
        precipitation_threshold_mm=float(os.getenv("PRECIPITATION_THRESHOLD_MM", "0.2")),
        workday_start_hour=int(os.getenv("WORKDAY_START_HOUR", "8")),
        workday_end_hour=int(os.getenv("WORKDAY_END_HOUR", "17")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_sheets.py -k headers -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/mow_metrics/__init__.py src/mow_metrics/models.py src/mow_metrics/config.py tests/conftest.py tests/test_sheets.py
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
```

- [ ] **Step 4: Expand with a second failing boundary test**

```python
from datetime import date

from mow_metrics.seasonality import derive_season_dates, is_date_in_season


def test_temperate_latitudes_get_longer_season():
    start_date, end_date = derive_season_dates(latitude=36.5, year=2026)
    assert start_date == date(2026, 3, 15)
    assert end_date == date(2026, 12, 15)


def test_is_date_in_season_is_inclusive():
    assert is_date_in_season(date(2026, 4, 1), date(2026, 4, 1), date(2026, 11, 30))
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
from mow_metrics.weather import build_weather_summary, extract_hourly_precipitation


def test_extract_hourly_precipitation_reads_open_meteo_payload():
    payload = {"hourly": {"precipitation": [0.0, 0.1, 0.2]}}
    assert extract_hourly_precipitation(payload) == [0.0, 0.1, 0.2]


def test_build_weather_summary_formats_total_rainfall():
    assert build_weather_summary([0.0, 0.1, 0.2]) == "Daily rainfall: 0.30 mm"
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
from mow_metrics.sheets import upsert_user_config_row


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
from fetch_and_predict import should_append_log_row


def test_should_append_log_row_skips_existing_key():
    existing_keys = {"jeff|2026|2026-04-23"}
    assert not should_append_log_row("jeff", 2026, "2026-04-23", existing_keys)
    assert should_append_log_row("jeff", 2026, "2026-04-30", existing_keys)
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
from app import pending_rows


def test_pending_rows_returns_only_pending_items():
    rows = [
        {"Confirmed Status": "Pending", "Date": "2026-04-09"},
        {"Confirmed Status": "Yes", "Date": "2026-04-16"},
    ]
    assert pending_rows(rows) == [{"Confirmed Status": "Pending", "Date": "2026-04-09"}]
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
git add .github/workflows/weather_check.yml README.md requirements.txt docs/roadmap.md
git commit -m "docs: wire deployment and setup guidance"
```

## Self-Review

### Spec coverage

- Setup flow: covered by Task 6 and shared services in Tasks 1-4
- Latitude-based seasonality and `44236` default: covered by Task 2
- Google Sheets schema and duplicate key behavior: covered by Tasks 1 and 4
- Rainfall-only prediction: covered by Task 3
- Daily GitHub Actions automation: covered by Tasks 5 and 7
- Manual confirmation and monthly summary: covered by Task 6
- Roadmap items for temperature, saturation, and USDA zones: covered by Task 7

### Placeholder scan

- No `TBD`, `TODO`, or deferred implementation placeholders remain inside the tasks.
- Each code-changing step includes concrete file targets and example code.
- Each verification step includes an explicit command and expected result.

### Type consistency

- `Username`, `Year`, `Date`, `Confirmed Status`, and `Expected Mow Day` are used consistently across tests and repository helpers.
- `derive_season_dates`, `predict_mow_status`, `build_log_key`, `should_process_user`, and `count_confirmed_mows_for_month` are introduced before later tasks rely on them.
