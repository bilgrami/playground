"""Unit tests for config and CLI parsing in snowdiff module."""

import argparse
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict

import pytest

from scripts.snowdiff import (
    build_target,
    deep_get,
    get_env_var,
    load_config,
    read_comment_collection,
    read_options,
    read_table_filter,
)


class TestDeepGet:
    """Tests for deep_get helper function."""

    def test_single_key(self) -> None:
        """Test single key access."""
        d = {"a": 1}
        assert deep_get(d, ["a"]) == 1

    def test_nested_keys(self) -> None:
        """Test nested key access."""
        d = {"a": {"b": {"c": 3}}}
        assert deep_get(d, ["a", "b", "c"]) == 3

    def test_missing_key_returns_default(self) -> None:
        """Test missing key returns default value."""
        d = {"a": 1}
        assert deep_get(d, ["b"]) is None
        assert deep_get(d, ["b"], "default") == "default"

    def test_missing_nested_key(self) -> None:
        """Test missing nested key returns default."""
        d = {"a": {"b": 1}}
        assert deep_get(d, ["a", "c"]) is None
        assert deep_get(d, ["x", "y", "z"], 0) == 0


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid YAML config."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("key: value\nnested:\n  inner: 123\n")
        cfg = load_config(config_file)
        assert cfg["key"] == "value"
        assert cfg["nested"]["inner"] == 123

    def test_load_missing_config_raises(self, tmp_path: Path) -> None:
        """Test loading missing config raises SystemExit."""
        missing = tmp_path / "nonexistent.yml"
        with pytest.raises(SystemExit, match="config not found"):
            load_config(missing)

    def test_load_empty_config_returns_empty_dict(self, tmp_path: Path) -> None:
        """Test empty config returns empty dict."""
        config_file = tmp_path / "empty.yml"
        config_file.write_text("")
        cfg = load_config(config_file)
        assert cfg == {}


class TestGetEnvVar:
    """Tests for get_env_var function."""

    def test_returns_env_var_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test returns value when env var is set."""
        monkeypatch.setenv("SNOWDIFF_LEFT_CONNECTION", "my_conn")
        assert get_env_var("left", "connection") == "my_conn"

    def test_returns_none_when_not_set(self) -> None:
        """Test returns None when env var is not set."""
        assert get_env_var("left", "nonexistent_field") is None

    def test_case_conversion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that side and field are converted to uppercase."""
        monkeypatch.setenv("SNOWDIFF_RIGHT_DATABASE", "my_db")
        # Lowercase input should work
        assert get_env_var("right", "database") == "my_db"


class TestBuildTarget:
    """Tests for build_target function."""

    @pytest.fixture
    def valid_config(self) -> Dict[str, Any]:
        """Return a valid configuration dictionary."""
        return {
            "left": {
                "connection": "dev",
                "role": "DEV_ROLE",
                "warehouse": "DEV_WH",
                "database": "DEV_DB",
                "schema": "PUBLIC",
            },
            "right": {
                "connection": "prod",
                "role": "PROD_ROLE",
                "warehouse": "PROD_WH",
                "database": "PROD_DB",
                "schema": "PUBLIC",
            },
        }

    def test_build_target_from_config(self, valid_config: Dict[str, Any]) -> None:
        """Test building target from config only."""
        target = build_target(valid_config, "left", {})
        assert target.connection == "dev"
        assert target.role == "DEV_ROLE"
        assert target.warehouse == "DEV_WH"
        assert target.database == "DEV_DB"
        assert target.schema == "PUBLIC"
        assert target.label == "left"

    def test_build_target_with_overrides(self, valid_config: Dict[str, Any]) -> None:
        """Test CLI overrides replace config values."""
        overrides = {
            "left_role": "CUSTOM_ROLE",
            "left_warehouse": "CUSTOM_WH",
        }
        target = build_target(valid_config, "left", overrides)
        assert target.role == "CUSTOM_ROLE"
        assert target.warehouse == "CUSTOM_WH"
        # Non-overridden values from config
        assert target.connection == "dev"
        assert target.database == "DEV_DB"

    def test_build_target_with_env_vars(
        self, valid_config: Dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variables take highest priority."""
        # Set env var for role
        monkeypatch.setenv("SNOWDIFF_LEFT_ROLE", "ENV_ROLE")
        # Also provide CLI override (should be ignored)
        overrides = {"left_role": "CLI_ROLE"}
        target = build_target(valid_config, "left", overrides)
        # Env var should take precedence
        assert target.role == "ENV_ROLE"

    def test_build_target_missing_connection_raises(self) -> None:
        """Test missing connection raises SystemExit with helpful message."""
        cfg = {"left": {"role": "R", "warehouse": "W", "database": "D", "schema": "S"}}
        with pytest.raises(SystemExit) as exc_info:
            build_target(cfg, "left", {})
        error_msg = str(exc_info.value)
        # Should mention the missing field
        assert "missing left.connection" in error_msg
        # Should suggest environment variable
        assert "SNOWDIFF_LEFT_CONNECTION" in error_msg
        # Should suggest CLI flag
        assert "--left-connection" in error_msg

    def test_build_target_missing_field_raises(self) -> None:
        """Test missing required field raises SystemExit with helpful message."""
        cfg = {"left": {"connection": "dev", "role": "R"}}  # missing warehouse, db, schema
        with pytest.raises(SystemExit) as exc_info:
            build_target(cfg, "left", {})
        error_msg = str(exc_info.value)
        assert "missing left.warehouse" in error_msg
        assert "SNOWDIFF_LEFT_WAREHOUSE" in error_msg


class TestReadOptions:
    """Tests for read_options function."""

    @pytest.fixture
    def mock_args(self) -> argparse.Namespace:
        """Return mock argparse namespace with defaults."""
        return argparse.Namespace(
            no_schema=False,
            no_table_ddl=False,
            no_data=False,
            no_procs=False,
            no_comments=False,
            no_last_changed=False,
        )

    def test_default_options_all_true(self, mock_args: argparse.Namespace) -> None:
        """Test default options are all True."""
        cfg: Dict[str, Any] = {}
        opt = read_options(cfg, mock_args)
        assert opt.schema is True
        assert opt.table_ddl is True
        assert opt.data is True
        assert opt.procs is True
        assert opt.comments is True
        assert opt.last_changed is True

    def test_options_from_config(self, mock_args: argparse.Namespace) -> None:
        """Test options loaded from config."""
        cfg = {"options": {"schema": False, "data": False}}
        opt = read_options(cfg, mock_args)
        assert opt.schema is False
        assert opt.data is False
        assert opt.table_ddl is True  # default

    def test_cli_flags_override_config(self, mock_args: argparse.Namespace) -> None:
        """Test CLI flags override config values."""
        cfg = {"options": {"schema": True, "data": True}}
        mock_args.no_schema = True
        mock_args.no_data = True
        opt = read_options(cfg, mock_args)
        assert opt.schema is False
        assert opt.data is False


class TestReadTableFilter:
    """Tests for read_table_filter function."""

    @pytest.fixture
    def mock_args(self) -> argparse.Namespace:
        """Return mock argparse namespace."""
        return argparse.Namespace(include=None, exclude=None)

    def test_empty_filters(self, mock_args: argparse.Namespace) -> None:
        """Test empty filters returns empty lists."""
        cfg: Dict[str, Any] = {}
        tf = read_table_filter(cfg, mock_args)
        assert tf.include == []
        assert tf.exclude == []
        assert tf.case_sensitive is False  # default

    def test_filters_from_config(self, mock_args: argparse.Namespace) -> None:
        """Test filters loaded from config."""
        cfg = {"table_filter": {"include": ["FACT_%"], "exclude": ["TMP_%"]}}
        tf = read_table_filter(cfg, mock_args)
        assert tf.include == ["FACT_%"]
        assert tf.exclude == ["TMP_%"]

    def test_cli_patterns_append_to_config(self, mock_args: argparse.Namespace) -> None:
        """Test CLI patterns are appended to config patterns."""
        cfg = {"table_filter": {"include": ["FACT_%"]}}
        mock_args.include = ["DIM_%"]
        mock_args.exclude = ["TMP_%"]
        tf = read_table_filter(cfg, mock_args)
        assert tf.include == ["FACT_%", "DIM_%"]
        assert tf.exclude == ["TMP_%"]

    def test_case_sensitive_from_config(self, mock_args: argparse.Namespace) -> None:
        """Test case_sensitive option loaded from config."""
        cfg = {"table_filter": {"case_sensitive": True}}
        tf = read_table_filter(cfg, mock_args)
        assert tf.case_sensitive is True

    def test_case_sensitive_defaults_to_false(self, mock_args: argparse.Namespace) -> None:
        """Test case_sensitive defaults to False (case-insensitive)."""
        cfg = {"table_filter": {"include": ["FACT_%"]}}
        tf = read_table_filter(cfg, mock_args)
        assert tf.case_sensitive is False


class TestReadCommentCollection:
    """Tests for read_comment_collection function."""

    @pytest.fixture
    def mock_args(self) -> argparse.Namespace:
        """Return mock argparse namespace."""
        return argparse.Namespace(column_comment_mode=None)

    def test_default_mode_is_desc(self, mock_args: argparse.Namespace) -> None:
        """Test default column comment mode is 'desc'."""
        cfg: Dict[str, Any] = {}
        cc = read_comment_collection(cfg, mock_args)
        assert cc.column_mode == "desc"

    def test_mode_from_config(self, mock_args: argparse.Namespace) -> None:
        """Test mode loaded from config."""
        cfg = {"comment_collection": {"column_mode": "account_usage"}}
        cc = read_comment_collection(cfg, mock_args)
        assert cc.column_mode == "account_usage"

    def test_cli_overrides_config(self, mock_args: argparse.Namespace) -> None:
        """Test CLI flag overrides config."""
        cfg = {"comment_collection": {"column_mode": "desc"}}
        mock_args.column_comment_mode = "account_usage"
        cc = read_comment_collection(cfg, mock_args)
        assert cc.column_mode == "account_usage"

    def test_invalid_mode_defaults_to_desc(self, mock_args: argparse.Namespace) -> None:
        """Test invalid mode falls back to 'desc'."""
        cfg = {"comment_collection": {"column_mode": "invalid"}}
        cc = read_comment_collection(cfg, mock_args)
        assert cc.column_mode == "desc"
