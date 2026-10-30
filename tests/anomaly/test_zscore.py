from backend.anomaly.zscore import z_score
BASE = [40.0, 42.0, 41.0, 39.0, 43.0, 40.0, 41.0, 42.0, 40.0, 41.0]

def test_z_score_value_within_normal_range():
    result = z_score(BASE, 42.0)
    assert result is False

def test_z_score_value_above_k_is_anomaly():
    result = z_score(BASE, 45.0)
    assert result is True

def test_z_score_far_above_normal_is_anomaly():
    result = z_score(BASE, 60.0)
    assert result is True

def test_z_score_low_value_is_not_anomaly():
    result = z_score(BASE, 20.0)
    assert result is False

def test_z_score_history_too_short():
    result = z_score([40.0, 41.0, 42.0], 200.0)
    assert result is False
def test_z_score_zero_deviation():
    result = z_score([40.0]*10, 60.0)
    assert result is False

def test_z_score_ignores_none_in_history():
    result = z_score(BASE + [None, None], 45.0)
    assert result is True

def test_z_score_latest_none():
    result = z_score(BASE, None)
    assert result is False

def test_z_score_history_one_below_minimum():
    result = z_score(BASE[:-1], 45.0)
    assert result is False