from collections.abc import Iterable
from typing import Any

from mow_metrics.models import LOG_HEADERS, USER_CONFIG_HEADERS


def build_log_key(username: str, year: int | str, mow_date: str) -> str:
    return f"{username}|{year}|{mow_date}"


def existing_log_keys(rows: Iterable[dict[str, str]]) -> set[str]:
    return {
        build_log_key(row["Username"], row["Year"], row["Date"])
        for row in rows
        if row.get("Username") and row.get("Year") and row.get("Date")
    }


def upsert_user_config_row(existing_rows: list[dict[str, str]], new_row: dict[str, str]) -> list[dict[str, str]]:
    result = []
    replaced = False
    for row in existing_rows:
        if row.get("Username") == new_row.get("Username") and row.get("Active Year") == new_row.get("Active Year"):
            result.append(new_row)
            replaced = True
        else:
            result.append(row)
    if not replaced:
        result.append(new_row)
    return result


def ensure_headers(worksheet, headers: list[str]) -> None:
    if worksheet.row_values(1) != headers:
        worksheet.update("1:1", [headers])


def find_log_row_number(rows: list[dict[str, str]], username: str, year: int | str, mow_date: str) -> int | None:
    target_key = build_log_key(username, year, mow_date)
    for index, row in enumerate(rows, start=2):
        if build_log_key(row.get("Username", ""), row.get("Year", ""), row.get("Date", "")) == target_key:
            return index
    return None


def log_entry_to_row(entry: dict[str, str]) -> list[str]:
    return [str(entry.get(header, "")) for header in LOG_HEADERS]


def update_confirmation(worksheet, row_number: int, confirmed_status: str, updated_at: str) -> None:
    worksheet.update(f"K{row_number}", [[confirmed_status]])
    worksheet.update(f"N{row_number}", [[updated_at]])


def user_config_to_row(entry: dict[str, str]) -> list[str]:
    return [str(entry.get(header, "")) for header in USER_CONFIG_HEADERS]


def authorize(service_account_info: dict[str, Any]):
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(credentials)


def open_spreadsheet(settings):
    client = authorize(settings.google_service_account_info)
    return client.open_by_key(settings.google_sheet_id)


def get_or_create_worksheet(spreadsheet, title: str, headers: list[str]):
    try:
        worksheet = spreadsheet.worksheet(title)
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(len(headers), 1))
    ensure_headers(worksheet, headers)
    return worksheet


def get_user_config_worksheet(spreadsheet):
    return get_or_create_worksheet(spreadsheet, "Users_Config", USER_CONFIG_HEADERS)


def get_log_worksheet(spreadsheet):
    return get_or_create_worksheet(spreadsheet, "Log", LOG_HEADERS)


def read_records(worksheet) -> list[dict[str, str]]:
    return worksheet.get_all_records()


def append_log_entry(worksheet, entry: dict[str, str]) -> None:
    worksheet.append_row(log_entry_to_row(entry), value_input_option="USER_ENTERED")


def save_user_config(worksheet, row: dict[str, str]) -> None:
    records = read_records(worksheet)
    row_values = user_config_to_row(row)
    for row_number, existing in enumerate(records, start=2):
        if existing.get("Username") == row.get("Username") and str(existing.get("Active Year")) == str(row.get("Active Year")):
            worksheet.update(f"A{row_number}:J{row_number}", [row_values])
            return
    worksheet.append_row(row_values, value_input_option="USER_ENTERED")
