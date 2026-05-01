# Rainfall Timing And Saturation Prediction Design

## Goal

Improve mowing predictions by considering when rain falls, not only how much rain falls during a broad workday window.

## Current Behavior

`predict_mow_status` receives one day of hourly precipitation and sums rainfall from `WORKDAY_START_HOUR` through `WORKDAY_END_HOUR`. If the total exceeds `PRECIPITATION_THRESHOLD_MM`, it predicts `Skipped`; otherwise it predicts `Mowed`.

This treats morning rain and evening rain similarly, even though evening rain often falls after mowing is complete. It also ignores heavy rain the prior evening that can leave the ground saturated.

## New Prediction Rules

The prediction will use two sets of hourly precipitation:

- Previous day precipitation.
- Target mow day precipitation.

Prediction precedence:

1. If previous-day saturation-window rain is at or above `SATURATION_THRESHOLD_MM`, predict `Skipped`.
2. Else if mow-day morning-window rain is at or above `PRECIPITATION_THRESHOLD_MM`, predict `Skipped`.
3. Else if mow-day work-window rain is at or above `PRECIPITATION_THRESHOLD_MM`, predict `Skipped`.
4. Else predict `Mowed`.

Default windows:

- Saturation window: previous day `18:00-23:00`.
- Morning window: mow day `06:00-12:00`.
- Work window: mow day `08:00-17:00`.

Default thresholds:

- `PRECIPITATION_THRESHOLD_MM=0.2`
- `SATURATION_THRESHOLD_MM=5.0`

Mow-day evening/night rainfall after the work window will appear in the summary but will not force a skipped prediction.

## Data Flow

The daily automation and dashboard backfill will fetch weather from the day before the mow date through the mow date. The raw API JSON stored in Google Sheets will include both dates in one Open-Meteo archive payload.

Existing log schema remains unchanged.

## Configuration

Add optional settings:

- `SATURATION_THRESHOLD_MM`
- `SATURATION_START_HOUR`
- `SATURATION_END_HOUR`
- `MOW_DAY_MORNING_START_HOUR`
- `MOW_DAY_MORNING_END_HOUR`

Existing settings remain:

- `PRECIPITATION_THRESHOLD_MM`
- `WORKDAY_START_HOUR`
- `WORKDAY_END_HOUR`

## Testing

Tests will cover:

- Previous evening heavy rain predicts `Skipped`.
- Mow-day morning rain predicts `Skipped`.
- Mow-day evening-only rain predicts `Mowed`.
- Fetching weather includes the prior day and target date.
- Settings load the new optional defaults and overrides.
