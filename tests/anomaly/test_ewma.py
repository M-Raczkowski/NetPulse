from backend.anomaly.ewma import ewma
BASE = [40.0, 42.0, 41.0, 39.0, 43.0, 40.0, 41.0, 42.0, 40.0, 41.0]

def test_ewma_value_within_normal_range():
    result = ewma(BASE, [41.0])
    assert result is False

def test_ewma_single_spike_is_smoothed():
    result = ewma(BASE, [45.0])
    assert result is False

def test_ewma_sustained_shift_is_anomaly():
    result = ewma(BASE, [45.0, 45.0])
    assert result is True

def test_ewma_low_value_is_not_anomaly():
    result = ewma(BASE, [20.0])
    assert result is False

def test_ewma_history_too_short():
    result = ewma([40.0, 41.0, 42.0], [200.0])
    assert result is False

def test_ewma_zero_deviation():
    result = ewma([40.0]*10, [60.0])
    assert result is False

def test_ewma_empty_recent():
    result = ewma(BASE,[])
    assert result is False

def test_ewma_ignores_none_in_history():
    result = ewma(BASE + [None, None], [45.0, 45.0])
    assert result is True

def test_ewma_ignores_none_in_recent():
    result = ewma(BASE, [None, 45.0, 45.0])
    assert result is True

def test_ewma_history_one_below_minimum():
    result = ewma(BASE[:-1], [45.0,45.0])
    assert result is False

def test_ewma_prolonged_moderate_shift_is_anomaly():
    result = ewma(BASE, [44.0,44.0,44.0])
    assert result is True

def test_ewma_prolonged_small_shift_is_not_anomaly():
    result = ewma(BASE, [43.0,43.0,43.0])
    assert result is False