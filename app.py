from datetime import date, datetime


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

    tab_setup, tab_dashboard = st.tabs(["Setup", "Dashboard"])
    with tab_setup:
        st.subheader("User Configuration")
        st.text_input("Username")
        st.number_input("Calendar Year", min_value=2024, max_value=2100, value=datetime.now().year)
        st.text_input("Zip Code")
        st.selectbox("Expected Mow Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        st.info("Connect Google Sheets secrets to enable saving profiles.")

    with tab_dashboard:
        st.subheader("Reconciliation")
        st.metric("Total Confirmed Mows This Month", 0)
        st.info("Log rows will appear here after Google Sheets is configured.")


if __name__ == "__main__":
    main()
