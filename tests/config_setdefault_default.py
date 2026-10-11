import pytest

from invoke import Config


@pytest.mark.parametrize("nested", [False, True])
def test_setdefault_without_default_tracks_none(nested):
    config = Config(defaults={"nested": {}} if nested else {})
    target = config.nested if nested else config

    assert target.setdefault("missing") is None
    assert target["missing"] is None
    config.merge()
    target = config.nested if nested else config
    assert "missing" in target
    assert target["missing"] is None


def test_setdefault_without_default_preserves_existing_value():
    config = Config(defaults={"present": "original"})

    assert config.setdefault("present") == "original"
    config.merge()
    assert config["present"] == "original"
