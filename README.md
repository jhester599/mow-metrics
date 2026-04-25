# mow-metrics

A lightweight Streamlit dashboard and GitHub Actions automation for weekly lawn mowing reconciliation.

Mow Metrics stores user mowing profiles in Google Sheets, checks Open-Meteo rainfall data after expected mow days, predicts whether the mow likely happened, and lets an operator confirm pending rows for monthly billing.

## Repository Layout

- `app.py`: Streamlit setup and reconciliation dashboard.
- `fetch_and_predict.py`: Daily automation script for GitHub Actions.
- `src/mow_metrics/`: Shared config, weather, seasonality, and Google Sheets helpers.
- `.github/workflows/weather_check.yml`: Daily scheduled prediction workflow.
- `tests/`: Unit tests for core decision logic and setup documentation.

## Google Sheet Setup

Create a Google Sheet with access granted to a Google Cloud service account. The application will create or update these tabs as needed:

- `Users_Config`
- `Log`

Share the sheet with the service account `client_email` using editor access.

## Required Secrets

Set these values for both GitHub Actions and Streamlit Community Cloud:

- `GOOGLE_SHEET_ID`: The spreadsheet ID from the Google Sheets URL.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: The full service account JSON object as a single JSON string.

Optional settings:

- `PRECIPITATION_THRESHOLD_MM`: Rainfall threshold for predicting a skipped mow. Defaults to `0.2`.
- `WORKDAY_START_HOUR`: First hour included in mowing-day rainfall checks. Defaults to `8`.
- `WORKDAY_END_HOUR`: Last hour included in mowing-day rainfall checks. Defaults to `17`.

## Local Development

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run tests:

```powershell
python -m pytest -v
```

Run the Streamlit app:

```powershell
streamlit run app.py
```

For local app testing, provide secrets through environment variables or `.streamlit/secrets.toml`. Do not commit local secrets.

## GitHub Actions

Add repository secrets:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`

The workflow runs daily at 12:00 UTC and can also be triggered manually from the Actions tab.

## Streamlit Community Cloud

Deploy the repository as a Streamlit app with `app.py` as the entrypoint. Add the same Google secrets in Streamlit's app settings before launching the dashboard.

## Seasonality Logic

The v1 seasonality rule uses latitude bands derived from zip-code geocoding. For zip code `44236`, the default mowing season is April 1 through November 30.

## Idempotency

Automation runs are duplicate-safe. The effective log key is `Username + Year + Date`, so rerunning the daily workflow will not append duplicate rows for the same expected mow date.
