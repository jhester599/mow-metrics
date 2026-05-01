# Backfill Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dashboard backfill for historical expected mow dates and editable confirmation statuses.

**Architecture:** Keep the Google Sheet schema unchanged. Add pure helper functions to `app.py` for date generation, missing-row detection, row display shaping, and edited-confirmation detection; reuse `fetch_and_predict.build_log_entry` and the existing weather prediction helpers for row creation.

**Tech Stack:** Python 3.12+, Streamlit, gspread, pytest, Open-Meteo API.

---

### Task 1: Backfill Date Helpers

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app_logic.py`

- [ ] Add tests for generating historical expected mow dates from season start through yesterday, capped by season end.
- [ ] Add tests for detecting missing backfill dates while skipping existing `Username|Year|Date` log keys.
- [ ] Implement `expected_mow_dates`, `find_user_profile`, and `missing_backfill_dates`.
- [ ] Run `python -m pytest tests/test_app_logic.py -v`.

### Task 2: Confirmation Edit Helpers

**Files:**
- Modify: `app.py`
- Modify: `tests/test_app_logic.py`

- [ ] Add tests for detecting changed `Confirmed Status` values by log key.
- [ ] Implement `confirmation_updates`.
- [ ] Run `python -m pytest tests/test_app_logic.py -v`.

### Task 3: Dashboard Backfill Flow

**Files:**
- Modify: `app.py`

- [ ] Import `build_log_entry`, `existing_log_keys`, `extract_hourly_precipitation`, `fetch_daily_weather`, and `predict_mow_status`.
- [ ] In the dashboard tab, compute missing dates for the selected profile.
- [ ] Hide or disable the backfill action when no dates are missing.
- [ ] On button click, fetch weather for missing dates, append pending log rows, and show the number added.
- [ ] Run `python -m pytest tests/test_app_logic.py tests/test_fetch_and_predict.py -v`.

### Task 4: Editable Confirmation Table

**Files:**
- Modify: `app.py`

- [ ] Replace the read-only dataframe plus pending-row radios with `st.data_editor`.
- [ ] Configure `Confirmed Status` as a selectbox column with `Pending`, `Yes`, and `No`.
- [ ] Add a save action that updates changed confirmations through `update_confirmation`.
- [ ] Keep prediction, weather, identity, and timestamp columns read-only.
- [ ] Run `python -m pytest -v`.

### Task 5: Manual JRH 2026 Backfill Verification

**Files:**
- Modify: none expected

- [ ] Start the Streamlit app locally.
- [ ] Use the dashboard with the configured secrets to select `JRH` and `2026`.
- [ ] Click the backfill action if it is available.
- [ ] Confirm the `Log` sheet contains one row for each missing expected mow date from season start through yesterday and does not duplicate the existing row.
- [ ] If local secrets are unavailable, report that manual sheet backfill could not be completed from this workspace.

### Self-Review

The plan covers the spec requirements: duplicate-safe backfill, season-start-through-yesterday generation, complete-state button hiding/disablement, editable confirmation status, and JRH 2026 manual verification. No placeholders remain.
