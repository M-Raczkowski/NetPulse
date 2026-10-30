from backend.anomaly.lifecycle import AlertState, update_alert

def test_update_alert_first_anomaly_does_not_open():
    result = update_alert(AlertState(), is_anomaly = True)
    assert result == (AlertState(False, 1, 0), None)

def test_update_alert_opens_after_two_anomalies():
    result = update_alert(AlertState(False, 1, 0), is_anomaly = True)
    assert result == (AlertState(True, 2, 0), "opened")

def test_update_alert_open_alert_stays_open_on_anomaly():
    result = update_alert(AlertState(True, 2, 0), is_anomaly = True)
    assert result == (AlertState(True, 3, 0), None)

def test_update_alert_normal_resets_anomaly_streak():
    result = update_alert(AlertState(False, 1, 0), is_anomaly = False)
    assert result == (AlertState(False, 0, 1), None)

def test_update_alert_anomaly_resets_normal_streak():
    result = update_alert(AlertState(True, 0, 2), is_anomaly = True)
    assert result == (AlertState(True, 1, 0), None)

def test_update_alert_does_not_close_before_limit():
    result = update_alert(AlertState(True, 0, 1), is_anomaly = False)
    assert result == (AlertState(True, 0, 2), None)

def test_update_alert_closes_after_three_normals():
    result = update_alert(AlertState(True, 0, 2), is_anomaly = False)
    assert result == (AlertState(False, 0, 3), "closed")

def test_update_alert_custom_open_after():
    result = update_alert(AlertState(),is_anomaly =True, open_after =1)
    assert result == (AlertState(True, 1, 0), "opened")

def test_update_alert_does_not_modify_input_state():
    state = AlertState(True, 5, 5)
    update_alert(state, is_anomaly = False)
    assert state == AlertState(True, 5, 5)

def test_update_alert_full_scenario():
    state = AlertState()
    result = []
    cycle = [True, True, True, False, False, False]
    for i in cycle:
        state, event = update_alert(state, is_anomaly = i)
        result.append(event)
    assert result == [None, "opened", None, None,None, "closed"]