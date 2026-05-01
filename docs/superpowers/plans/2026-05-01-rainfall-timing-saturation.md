# Rainfall Timing Saturation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve mow predictions by accounting for prior-night saturation, mow-day morning rain, and late-day rain timing.

**Architecture:** Keep the `Log` schema unchanged. Extend settings with rainfall timing knobs, change weather fetching to request the previous day through the target mow day, and update `predict_mow_status` to accept both previous-day and mow-day hourly precipitation while preserving a compatibility path for existing tests and callers.

**Tech Stack:** Python 3.12+, pytest, requests, Open-Meteo archive API.

---

### Task 1: Settings

**Files:**
- Modify: `src/mow_metrics/config.py`
- Modify: `tests/test_config.py`

- [ ] Add tests proving default saturation and morning-window settings load.
- [ ] Add tests proving env overrides are parsed.
- [ ] Add fields to `Settings` and `load_settings_from_mapping`.
- [ ] Run `python -m pytest tests/test_config.py -v`.

### Task 2: Weather Prediction Rules

**Files:**
- Modify: `src/mow_metrics/weather.py`
- Modify: `tests/test_weather.py`

- [ ] Add tests for previous-night saturation predicting `Skipped`.
- [ ] Add tests for mow-day morning rain predicting `Skipped`.
- [ ] Add tests for evening-only rain predicting `Mowed`.
- [ ] Update `predict_mow_status` to support prior-day and mow-day hourly lists, with precedence matching the design.
- [ ] Update weather summary text to show saturation, morning, workday, and evening rainfall totals.
- [ ] Run `python -m pytest tests/test_weather.py -v`.

### Task 3: Two-Day Fetching Integration

**Files:**
- Modify: `src/mow_metrics/weather.py`
- Modify: `fetch_and_predict.py`
- Modify: `app.py`
- Modify: `tests/test_weather.py`
- Modify: `tests/test_fetch_and_predict.py`

- [ ] Update `fetch_daily_weather` to request previous day through target date.
- [ ] Add an extractor for target-day and previous-day hourly precipitation from multi-day Open-Meteo payloads.
- [ ] Update automation and dashboard backfill to pass previous-day and target-day hourly values to `predict_mow_status`.
- [ ] Run `python -m pytest tests/test_weather.py tests/test_fetch_and_predict.py tests/test_app_logic.py -v`.

### Task 4: Full Verification

**Files:**
- Modify: none expected

- [ ] Run `python -m pytest -v`.
- [ ] Run `python -m py_compile app.py fetch_and_predict.py src/mow_metrics/*.py` using PowerShell-expanded file paths.
- [ ] Review `git diff`.

### Self-Review

The plan covers the approved design: time-of-day buckets, saturation, two-day raw weather payloads, config settings, and tests for the main prediction branches. No placeholders remain.
