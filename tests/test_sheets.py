from mow_metrics.models import CONFIRMED_STATUS_PENDING, LOG_HEADERS, USER_CONFIG_HEADERS


def test_shared_headers_and_status_constants_are_defined():
    assert USER_CONFIG_HEADERS[:4] == [
        "Username",
        "Active Year",
        "Zip Code",
        "Latitude",
    ]
    assert "Prediction Reason" in LOG_HEADERS
    assert CONFIRMED_STATUS_PENDING == "Pending"
