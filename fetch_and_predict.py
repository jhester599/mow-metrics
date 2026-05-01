from datetime import date, datetime, timedelta, timezone
import json

from mow_metrics.config import load_settings
from mow_metrics.models import CONFIRMED_STATUS_PENDING
from mow_metrics.seasonality import is_date_in_season
from mow_metrics.sheets import (
    append_log_entry,
    build_log_key,
    existing_log_keys,
    get_log_worksheet,
    get_user_config_worksheet,
    open_spreadsheet,
    read_records,
)
from mow_metrics.weather import extract_hourly_precipitation_for_date, fetch_daily_weather, predict_mow_status


def should_process_user(user_row: dict[str, str], today: date) -> bool:
    season_start = datetime.strptime(user_row["Season Start"], "%Y-%m-%d").date()
    season_end = datetime.strptime(user_row["Season End"], "%Y-%m-%d").date()
    if not is_date_in_season(today, season_start, season_end):
        return False

    yesterday = today - timedelta(days=1)
    return yesterday.strftime("%A") == user_row["Expected Mow Day"]


def should_append_log_row(username: str, year: int, mow_date: str, existing_keys: set[str]) -> bool:
    return build_log_key(username, year, mow_date) not in existing_keys


def build_log_entry(
    user_row: dict[str, str],
    mow_date: str,
    weather_summary: str,
    raw_api_json: dict,
    predicted_status: str,
    prediction_reason: str,
    created_at: str,
) -> dict[str, str]:
    return {
        "Username": user_row["Username"],
        "Year": user_row["Active Year"],
        "Date": mow_date,
        "Expected Day": user_row["Expected Mow Day"],
        "Zip Code": user_row["Zip Code"],
        "Latitude": user_row["Latitude"],
        "Longitude": user_row["Longitude"],
        "Weather Summary": weather_summary,
        "Raw API JSON": json.dumps(raw_api_json, sort_keys=True),
        "Predicted Status": predicted_status,
        "Confirmed Status": CONFIRMED_STATUS_PENDING,
        "Prediction Reason": prediction_reason,
        "Created At": created_at,
        "Updated At": created_at,
    }


def process_users(
    user_rows: list[dict[str, str]],
    log_rows: list[dict[str, str]],
    today: date,
    settings,
) -> list[dict[str, str]]:
    keys = existing_log_keys(log_rows)
    entries = []
    for user_row in user_rows:
        if str(user_row.get("Active Year")) != str(today.year):
            continue
        if not should_process_user(user_row, today):
            continue

        mow_date = today - timedelta(days=1)
        mow_date_text = mow_date.isoformat()
        if not should_append_log_row(user_row["Username"], today.year, mow_date_text, keys):
            continue

        weather_payload = fetch_daily_weather(
            latitude=float(user_row["Latitude"]),
            longitude=float(user_row["Longitude"]),
            target_date=mow_date,
        )
        previous_mow_date = mow_date - timedelta(days=1)
        previous_day_hourly_precipitation = extract_hourly_precipitation_for_date(weather_payload, previous_mow_date)
        hourly_precipitation = extract_hourly_precipitation_for_date(weather_payload, mow_date)
        prediction = predict_mow_status(
            hourly_precipitation=hourly_precipitation,
            previous_day_hourly_precipitation=previous_day_hourly_precipitation,
            threshold_mm=settings.precipitation_threshold_mm,
            workday_start_hour=settings.workday_start_hour,
            workday_end_hour=settings.workday_end_hour,
            saturation_threshold_mm=settings.saturation_threshold_mm,
            saturation_start_hour=settings.saturation_start_hour,
            saturation_end_hour=settings.saturation_end_hour,
            morning_start_hour=settings.mow_day_morning_start_hour,
            morning_end_hour=settings.mow_day_morning_end_hour,
        )
        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        entry = build_log_entry(
            user_row=user_row,
            mow_date=mow_date_text,
            weather_summary=prediction.weather_summary,
            raw_api_json=weather_payload,
            predicted_status=prediction.predicted_status,
            prediction_reason=prediction.reason,
            created_at=created_at,
        )
        keys.add(build_log_key(entry["Username"], entry["Year"], entry["Date"]))
        entries.append(entry)
    return entries


def main() -> None:
    settings = load_settings()
    spreadsheet = open_spreadsheet(settings)
    user_worksheet = get_user_config_worksheet(spreadsheet)
    log_worksheet = get_log_worksheet(spreadsheet)
    entries = process_users(
        user_rows=read_records(user_worksheet),
        log_rows=read_records(log_worksheet),
        today=date.today(),
        settings=settings,
    )
    for entry in entries:
        append_log_entry(log_worksheet, entry)
    print(f"Appended {len(entries)} mow prediction rows.")


if __name__ == "__main__":
    main()
