from backend.anomaly.threshold import threshold_check


def test_below_threshold():
    result = threshold_check(40, 100)
    assert result == False
def test_above_threshold():
    result = threshold_check(150, 100)
    assert result == True
def test_equal_threshold():
    result = threshold_check(100, 100)
    assert result == False
def test_no_value():
    result = threshold_check(None, 100)
    assert result == False