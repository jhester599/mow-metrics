from datetime import date, datetime, timedelta, timezone
import json

from mow_metrics.config import load_settings_from_mapping
from mow_metrics.models import (
    CONFIRMED_STATUS_MOWED,
    CONFIRMED_STATUS_PENDING,
    CONFIRMED_STATUS_SKIPPED,
    MOW_DAYS,
)
from mow_metrics.seasonality import derive_season_dates
from mow_metrics.sheets import (
    append_log_entry,
    find_log_row_number,
    get_log_worksheet,
    get_user_config_worksheet,
    open_spreadsheet,
    read_records,
    save_user_config,
    update_confirmation,
)
from mow_metrics.weather import (
    extract_hourly_precipitation,
    fetch_daily_weather,
    geocode_zip,
    predict_mow_status,
)
from fetch_and_predict import build_log_entry


def count_confirmed_mows_for_month(rows: list[dict[str, str]], selected_year: int, current_month: int) -> int:
    total = 0
    for row in rows:
        if normalize_confirmed_status(row.get("Confirmed Status", "")) != CONFIRMED_STATUS_MOWED:
            continue
        row_date = datetime.strptime(row["Date"], "%Y-%m-%d")
        if row_date.year == selected_year and row_date.month == current_month:
            total += 1
    return total


def pending_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Confirmed Status") == "Pending"]


def normalize_confirmed_status(status: str) -> str:
    return {
        "Yes": CONFIRMED_STATUS_MOWED,
        "No": CONFIRMED_STATUS_SKIPPED,
    }.get(status, status)


def status_fill_color(status: str) -> str:
    normalized = normalize_confirmed_status(status)
    if normalized == CONFIRMED_STATUS_MOWED:
        return "background-color: #d9ead3"
    if normalized == CONFIRMED_STATUS_SKIPPED:
        return "background-color: #f4cccc"
    return ""


def display_log_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    display_rows = []
    for row in rows:
        display_row = {
            key: normalize_confirmed_status(value) if key == "Confirmed Status" else value
            for key, value in row.items()
            if key != "Raw API JSON"
        }
        display_row["Set Confirmed Status"] = display_row.get("Confirmed Status", CONFIRMED_STATUS_PENDING)
        display_rows.append(display_row)
    return display_rows


def filter_log_rows(rows: list[dict[str, str]], username: str, year: int) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("Username") == username and str(row.get("Year")) == str(year)
    ]


def sort_log_rows_by_date(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: datetime.strptime(row["Date"], "%Y-%m-%d"))


def find_user_profile(rows: list[dict[str, str]], username: str, year: int) -> dict[str, str] | None:
    for row in rows:
        if row.get("Username") == username and str(row.get("Active Year")) == str(year):
            return row
    return None


def expected_mow_dates(
    season_start: date,
    season_end: date,
    expected_mow_day: str,
    today: date,
) -> list[date]:
    end_date = min(season_end, today - timedelta(days=1))
    if end_date < season_start:
        return []

    dates = []
    current = season_start
    while current <= end_date:
        if current.strftime("%A") == expected_mow_day:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def missing_backfill_dates(
    user_row: dict[str, str],
    log_rows: list[dict[str, str]],
    today: date,
) -> list[date]:
    from mow_metrics.sheets import build_log_key, existing_log_keys

    existing_keys = existing_log_keys(log_rows)
    username = str(user_row["Username"])
    year = str(user_row["Active Year"])
    dates = expected_mow_dates(
        season_start=datetime.strptime(user_row["Season Start"], "%Y-%m-%d").date(),
        season_end=datetime.strptime(user_row["Season End"], "%Y-%m-%d").date(),
        expected_mow_day=str(user_row["Expected Mow Day"]),
        today=today,
    )
    return [
        mow_date
        for mow_date in dates
        if build_log_key(username, year, mow_date.isoformat()) not in existing_keys
    ]


def confirmation_updates(
    original_rows: list[dict[str, str]],
    edited_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    from mow_metrics.sheets import build_log_key

    original_by_key = {
        build_log_key(row.get("Username", ""), row.get("Year", ""), row.get("Date", "")): row
        for row in original_rows
    }
    updates = []
    for row in edited_rows:
        key = build_log_key(row.get("Username", ""), row.get("Year", ""), row.get("Date", ""))
        original = original_by_key.get(key)
        if not original:
            continue
        edited_status = normalize_confirmed_status(
            row.get("Set Confirmed Status", row.get("Confirmed Status", ""))
        )
        original_status = normalize_confirmed_status(original.get("Confirmed Status", ""))
        if edited_status != original_status:
            row["Confirmed Status"] = edited_status
            updates.append(row)
    return updates


def build_backfill_entries(
    user_row: dict[str, str],
    missing_dates: list[date],
    settings,
    created_at: str,
) -> list[dict[str, str]]:
    entries = []
    for mow_date in missing_dates:
        weather_payload = fetch_daily_weather(
            latitude=float(user_row["Latitude"]),
            longitude=float(user_row["Longitude"]),
            target_date=mow_date,
        )
        hourly_precipitation = extract_hourly_precipitation(weather_payload)
        prediction = predict_mow_status(
            hourly_precipitation=hourly_precipitation,
            threshold_mm=settings.precipitation_threshold_mm,
            workday_start_hour=settings.workday_start_hour,
            workday_end_hour=settings.workday_end_hour,
        )
        entries.append(
            build_log_entry(
                user_row=user_row,
                mow_date=mow_date.isoformat(),
                weather_summary=prediction.weather_summary,
                raw_api_json=weather_payload,
                predicted_status=prediction.predicted_status,
                prediction_reason=prediction.reason,
                created_at=created_at,
            )
        )
    return entries


def build_user_config_row(
    username: str,
    active_year: int,
    zip_code: str,
    latitude: float,
    longitude: float,
    expected_mow_day: str,
    season_start: date,
    season_end: date,
    timestamp: str,
) -> dict[str, str]:
    return {
        "Username": username,
        "Active Year": str(active_year),
        "Zip Code": zip_code,
        "Latitude": f"{latitude:.2f}",
        "Longitude": f"{longitude:.2f}",
        "Expected Mow Day": expected_mow_day,
        "Season Start": season_start.isoformat(),
        "Season End": season_end.isoformat(),
        "Created At": timestamp,
        "Updated At": timestamp,
    }


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Mow Metrics", page_icon="M", layout="wide")
    st.title("Mow Metrics")
    st.caption("Weekly mowing prediction and billing reconciliation.")

    settings, settings_error = _load_streamlit_settings(st)
    if not settings:
        st.warning("Add Google Sheets secrets to enable the dashboard.")
        if settings_error:
            st.caption(f"Secret loading detail: {settings_error}")
        return

    spreadsheet = open_spreadsheet(settings)
    user_worksheet = get_user_config_worksheet(spreadsheet)
    log_worksheet = get_log_worksheet(spreadsheet)
    user_rows = read_records(user_worksheet)
    log_rows = read_records(log_worksheet)

    tab_setup, tab_dashboard = st.tabs(["Setup", "Dashboard"])
    with tab_setup:
        st.subheader("User Configuration")
        with st.form("user-config"):
            username = st.text_input("Username")
            active_year = st.number_input("Calendar Year", min_value=2024, max_value=2100, value=datetime.now().year)
            zip_code = st.text_input("Zip Code")
            expected_mow_day = st.selectbox("Expected Mow Day", MOW_DAYS)
            submitted = st.form_submit_button("Save profile")

        if submitted:
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            location = geocode_zip(zip_code)
            season_start, season_end = derive_season_dates(location.latitude, int(active_year))
            save_user_config(
                user_worksheet,
                build_user_config_row(
                    username=username,
                    active_year=int(active_year),
                    zip_code=zip_code,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    expected_mow_day=expected_mow_day,
                    season_start=season_start,
                    season_end=season_end,
                    timestamp=timestamp,
                ),
            )
            st.success("Profile saved.")

    with tab_dashboard:
        st.subheader("Reconciliation")
        usernames = sorted({str(row.get("Username")) for row in user_rows if row.get("Username")})
        if not usernames:
            st.info("Add a user profile to start tracking mowing activity.")
            return
        username = st.selectbox("Username", usernames)
        years = sorted({int(row.get("Active Year")) for row in user_rows if row.get("Username") == username})
        selected_year = st.selectbox("Year", years)
        selected_profile = find_user_profile(user_rows, username=username, year=selected_year)
        selected_rows = sort_log_rows_by_date(filter_log_rows(log_rows, username=username, year=selected_year))
        st.metric(
            "Total Confirmed Mows This Month",
            count_confirmed_mows_for_month(selected_rows, selected_year, datetime.now().month),
        )

        if selected_profile:
            dates_to_backfill = missing_backfill_dates(selected_profile, log_rows, today=date.today())
            if dates_to_backfill:
                if st.button(f"Backfill {len(dates_to_backfill)} missing date(s)"):
                    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                    entries = build_backfill_entries(selected_profile, dates_to_backfill, settings, timestamp)
                    for entry in entries:
                        append_log_entry(log_worksheet, entry)
                    st.success(f"Backfilled {len(entries)} missing date(s).")
                    st.rerun()
            else:
                st.caption("Historical expected mow dates are backfilled for this user/year.")

        if not selected_rows:
            st.info("No log rows yet for this user/year.")
            return

        import pandas as pd

        editor_rows = display_log_rows(selected_rows)
        editor_frame = pd.DataFrame(editor_rows)
        styled_editor = editor_frame.style.map(
            status_fill_color,
            subset=["Predicted Status", "Confirmed Status"],
        )
        edited_data = st.data_editor(
            styled_editor,
            use_container_width=True,
            hide_index=True,
            disabled=[
                "Username",
                "Year",
                "Date",
                "Expected Day",
                "Zip Code",
                "Latitude",
                "Longitude",
                "Weather Summary",
                "Predicted Status",
                "Confirmed Status",
                "Prediction Reason",
                "Created At",
                "Updated At",
            ],
            column_config={
                "Set Confirmed Status": st.column_config.SelectboxColumn(
                    "Set Confirmed Status",
                    options=[CONFIRMED_STATUS_PENDING, CONFIRMED_STATUS_MOWED, CONFIRMED_STATUS_SKIPPED],
                    required=True,
                ),
            },
            key=f"log-editor-{username}-{selected_year}",
        )
        edited_rows = edited_data.to_dict("records") if hasattr(edited_data, "to_dict") else edited_data
        updates = confirmation_updates(selected_rows, edited_rows)
        if st.button("Save confirmation changes", disabled=not updates):
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            updated_count = 0
            for row in updates:
                row_number = find_log_row_number(log_rows, row["Username"], row["Year"], row["Date"])
                if not row_number:
                    continue
                update_confirmation(
                    log_worksheet,
                    row_number=row_number,
                    confirmed_status=row["Confirmed Status"],
                    updated_at=timestamp,
                )
                updated_count += 1
            if updated_count:
                st.success(f"Updated {updated_count} confirmation(s).")
                st.rerun()
            else:
                st.warning("No matching log rows were found to update.")

        if pending_rows(selected_rows):
            st.caption(
                f"{len(pending_rows(selected_rows))} row(s) still need confirmation."
            )


def _load_streamlit_settings(st):
    try:
        secrets = dict(st.secrets)
        if isinstance(secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON"), dict):
            secrets["GOOGLE_SERVICE_ACCOUNT_JSON"] = json.dumps(secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
        return load_settings_from_mapping(secrets), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


if __name__ == "__main__":
    main()
