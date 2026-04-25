from datetime import date


def derive_season_dates(latitude: float, year: int) -> tuple[date, date]:
    if latitude >= 40:
        return date(year, 4, 1), date(year, 11, 30)
    if latitude >= 33:
        return date(year, 3, 15), date(year, 12, 15)
    return date(year, 3, 1), date(year, 12, 31)


def is_date_in_season(target_date: date, season_start: date, season_end: date) -> bool:
    return season_start <= target_date <= season_end


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)
