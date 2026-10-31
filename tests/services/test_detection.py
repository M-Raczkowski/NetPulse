from backend.services.detection import is_anomalous
import pytest

BASE = [40.0, 42.0, 41.0, 39.0, 43.0, 40.0, 41.0, 42.0, 40.0, 41.0]


def test_threshold_alarm():
    result = is_anomalous("threshold", BASE + [150.0], threshold=100.0)
    assert result is True


def test_threshold_normal():
    result = is_anomalous("threshold", BASE + [50.0], threshold=100.0)
    assert result is False


def test_zscore_alarm():
    result = is_anomalous("zscore", BASE + [60.0], threshold=100.0)
    assert result is True


def test_zscore_normal():
    result = is_anomalous("zscore", BASE + [42.0], threshold=100.0)
    assert result is False


def test_ewma_alarm():
    result = is_anomalous("ewma", BASE + [44.0] * 3, threshold=100.0)
    assert result is True


def test_ewma_normal():
    result = is_anomalous("ewma", BASE + [43.0] * 3, threshold=100.0)
    assert result is False


def test_no_values():
    result = is_anomalous("ewma", [], threshold=100.0)
    assert result is False


def test_unknown_detector():
    with pytest.raises(ValueError):
        is_anomalous("foo", BASE, threshold=100.0)
