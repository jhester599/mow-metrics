from collections.abc import Iterable

from mow_metrics.models import LOG_HEADERS


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
