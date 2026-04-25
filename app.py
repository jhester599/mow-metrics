from datetime import date, datetime, timezone
import json

from mow_metrics.config import load_settings_from_mapping
from mow_metrics.models import MOW_DAYS
from mow_metrics.seasonality import derive_season_dates
from mow_metrics.sheets import (
    find_log_row_number,
    get_log_worksheet,
    get_user_config_worksheet,
    open_spreadsheet,
    read_records,
    save_user_config,
    update_confirmation,
)
from mow_metrics.weather import geocode_zip


def count_confirmed_mows_for_month(rows: list[dict[str, str]], selected_year: int, current_month: int) -> int:
    total = 0
    for row in rows:
        if row.get("Confirmed Status") != "Yes":
            continue
        row_date = datetime.strptime(row["Date"], "%Y-%m-%d")
        if row_date.year == selected_year and row_date.month == current_month:
            total += 1
    return total


def pending_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if row.get("Confirmed Status") == "Pending"]


def filter_log_rows(rows: list[dict[str, str]], username: str, year: int) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if row.get("Username") == username and str(row.get("Year")) == str(year)
    ]


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

    settings = _load_streamlit_settings(st)
    if not settings:
        st.warning("Add Google Sheets secrets to enable the dashboard.")
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
        selected_rows = filter_log_rows(log_rows, username=username, year=selected_year)
        st.metric(
            "Total Confirmed Mows This Month",
            count_confirmed_mows_for_month(selected_rows, selected_year, datetime.now().month),
        )
        st.dataframe(selected_rows, use_container_width=True)
        for row in pending_rows(selected_rows):
            row_number = find_log_row_number(log_rows, row["Username"], row["Year"], row["Date"])
            left, right = st.columns([3, 2])
            left.write(f"{row['Date']} - predicted {row['Predicted Status']}")
            confirmed = right.radio(
                "Confirmed Status",
                ["Pending", "Yes", "No"],
                key=f"confirm-{row['Username']}-{row['Year']}-{row['Date']}",
                horizontal=True,
            )
            if confirmed != "Pending" and row_number:
                update_confirmation(
                    log_worksheet,
                    row_number=row_number,
                    confirmed_status=confirmed,
                    updated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                )
                st.success(f"Updated {row['Date']} to {confirmed}.")


def _load_streamlit_settings(st):
    try:
        secrets = dict(st.secrets)
        if isinstance(secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON"), dict):
            secrets["GOOGLE_SERVICE_ACCOUNT_JSON"] = json.dumps(secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
        return load_settings_from_mapping(secrets)
    except Exception:
        return None


if __name__ == "__main__":
    main()
