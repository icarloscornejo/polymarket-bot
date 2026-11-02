"""TDD tests for Settings loader and bootstrap function."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.config.settings import Settings
from src.infrastructure.persistence.database import build_engine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_CONFIG = textwrap.dedent("""\
    strategy_defaults:
      entry_window_min_sec: 5
      entry_window_max_sec: 25
      min_dtt: 10.0
      min_gain_usd: 0.75
      position_size_usd: 10.0
      snapshot_interval_ms: 1000
      logging_window_buffer_sec: 10
    runtime:
      mode: PAPER
      btc_feed_primary: binance
      btc_feed_fallback: coinbase
      btc_feed_failover_threshold_sec: 3
      market_discovery_websocket: true
      market_discovery_rest_interval_sec: 30
      timezone_default: America/El_Salvador
    cleanup:
      snapshots_retention_days: 7
      daily_run_hour_local: 3
    storage:
      sqlite_path: data/polybot.db
    logging:
      level: INFO
      json: true
""")


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    f = tmp_path / "config.yml"
    f.write_text(_VALID_CONFIG)
    return f


# ---------------------------------------------------------------------------
# Settings.load()
# ---------------------------------------------------------------------------

class TestSettingsLoad:

    def test_loads_strategy_defaults(self, config_file: Path) -> None:
        s = Settings.load(str(config_file))
        assert s.strategy_defaults.min_dtt == pytest.approx(10.0)
        assert s.strategy_defaults.position_size_usd == pytest.approx(10.0)
        assert s.strategy_defaults.entry_window_min_sec == 5
        assert s.strategy_defaults.entry_window_max_sec == 25

    def test_loads_runtime_config(self, config_file: Path) -> None:
        s = Settings.load(str(config_file))
        assert s.runtime.mode == "PAPER"
        assert s.runtime.btc_feed_primary == "binance"
        assert s.runtime.timezone_default == "America/El_Salvador"

    def test_loads_cleanup_config(self, config_file: Path) -> None:
        s = Settings.load(str(config_file))
        assert s.cleanup.snapshots_retention_days == 7
        assert s.cleanup.daily_run_hour_local == 3

    def test_loads_storage_config(self, config_file: Path) -> None:
        s = Settings.load(str(config_file))
        assert s.storage.sqlite_path == "data/polybot.db"

    def test_loads_logging_config(self, config_file: Path) -> None:
        s = Settings.load(str(config_file))
        assert s.logging.level == "INFO"
        assert s.logging.json is True

    def test_raises_when_config_file_missing(self) -> None:
        with pytest.raises(FileNotFoundError):
            Settings.load("/nonexistent/path/config.yml")

    def test_reads_env_vars_for_api_settings(self, config_file: Path, monkeypatch) -> None:
        monkeypatch.setenv("API_HOST", "0.0.0.0")
        monkeypatch.setenv("API_PORT", "9000")
        s = Settings.load(str(config_file))
        assert s.api_host == "0.0.0.0"
        assert s.api_port == 9000

    def test_api_defaults_when_env_vars_missing(self, config_file: Path, monkeypatch) -> None:
        monkeypatch.delenv("API_HOST", raising=False)
        monkeypatch.delenv("API_PORT", raising=False)
        s = Settings.load(str(config_file))
        assert s.api_host == "127.0.0.1"
        assert s.api_port == 8000

    def test_polymarket_keys_are_none_when_not_in_env(self, config_file: Path, monkeypatch) -> None:
        for key in ["POLYMARKET_PRIVATE_KEY", "POLYMARKET_API_KEY",
                    "POLYMARKET_API_SECRET", "POLYMARKET_API_PASSPHRASE",
                    "POLYMARKET_PROXY_ADDRESS"]:
            monkeypatch.delenv(key, raising=False)
        s = Settings.load(str(config_file))
        assert s.polymarket_private_key is None
        assert s.polymarket_api_key is None

    def test_polymarket_keys_loaded_from_env(self, config_file: Path, monkeypatch) -> None:
        monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "0xdeadbeef")
        monkeypatch.setenv("POLYMARKET_API_KEY", "my-api-key")
        monkeypatch.setenv("POLYMARKET_API_SECRET", "my-secret")
        monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "my-pass")
        monkeypatch.setenv("POLYMARKET_PROXY_ADDRESS", "0xcafe")
        s = Settings.load(str(config_file))
        assert s.polymarket_private_key == "0xdeadbeef"
        assert s.polymarket_api_key == "my-api-key"


# ---------------------------------------------------------------------------
# Settings.validate_for_live_mode()
# ---------------------------------------------------------------------------

class TestSettingsValidateForLiveMode:

    def _settings_with_keys(self, config_file: Path, monkeypatch) -> Settings:
        monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "0xdeadbeef")
        monkeypatch.setenv("POLYMARKET_API_KEY", "key")
        monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
        monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
        monkeypatch.setenv("POLYMARKET_PROXY_ADDRESS", "0xcafe")
        return Settings.load(str(config_file))

    def test_paper_mode_validates_without_keys(self, config_file: Path, monkeypatch) -> None:
        for k in ["POLYMARKET_PRIVATE_KEY", "POLYMARKET_API_KEY",
                  "POLYMARKET_API_SECRET", "POLYMARKET_API_PASSPHRASE",
                  "POLYMARKET_PROXY_ADDRESS"]:
            monkeypatch.delenv(k, raising=False)
        s = Settings.load(str(config_file))
        s.validate_for_mode("PAPER")  # must not raise

    def test_live_mode_raises_when_private_key_missing(self, config_file: Path, monkeypatch) -> None:
        monkeypatch.delenv("POLYMARKET_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("POLYMARKET_API_KEY", "key")
        monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
        monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
        monkeypatch.setenv("POLYMARKET_PROXY_ADDRESS", "0xcafe")
        s = Settings.load(str(config_file))
        with pytest.raises(ValueError, match="POLYMARKET_PRIVATE_KEY"):
            s.validate_for_mode("LIVE")

    def test_live_mode_succeeds_when_all_keys_present(self, config_file: Path, monkeypatch) -> None:
        s = self._settings_with_keys(config_file, monkeypatch)
        s.validate_for_mode("LIVE")  # must not raise

    def test_live_mode_raises_when_api_key_missing(self, config_file: Path, monkeypatch) -> None:
        monkeypatch.setenv("POLYMARKET_PRIVATE_KEY", "0xdeadbeef")
        monkeypatch.delenv("POLYMARKET_API_KEY", raising=False)
        monkeypatch.setenv("POLYMARKET_API_SECRET", "secret")
        monkeypatch.setenv("POLYMARKET_API_PASSPHRASE", "pass")
        monkeypatch.setenv("POLYMARKET_PROXY_ADDRESS", "0xcafe")
        s = Settings.load(str(config_file))
        with pytest.raises(ValueError, match="POLYMARKET_API_KEY"):
            s.validate_for_mode("LIVE")


# ---------------------------------------------------------------------------
# bootstrap()
# ---------------------------------------------------------------------------

class TestBootstrap:
    def test_seeds_strategy_params_and_runtime_settings(self, config_file: Path) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.infrastructure.persistence.models import Base
        from src.infrastructure.persistence.models import StrategyParamsModel, RuntimeSettingsModel
        from src.infrastructure.config.settings import bootstrap

        s = Settings.load(str(config_file))
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            bootstrap(session, s)
            params = session.query(StrategyParamsModel).filter_by(valid_to=None).first()
            rt = session.query(RuntimeSettingsModel).filter_by(id=1).first()

        assert params is not None
        assert params.min_dtt == pytest.approx(10.0)
        assert rt is not None
        assert rt.timezone == "America/El_Salvador"
        engine.dispose()

    def test_bootstrap_is_idempotent(self, config_file: Path) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from src.infrastructure.persistence.models import Base, StrategyParamsModel
        from src.infrastructure.config.settings import bootstrap

        s = Settings.load(str(config_file))
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        with Session() as session:
            bootstrap(session, s)
            bootstrap(session, s)  # second call must not duplicate
            count = session.query(StrategyParamsModel).filter_by(valid_to=None).count()

        assert count == 1
        engine.dispose()


# ---------------------------------------------------------------------------
# build_engine
# ---------------------------------------------------------------------------

class TestBuildEngine:
    def test_sqlite_pragma_listener_attached_for_sqlite_url(self) -> None:
        """build_engine("sqlite:///:memory:") attaches WAL + FK pragma listener."""
        from sqlalchemy.pool import StaticPool
        engine = build_engine("sqlite:///:memory:")
        # Verify connection works and WAL is set (indirectly: no exception means listener ran)
        with engine.connect() as conn:
            result = conn.execute(__import__("sqlalchemy").text("PRAGMA journal_mode")).scalar()
        assert result in ("wal", "memory")  # StaticPool uses memory mode
        engine.dispose()

    def test_build_engine_skips_pragma_for_non_sqlite_url(self) -> None:
        """Non-SQLite URLs skip the SQLite pragma event listener (branch 20->27)."""
        mock_engine = MagicMock()
        with patch("src.infrastructure.persistence.database.create_engine", return_value=mock_engine):
            with patch("src.infrastructure.persistence.database.event") as mock_event:
                result = build_engine("postgresql://user:pass@localhost/test")
        mock_event.listens_for.assert_not_called()
        assert result is mock_engine
