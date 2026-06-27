# Prediction Improvement Plan

**Date:** 2026-06-27

## Goal

Improve prediction accuracy by adding an accuracy dashboard, expanding weather signals, extending the saturation lookback window, and providing data-driven threshold tuning based on actual confirmed outcomes.

## Background

The v1 prediction model is rainfall-only and purely rule-based. It never learns from operator confirmations. When a confirmed outcome disagrees with a prediction, that signal is stored but unused. This plan addresses that gap across four implemented phases and one pending phase.

---

## Phase 1 — Accuracy Dashboard (Implemented)

**What:** Add an "Accuracy" tab to the Streamlit dashboard that compares `Predicted Status` vs `Confirmed Status` for all non-Pending rows.

**Metrics shown:**
- Total confirmed rows for the selected user/year
- Overall accuracy % (predicted == confirmed)
- False positive count and rate (predicted Mowed, confirmed Skipped)
- False negative count and rate (predicted Skipped, confirmed Mowed)
- Monthly accuracy breakdown table

**Why:** Without measurement there is no baseline. This tab turns the existing confirmation data into a feedback signal and reveals whether the model skews toward over-predicting Mowed or Skipped.

**Files changed:**
- `app.py` — `compute_accuracy_metrics()`, accuracy tab in `main()`

---

## Phase 2 — Temperature and Wind Signals (Implemented)

**What:** Extend `fetch_daily_weather` to fetch daily `temperature_2m_min` and `wind_gusts_10m_max` from the Open-Meteo Archive API alongside existing hourly precipitation. Incorporate these into `predict_mow_status`.

**New prediction checks (evaluated before rain checks):**
- If `min_temperature_c < min_temperature_threshold_c` (default 5°C) → predict Skipped
- If `max_wind_gust_kmh > max_wind_gust_threshold_kmh` (default 60 km/h) → predict Skipped (evaluated after rain checks)

**Why:** Rain is not the only reason mowing is skipped. Cold temperatures (<5°C) make grass dormant and mowing impractical. Extreme wind gusts (>60 km/h) are a safety concern for equipment operators. Both signals are available in the same Open-Meteo API call at no additional cost.

**New config settings (all env-var configurable):**
- `MIN_TEMPERATURE_THRESHOLD_C` (default `5.0`)
- `MAX_WIND_GUST_THRESHOLD_KMH` (default `60.0`)

**Files changed:**
- `src/mow_metrics/config.py` — two new settings
- `src/mow_metrics/weather.py` — updated fetch, new extractors, updated prediction logic
- `fetch_and_predict.py` — pass new signals to `predict_mow_status`
- `app.py` — pass new signals in `build_backfill_entries`

---

## Phase 3 — Extended 48-Hour Saturation Lookback (Implemented)

**What:** Extend `fetch_daily_weather` to fetch 3 days of data instead of 2. Add an extended saturation check that sums hourly precipitation from the 48 hours before the mow day and compares it to a configurable threshold.

**New prediction check (evaluated before the existing 6-hour evening saturation check):**
- If total precipitation over the 48 hours prior to the mow day >= `extended_saturation_threshold_mm` (default 15.0 mm) → predict Skipped

**Why:** Soil saturation persists longer than one evening. A heavy rain on Tuesday (>15mm over two prior days) can leave the ground too wet for a Thursday mow even if Tuesday evening's 6-hour window was below the 5mm threshold. The existing check misses multi-day soaking events entirely.

**New config setting:**
- `EXTENDED_SATURATION_THRESHOLD_MM` (default `15.0`)

**Files changed:**
- `src/mow_metrics/config.py` — one new setting
- `src/mow_metrics/weather.py` — updated fetch start date, new `extract_extended_prior_precipitation()`
- `fetch_and_predict.py` — extract and pass extended precip
- `app.py` — extract and pass extended precip in backfill

---

## Phase 4 — Data-Driven Threshold Tuning (Implemented)

**What:** Add a threshold tuning analysis to the Accuracy tab. For each user/year with enough confirmed rows (minimum 3), parse the stored `Weather Summary` strings to extract rainfall window totals, then grid-search precipitation and saturation thresholds to find the combination that would have maximized accuracy on the confirmed history.

**Output shown in UI:**
- Suggested `precipitation_threshold_mm` and `saturation_threshold_mm`
- Projected accuracy at suggested thresholds vs current thresholds
- Sample size used for tuning

**Why:** The default thresholds (0.2mm workday, 5.0mm saturation) are sensible starting points but are not calibrated to any specific operator's real behavior or location. After a season of confirmed data, the tuning tool surfaces better values that the operator can apply via environment variables.

**Files changed:**
- `app.py` — `parse_weather_summary_values()`, `_simulate_prediction_from_summary()`, `compute_optimal_thresholds()`, threshold section in accuracy tab

---

## Phase 5 — Consecutive-Skip Pattern and Confidence Scoring (PENDING)

**Status:** Pending. Not yet implemented.

**Why deferred:** Requires more confirmed history to be meaningful. Consecutive-skip detection is most useful after a full season of data; confidence scoring benefits from having Phases 2–4 running for at least a few weeks so the new signals populate new log rows.

### 5a — Consecutive-Skip Pattern Awareness

**What:** If an operator has confirmed Skipped for 2 or more consecutive expected mow dates, lower the effective threshold for the following week's prediction. Repeated confirmed skips may indicate a service suspension or extended equipment issue that weather data cannot detect.

**Approach:**
- Count confirmed-Skipped streak from confirmation history before the current prediction date
- If streak >= 2, apply a multiplier (e.g. 0.5×) to precipitation thresholds for that prediction
- Store streak count in the prediction reason string for transparency

**Risk:** Could produce false negatives if a true weather skip happens to follow a legitimate confirmed skip.

### 5b — Prediction Confidence Score

**What:** Instead of a binary Mowed/Skipped, compute and store a 0–100 confidence score representing how far each rainfall total is from its threshold. Low-confidence predictions (values near threshold boundaries) get a visual flag in the dashboard.

**Approach:**
- For each check that fires, confidence = `min(1.0, ratio_of_rainfall_to_threshold) * 100`
- For a Mowed prediction, confidence = `min(distance_to_nearest_threshold / threshold) * 100`
- Store in a new `Prediction Confidence` log column (requires schema migration)

**Schema change needed:** Add `Prediction Confidence` column to the Log tab header and `LogEntry` dataclass. Existing rows would have empty values.

**Risk:** Schema changes to Google Sheets require careful migration to avoid breaking existing log reads. Should be implemented with a header-version guard.

### 5c — Season-Edge Dampening

**What:** Within a configurable buffer window near `Season Start` and `Season End` (default 2 weeks), apply a stricter prediction threshold. Operators tend to skip marginal weeks at the edges of the season even without significant rain.

**Approach:**
- Check if the mow date falls within `season_start + buffer` or `season_end - buffer`
- If so, halve the effective precipitation threshold for that prediction
- Log the dampening reason in `Prediction Reason`

**Config setting needed:** `SEASON_EDGE_BUFFER_DAYS` (default `14`)
