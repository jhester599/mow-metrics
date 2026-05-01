from dataclasses import dataclass

USER_CONFIG_HEADERS = [
    "Username",
    "Active Year",
    "Zip Code",
    "Latitude",
    "Longitude",
    "Expected Mow Day",
    "Season Start",
    "Season End",
    "Created At",
    "Updated At",
]

LOG_HEADERS = [
    "Username",
    "Year",
    "Date",
    "Expected Day",
    "Zip Code",
    "Latitude",
    "Longitude",
    "Weather Summary",
    "Raw API JSON",
    "Predicted Status",
    "Confirmed Status",
    "Prediction Reason",
    "Created At",
    "Updated At",
]

CONFIRMED_STATUS_PENDING = "Pending"
CONFIRMED_STATUS_MOWED = "Mowed"
CONFIRMED_STATUS_SKIPPED = "Skipped"
PREDICTED_STATUS_MOWED = "Mowed"
PREDICTED_STATUS_SKIPPED = "Skipped"

MOW_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


@dataclass(frozen=True)
class UserConfig:
    username: str
    active_year: int
    zip_code: str
    latitude: float
    longitude: float
    expected_mow_day: str
    season_start: str
    season_end: str


@dataclass(frozen=True)
class LogEntry:
    username: str
    year: int
    date: str
    expected_day: str
    zip_code: str
    latitude: float
    longitude: float
    weather_summary: str
    raw_api_json: str
    predicted_status: str
    confirmed_status: str
    prediction_reason: str
