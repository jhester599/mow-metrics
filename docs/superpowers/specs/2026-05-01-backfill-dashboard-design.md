# Backfill Dashboard Design

## Goal

Add dashboard support for filling historical mowing prediction rows for a selected user/year, then let the operator confirm mowing outcomes directly in the displayed table.

## Current Behavior

The scheduled GitHub Actions workflow runs `fetch_and_predict.py` once per day. It only evaluates yesterday's expected mow date, predicts whether mowing likely occurred, and appends a pending row to the Google Sheet `Log` tab when no row already exists for `Username + Year + Date`.

The Streamlit dashboard can save user profiles and display selected log rows. It currently updates pending confirmations through separate radio buttons below a read-only dataframe.

## Backfill Behavior

The dashboard will add an on-demand backfill action for the selected user and year.

For the selected profile, the app will generate expected mow dates from the profile's `Season Start` through yesterday. It will include only dates whose weekday matches `Expected Mow Day`, skip dates after `Season End`, and skip log entries that already exist for the same `Username + Year + Date`.

For each missing date, the app will fetch archived Open-Meteo precipitation data, use the same prediction logic as the daily automation, and append a normal pending `Log` row. Existing rows are not modified. This makes the backfill duplicate-safe and consistent with scheduled predictions.

If there are no missing historical dates for the selected profile, the dashboard will not show an active backfill button. It will show a small completion note instead, so the operator can tell the selected user/year is already backfilled.

## Confirmation Editing

The reconciliation table will become editable through `st.data_editor`.

The operator will edit `Confirmed Status` directly in the table using the existing values `Pending`, `Yes`, and `No`. The app will keep prediction and weather columns read-only. A save action will compare edited rows to the original log rows and update only rows whose confirmation changed.

The monthly confirmed mow metric will continue to count rows whose `Confirmed Status` is `Yes`.

## Existing JRH 2026 User

The existing `JRH` / `2026` profile will use the same dashboard backfill path as every other user. When selected, the app will backfill missing expected mow dates from the user's configured season start through yesterday and skip the one existing `Log` row.

## Error Handling

Backfill writes are append-only and duplicate-safe. If a weather request or sheet write fails, Streamlit will surface the exception rather than silently pretending the backfill finished. The operator can rerun the backfill after the issue is fixed; already-created rows will be skipped.

## Testing

Unit tests will cover:

- Historical mow-date generation from season start through yesterday.
- Missing backfill date detection that skips existing log keys.
- Backfill row construction using the same prediction fields as daily automation.
- Confirmation-change detection for editable table rows.
