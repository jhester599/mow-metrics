import json

import pytest

from mow_metrics.config import load_settings, load_settings_from_mapping


def test_load_settings_reads_sheet_id_service_account_and_defaults(monkeypatch):
    service_account = {"client_email": "bot@example.com", "private_key": "fake"}
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-123")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps(service_account))

    settings = load_settings()

    assert settings.google_sheet_id == "sheet-123"
    assert settings.google_service_account_info == service_account
    assert settings.precipitation_threshold_mm == 0.2
    assert settings.workday_start_hour == 8
    assert settings.workday_end_hour == 17
    assert settings.saturation_threshold_mm == 5.0
    assert settings.saturation_start_hour == 18
    assert settings.saturation_end_hour == 23
    assert settings.mow_day_morning_start_hour == 6
    assert settings.mow_day_morning_end_hour == 12


def test_load_settings_requires_service_account_json(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEET_ID", "sheet-123")
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

    with pytest.raises(RuntimeError, match="GOOGLE_SERVICE_ACCOUNT_JSON"):
        load_settings()


def test_load_settings_from_mapping_supports_streamlit_like_secrets():
    service_account = {"client_email": "bot@example.com", "private_key": "fake"}

    settings = load_settings_from_mapping(
        {
            "GOOGLE_SHEET_ID": "sheet-123",
            "GOOGLE_SERVICE_ACCOUNT_JSON": json.dumps(service_account),
            "PRECIPITATION_THRESHOLD_MM": "0.5",
            "SATURATION_THRESHOLD_MM": "8.0",
            "SATURATION_START_HOUR": "17",
            "SATURATION_END_HOUR": "22",
            "MOW_DAY_MORNING_START_HOUR": "5",
            "MOW_DAY_MORNING_END_HOUR": "11",
        }
    )

    assert settings.google_sheet_id == "sheet-123"
    assert settings.google_service_account_info == service_account
    assert settings.precipitation_threshold_mm == 0.5
    assert settings.saturation_threshold_mm == 8.0
    assert settings.saturation_start_hour == 17
    assert settings.saturation_end_hour == 22
    assert settings.mow_day_morning_start_hour == 5
    assert settings.mow_day_morning_end_hour == 11
