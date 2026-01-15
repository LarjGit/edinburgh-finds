"""
Extraction configuration loader.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


REQUIRED_ROOT_KEYS = {"llm", "trust_levels"}
REQUIRED_LLM_KEYS = {"model"}


def load_extraction_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and validate extraction configuration from YAML.

    Args:
        config_path: Optional path to extraction.yaml

    Returns:
        Dict[str, Any]: Validated configuration dictionary
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "extraction.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as handle:
        config = yaml.safe_load(handle) or {}

    _validate_extraction_config(config)
    return config


def _validate_extraction_config(config: Dict[str, Any]) -> None:
    missing = REQUIRED_ROOT_KEYS - set(config.keys())
    if missing:
        raise ValueError(f"Missing required config keys: {sorted(missing)}")

    llm_config = config.get("llm") or {}
    missing_llm = REQUIRED_LLM_KEYS - set(llm_config.keys())
    if missing_llm:
        raise ValueError(f"Missing required llm config keys: {sorted(missing_llm)}")

    trust_levels = config.get("trust_levels") or {}
    if not isinstance(trust_levels, dict) or not trust_levels:
        raise ValueError("trust_levels must be a non-empty mapping")

    for source, score in trust_levels.items():
        if not isinstance(score, int):
            raise ValueError(f"Trust level for {source} must be an integer")

