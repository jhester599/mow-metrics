# Mow Metrics Design Spec

**Date:** 2026-04-24

## Goal

Build a lightweight Streamlit application and scheduled automation that help track expected weekly lawn mowing visits, predict whether a mow likely occurred based on weather, and reconcile those predictions with manual confirmation for monthly billing.

## Product Summary

Mow Metrics is an operator-friendly dashboard, not a self-serve SaaS product. In v1, there is no authentication layer. A user can add or update a mowing profile, then select a username and year to review predicted mow events, confirm whether the mow actually happened, and see a current-month confirmed mow count.

The system has two execution surfaces:

- A Streamlit app for setup and reconciliation
- A scheduled Python script run by GitHub Actions for daily prediction logging

Both surfaces share the same Google Sheets-backed data model and business rules where possible.

## Scope

### In Scope for v1

- Setup flow for `Username`, `Calendar Year`, `Zip Code`, and `Expected Mow Day`
- Zip-code-first location model with server-side geocoding to canonical latitude and longitude
- Default mowing season calculation using a latitude-band heuristic
- Storage in Google Sheets with separate configuration and event log tabs
- Daily automation that evaluates only eligible users and only on relevant mow dates
- Rainfall-only mowing prediction
- Duplicate prevention for rerun safety using `Username + Year + Date`
- Manual confirmation workflow in the Streamlit dashboard
- Monthly confirmed mow summary metric
- Deployment-ready repository structure for Streamlit Community Cloud and GitHub Actions

### Out of Scope for v1

- Authentication and multi-tenant access control
- Sophisticated machine-learning or probabilistic prediction models
- Native billing, invoicing, or payment workflows
- Push notifications, SMS, or email alerts
- Complex GIS or agronomy datasets

## Primary Decisions

### Location Input Model

The app will accept zip code input only in v1. During setup, the app will geocode the zip code to latitude and longitude and store all three values:

- Original zip code
- Canonical latitude
- Canonical longitude

This keeps onboarding simple while preserving precise coordinates for weather queries and seasonality heuristics.

### Authentication

There will be no authentication in v1. The Streamlit app will behave like a shared admin or operator dashboard where someone selects a username from stored records.

### Prediction Model

The prediction model will be rainfall-only in v1. If precipitation during typical mowing hours exceeds a configured threshold, the predicted status becomes `Skipped`. Otherwise it becomes `Mowed`.

### Idempotency

The automation must not append duplicate log rows for the same user and expected mow date. The effective uniqueness key is:

- `Username + Year + Date`

## Seasonality Design

### Chosen Approach

The v1 seasonality default will use a latitude-based heuristic derived from the geocoded zip code. This is intentionally lightweight, deterministic, and free to host.

The heuristic will map latitude bands to broad mowing seasons. Example shape:

- Northern climates: later start, earlier end
- Temperate climates: moderate season
- Southern climates: longer season

For the prototype zip code `44236`, the default season must resolve to:

- `Season Start`: `2026-04-01`
- `Season End`: `2026-11-30`

The calculated season is a starting default, not a claim of biological precision.

### Why This Approach

- No paid services required
- Easy to explain in documentation
- Deterministic behavior for testing
- Good enough for a decision-support v1

### Roadmap Candidates

These are explicitly deferred, not part of v1:

- USDA hardiness-zone-based seasonality
- Temperature-aware prediction
- Ground saturation or soil-moisture proxy signals

## Data Model

Google Sheets will act as the persistence layer.

### `Users_Config` Tab

One row per `Username + Active Year`.

Required columns:

- `Username`
- `Active Year`
- `Zip Code`
- `Latitude`
- `Longitude`
- `Expected Mow Day`
- `Season Start`
- `Season End`
- `Created At`
- `Updated At`

### `Log` Tab

One row per predicted mowing event.

Required columns:

- `Username`
- `Year`
- `Date`
- `Expected Day`
- `Zip Code`
- `Latitude`
- `Longitude`
- `Weather Summary`
- `Raw API JSON`
- `Predicted Status`
- `Confirmed Status`
- `Prediction Reason`
- `Created At`
- `Updated At`

Expected status values:

- `Predicted Status`: `Mowed` or `Skipped`
- `Confirmed Status`: `Pending`, `Yes`, or `No`

## Streamlit Application Design

`app.py` will expose two main workflows in one application.

### 1. Setup / User Configuration

The setup view collects:

- `Username`
- `Calendar Year`
- `Zip Code`
- `Expected Mow Day`

When the form is submitted:

1. The app geocodes the zip code to latitude and longitude.
2. The app computes a default season start and end for the selected year.
3. The app writes or updates the matching `Users_Config` row.

Expected behavior:

- If a `Username + Active Year` row already exists, update it rather than inserting a duplicate.
- Show a clear success or error message after save.

### 2. Reconciliation Dashboard

The dashboard allows an operator to:

- Select a username
- Select a year
- Load filtered log data for that user and year
- View predicted mow records in a table
- Update `Pending` rows to `Yes` or `No`
- See a current-month confirmed mow count

Manual confirmation updates must write back to the `Log` tab immediately.

### Monthly Summary Metric

The app will calculate `Total Confirmed Mows This Month` using:

- The selected username
- The selected year
- The current calendar month at runtime
- Rows where `Confirmed Status = Yes`

## Automation Design

`fetch_and_predict.py` will run independently of the Streamlit app and be triggered daily by GitHub Actions.

### Daily Job Flow

For the current runtime date:

1. Read all `Users_Config` rows.
2. Filter to rows where `Active Year` matches the current calendar year.
3. For each active user, check whether today falls inside `Season Start` and `Season End`.
4. If outside the configured season, skip the user.
5. Determine whether yesterday matched the user's `Expected Mow Day`.
6. If not, skip the user.
7. If yes, fetch yesterday's weather from Open-Meteo using stored latitude and longitude.
8. Apply rainfall-only prediction logic.
9. Check whether a `Log` row already exists for `Username + Year + Date`.
10. If no existing row is found, append a new log entry with `Confirmed Status = Pending`.

### Weather Query

The system will use Open-Meteo and request yesterday's precipitation data for the stored coordinates.

The application should preserve:

- A concise human-readable weather summary
- The raw JSON response for auditability and future tuning

### Prediction Rule

The rainfall-only decision rule should be simple and explainable:

- If rainfall during configured working hours is at or above threshold, predict `Skipped`
- Otherwise predict `Mowed`

The reason string saved to the log should briefly explain why the prediction was made.

## Repository Structure

The repository should favor thin entrypoints and reusable modules.

Planned structure:

- `app.py`
- `fetch_and_predict.py`
- `.github/workflows/weather_check.yml`
- `requirements.txt`
- `README.md`
- `src/mow_metrics/config.py`
- `src/mow_metrics/models.py`
- `src/mow_metrics/seasonality.py`
- `src/mow_metrics/sheets.py`
- `src/mow_metrics/weather.py`
- `tests/`

### Responsibility Split

- `app.py` owns Streamlit UI composition
- `fetch_and_predict.py` owns scheduled orchestration
- `config.py` owns environment and settings loading
- `models.py` owns structured record representations and shared constants
- `seasonality.py` owns the latitude-band heuristic
- `sheets.py` owns Google Sheets read and write operations
- `weather.py` owns geocoding and Open-Meteo interactions

## Configuration

The application will use environment variables and Streamlit secrets for:

- Google service account credentials
- Target Google Sheet ID
- Optional precipitation threshold settings
- Optional working-hours settings for rainfall evaluation

Both runtime surfaces must be supported:

- GitHub Actions will provide `GOOGLE_SHEET_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON` as encrypted repository secrets.
- Streamlit Community Cloud will provide equivalent values through Streamlit secrets, which the app can adapt into the same settings object used by the automation script.

The README must document:

- Local setup
- Google Sheets service account setup
- Streamlit Community Cloud secrets
- GitHub Actions secrets configuration

## Testing Strategy

Automated tests should focus on the decision logic and data rules rather than the full UI surface.

Priority coverage:

- Configuration loading for required Google secrets and default prediction settings
- Seasonality heuristic behavior across representative latitude bands
- Prototype default behavior for zip code `44236`
- Zip-code geocoding using mocked HTTP responses
- Open-Meteo archive request construction using mocked HTTP responses
- Duplicate detection for `Username + Year + Date`
- Rainfall-only prediction decisions from sample Open-Meteo payloads
- Google Sheets header initialization and row conversion behavior
- Row update logic for manual confirmation writes
- Automation orchestration decisions for season checks, expected mow day checks, duplicate skipping, and pending log creation
- Dashboard helper behavior for user/year filtering, pending-row selection, setup row construction, and monthly confirmed mow counts

The Streamlit app itself can remain lightly tested in v1 as long as the core services are well covered.

## Risks and Mitigations

### Geocoding Accuracy

Risk: Zip-code geocoding may return a central coordinate rather than the exact mowing site.

Mitigation: This is acceptable for v1 because the tool is advisory, not contractual. Store the canonical lat/lon used so behavior is transparent.

### Weather Simplification

Risk: Rainfall-only logic may misclassify real mowing outcomes.

Mitigation: Preserve raw weather data and prediction reasons, and allow manual confirmation overrides.

### Google Sheets as Database

Risk: Sheets is simple but not strongly transactional.

Mitigation: Keep schemas explicit, use deterministic keys, and make the automation idempotent.

## Success Criteria

The v1 implementation is successful when:

- A new user profile can be created from zip code input
- The system stores lat/lon and computed season dates
- The daily job logs at most one record per user per expected mow date
- The prediction is based on yesterday's rainfall data
- Pending rows can be manually confirmed from the dashboard
- The dashboard shows the current month's confirmed mow count
- The app and automation can be configured from documented secrets and environment variables
