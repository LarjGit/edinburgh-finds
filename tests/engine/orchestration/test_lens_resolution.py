"""
Tests for lens resolution precedence (architecture.md 3.1).

LR-001: Lens resolution must follow 4-level precedence:
1. CLI override (--lens flag)
2. Environment variable (LENS_ID)
3. Application config (engine/config/app.yaml → default_lens)
4. Dev/Test fallback (LR-002 - not implemented yet)
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO
import pytest


def test_cli_override_takes_precedence_over_config(monkeypatch):
    """
    CLI --lens flag should take precedence over config file.

    Precedence: CLI > environment > config > error
    """
    # Ensure environment variable is NOT set
    monkeypatch.delenv("LENS_ID", raising=False)

    # Simulate CLI args with --lens flag
    test_args = [
        "cli.py", "run",
        "--lens", "edinburgh_finds",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock file system to provide config with different value
        config_content = "default_lens: wine\n"
        m = mock_open(read_data=config_content)

        with patch('engine.orchestration.cli.bootstrap_lens') as mock_bootstrap:
            with patch('engine.orchestration.cli.asyncio.run'):
                with patch('builtins.open', m):
                    mock_bootstrap.return_value = MagicMock()

                    try:
                        main()
                    except SystemExit:
                        pass  # CLI exits successfully

                    # Verify bootstrap was called with CLI value, not config value
                    mock_bootstrap.assert_called_once()
                    call_args = mock_bootstrap.call_args[0]
                    assert call_args[0] == "edinburgh_finds", "CLI override failed"


def test_environment_variable_takes_precedence_over_config(monkeypatch):
    """
    LENS_ID environment variable should take precedence over config file.

    Precedence: CLI > environment > config > error
    """
    # Set environment variable
    monkeypatch.setenv("LENS_ID", "edinburgh_finds")

    # Simulate CLI args WITHOUT --lens flag
    test_args = [
        "cli.py", "run",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock file system to provide config with different value
        config_content = "default_lens: wine\n"
        m = mock_open(read_data=config_content)

        with patch('engine.orchestration.cli.bootstrap_lens') as mock_bootstrap:
            with patch('engine.orchestration.cli.asyncio.run'):
                with patch('builtins.open', m):
                    mock_bootstrap.return_value = MagicMock()

                    try:
                        main()
                    except SystemExit:
                        pass  # CLI exits successfully

                    # Verify bootstrap was called with env var value, not config value
                    mock_bootstrap.assert_called_once()
                    call_args = mock_bootstrap.call_args[0]
                    assert call_args[0] == "edinburgh_finds", "Environment variable precedence failed"


def test_config_file_used_when_cli_and_env_not_set(monkeypatch):
    """
    Config file should be used when CLI and environment variable not set.

    Precedence: CLI > environment > config > error
    """
    # Ensure environment variable is NOT set
    monkeypatch.delenv("LENS_ID", raising=False)

    # Simulate CLI args WITHOUT --lens flag
    test_args = [
        "cli.py", "run",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock file system to provide config file
        config_content = "default_lens: wine\n"
        m = mock_open(read_data=config_content)

        # Mock Path.exists() to return True for config file
        with patch('engine.orchestration.cli.bootstrap_lens') as mock_bootstrap:
            with patch('engine.orchestration.cli.asyncio.run'):
                with patch('builtins.open', m):
                    with patch.object(Path, 'exists', return_value=True):
                        mock_bootstrap.return_value = MagicMock()

                        try:
                            main()
                        except SystemExit:
                            pass  # CLI exits successfully

                        # Verify bootstrap was called with config value
                        mock_bootstrap.assert_called_once()
                        call_args = mock_bootstrap.call_args[0]
                        assert call_args[0] == "wine", "Config file not used as fallback"


def test_missing_config_file_does_not_crash(monkeypatch, capsys):
    """
    Missing config file should fail gracefully with clear error message.

    When CLI, environment, and config are all unavailable, should error cleanly.
    """
    # Ensure environment variable is NOT set
    monkeypatch.delenv("LENS_ID", raising=False)

    # Simulate CLI args WITHOUT --lens flag
    test_args = [
        "cli.py", "run",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock Path.exists() to return False (no config file)
        with patch.object(Path, 'exists', return_value=False):
            # Should exit with error, not crash
            with pytest.raises(SystemExit) as exc_info:
                main()

            # Should exit with error code 1
            assert exc_info.value.code == 1, "Should exit with error code"

            # Should print clear error message
            captured = capsys.readouterr()
            assert "ERROR: No lens specified" in captured.out, "Missing error message"


def test_config_with_null_default_lens_does_not_crash(monkeypatch, capsys):
    """
    Config file with default_lens: null should be treated as no config.

    Per user guidance: "Use default_lens: null (or omit the key entirely)."
    This should gracefully fall through to error (or future fallback).
    """
    # Ensure environment variable is NOT set
    monkeypatch.delenv("LENS_ID", raising=False)

    # Simulate CLI args WITHOUT --lens flag
    test_args = [
        "cli.py", "run",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock file system to provide config with null value
        config_content = "default_lens: null\n"
        m = mock_open(read_data=config_content)

        # Mock Path.exists() to return True
        with patch('builtins.open', m):
            with patch.object(Path, 'exists', return_value=True):
                # Should exit with error (null treated as no config)
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with error code 1
                assert exc_info.value.code == 1, "Should exit with error code"

                # Should print clear error message
                captured = capsys.readouterr()
                assert "ERROR: No lens specified" in captured.out, "Missing error message"


def test_invalid_yaml_in_config_fails_gracefully(monkeypatch, capsys):
    """
    Invalid YAML in config file should fail gracefully with clear error.

    Per user guidance: "If the config file exists but YAML is unavailable,
    fail gracefully with a clear error."
    """
    # Ensure environment variable is NOT set
    monkeypatch.delenv("LENS_ID", raising=False)

    # Simulate CLI args WITHOUT --lens flag
    test_args = [
        "cli.py", "run",
        "test query"
    ]

    with patch.object(sys, 'argv', test_args):
        from engine.orchestration.cli import main

        # Mock file system to provide invalid YAML
        config_content = "default_lens: [unclosed array\n"
        m = mock_open(read_data=config_content)

        # Mock Path.exists() to return True
        with patch('builtins.open', m):
            with patch.object(Path, 'exists', return_value=True):
                # Should exit with error, not crash with stack trace
                with pytest.raises(SystemExit) as exc_info:
                    main()

                # Should exit with error code 1
                assert exc_info.value.code == 1, "Should exit with error code"

                # Should print error about config file
                captured = capsys.readouterr()
                assert "config" in captured.out.lower() or "yaml" in captured.out.lower(), \
                    "Should mention config/YAML error"
