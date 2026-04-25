from datetime import date, datetime, timedelta
import json

from mow_metrics.models import CONFIRMED_STATUS_PENDING
from mow_metrics.seasonality import is_date_in_season
from mow_metrics.sheets import build_log_key


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


def main() -> None:
    # The full sheet-backed workflow is wired after the Streamlit app and docs are in place.
    print("Mow Metrics daily prediction helpers loaded.")


if __name__ == "__main__":
    main()
