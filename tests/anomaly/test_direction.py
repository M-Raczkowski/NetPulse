import pytest
from backend.anomaly.direction import direction_sign


def test_direction_sign_high():
    assert direction_sign("high") == 1


def test_direction_sign_low():
    assert direction_sign("low") == -1


def test_direction_sign_unknown():
    with pytest.raises(ValueError):
        direction_sign("sideways")
