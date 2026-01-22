"""
Tests for extraction config loading and validation.
"""

import pytest

from engine.extraction.config import load_extraction_config


def test_load_extraction_config_defaults():
    config = load_extraction_config()
    assert "llm" in config
    assert "trust_levels" in config
    assert "model" in config["llm"]
    assert "google_places" in config["trust_levels"]


def test_load_extraction_config_missing_required_keys(tmp_path):
    config_path = tmp_path / "extraction.yaml"
    config_path.write_text("llm:\n  model: \"test-model\"\n")

    with pytest.raises(ValueError, match="Missing required config keys"):
        load_extraction_config(str(config_path))


def test_load_extraction_config_invalid_trust_level(tmp_path):
    config_path = tmp_path / "extraction.yaml"
    config_path.write_text(
        "llm:\n  model: \"test-model\"\ntrust_levels:\n  google_places: high\n"
    )

    with pytest.raises(ValueError, match="Trust level"):
        load_extraction_config(str(config_path))

