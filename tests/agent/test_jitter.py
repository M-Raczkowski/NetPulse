from agent.measurements.jitter import calculate_jitter


def test_jitter_basic_case():
    test_values = [20,22,21,25]
    result = calculate_jitter(test_values)
    assert result == 7/3
def test_jitter_ignores_lost_packets():
    test_values = [20, None, 22]
    result = calculate_jitter(test_values)
    assert result == 2.0
def test_jitter_no_data():
    test_values = []
    result = calculate_jitter(test_values)
    assert result is None