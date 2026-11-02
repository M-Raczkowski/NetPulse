from agent.config import parse_targets
import pytest


def test_parse_targets_one_target():
    result = parse_targets("127.0.0.1:9999")
    assert result == [("127.0.0.1", 9999)]


def test_parse_targets_two_targets():
    result = parse_targets("127.0.0.1:9999,192.0.0.1:8888")
    assert result == [("127.0.0.1", 9999), ("192.0.0.1", 8888)]


def test_parse_targets_targets_with_space():
    result = parse_targets("127.0.0.1:9999, 192.0.0.1:8888")
    assert result == [("127.0.0.1", 9999), ("192.0.0.1", 8888)]


def test_parse_targets_no_port():
    with pytest.raises(ValueError):
        parse_targets("127.0.0.1")


def test_parse_targerts_port_not_int():
    with pytest.raises(ValueError):
        parse_targets("host:abc")
