from datetime import date

from mow_metrics.seasonality import derive_season_dates, is_date_in_season, parse_iso_date


def test_44236_defaults_to_april_through_november_for_2026():
    start_date, end_date = derive_season_dates(latitude=41.35, year=2026)
    assert start_date == date(2026, 4, 1)
    assert end_date == date(2026, 11, 30)


def test_temperate_latitudes_get_longer_season():
    start_date, end_date = derive_season_dates(latitude=36.5, year=2026)
    assert start_date == date(2026, 3, 15)
    assert end_date == date(2026, 12, 15)


def test_is_date_in_season_is_inclusive():
    assert is_date_in_season(date(2026, 4, 1), date(2026, 4, 1), date(2026, 11, 30))


def test_parse_iso_date_accepts_sheet_date_format():
    assert parse_iso_date("2026-11-30") == date(2026, 11, 30)
