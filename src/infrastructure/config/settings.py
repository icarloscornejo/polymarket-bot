from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Sub-config dataclasses (one per config.yml section)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategyDefaults:
    entry_window_min_sec: int
    entry_window_max_sec: int
    min_dtt: float
    min_gain_usd: float
    position_size_usd: float
    snapshot_interval_ms: int
    logging_window_buffer_sec: int


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str
    btc_feed_primary: str
    btc_feed_fallback: str
    btc_feed_failover_threshold_sec: int
    market_discovery_websocket: bool
    market_discovery_rest_interval_sec: int
    timezone_default: str


@dataclass(frozen=True)
class CleanupConfig:
    snapshots_retention_days: int
    daily_run_hour_local: int


@dataclass(frozen=True)
class StorageConfig:
    sqlite_path: str


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    json: bool


# ---------------------------------------------------------------------------
# Top-level Settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    strategy_defaults: StrategyDefaults
    runtime: RuntimeConfig
    cleanup: CleanupConfig
    storage: StorageConfig
    logging: LoggingConfig

    # From environment
    api_host: str
    api_port: int
    polymarket_private_key: str | None
    polymarket_proxy_address: str | None
    polymarket_api_key: str | None
    polymarket_api_secret: str | None
    polymarket_api_passphrase: str | None

    @classmethod
    def load(cls, config_path: str) -> Settings:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with path.open() as f:
            raw = yaml.safe_load(f)

        sd = raw["strategy_defaults"]
        rt = raw["runtime"]
        cl = raw["cleanup"]

        return cls(
            strategy_defaults=StrategyDefaults(
                entry_window_min_sec=sd["entry_window_min_sec"],
                entry_window_max_sec=sd["entry_window_max_sec"],
                min_dtt=float(sd["min_dtt"]),
                min_gain_usd=float(sd["min_gain_usd"]),
                position_size_usd=float(sd["position_size_usd"]),
                snapshot_interval_ms=int(sd["snapshot_interval_ms"]),
                logging_window_buffer_sec=int(sd["logging_window_buffer_sec"]),
            ),
            runtime=RuntimeConfig(
                mode=rt["mode"],
                btc_feed_primary=rt["btc_feed_primary"],
                btc_feed_fallback=rt["btc_feed_fallback"],
                btc_feed_failover_threshold_sec=int(rt["btc_feed_failover_threshold_sec"]),
                market_discovery_websocket=bool(rt["market_discovery_websocket"]),
                market_discovery_rest_interval_sec=int(rt["market_discovery_rest_interval_sec"]),
                timezone_default=rt["timezone_default"],
            ),
            cleanup=CleanupConfig(
                snapshots_retention_days=int(cl["snapshots_retention_days"]),
                daily_run_hour_local=int(cl["daily_run_hour_local"]),
            ),
            storage=StorageConfig(sqlite_path=raw["storage"]["sqlite_path"]),
            logging=LoggingConfig(
                level=raw["logging"]["level"],
                json=bool(raw["logging"]["json"]),
            ),
            api_host=os.environ.get("API_HOST", "127.0.0.1"),
            api_port=int(os.environ.get("API_PORT", "8000")),
            polymarket_private_key=os.environ.get("POLYMARKET_PRIVATE_KEY") or None,
            polymarket_proxy_address=os.environ.get("POLYMARKET_PROXY_ADDRESS") or None,
            polymarket_api_key=os.environ.get("POLYMARKET_API_KEY") or None,
            polymarket_api_secret=os.environ.get("POLYMARKET_API_SECRET") or None,
            polymarket_api_passphrase=os.environ.get("POLYMARKET_API_PASSPHRASE") or None,
        )

    def validate_for_mode(self, mode: str) -> None:
        """Raise ValueError if required credentials are missing for the given mode."""
        if mode != "LIVE":
            return

        required = {
            "POLYMARKET_PRIVATE_KEY": self.polymarket_private_key,
            "POLYMARKET_API_KEY": self.polymarket_api_key,
            "POLYMARKET_API_SECRET": self.polymarket_api_secret,
            "POLYMARKET_API_PASSPHRASE": self.polymarket_api_passphrase,
            "POLYMARKET_PROXY_ADDRESS": self.polymarket_proxy_address,
        }
        for name, value in required.items():
            if not value:
                raise ValueError(
                    f"LIVE mode requires {name} to be set in the environment."
                )


# ---------------------------------------------------------------------------
# Bootstrap — seed DB with defaults from config
# ---------------------------------------------------------------------------

def bootstrap(session: object, settings: Settings) -> None:
    """Seed strategy_params and runtime_settings from config if tables are empty."""
    from src.infrastructure.persistence.database import seed_defaults

    seed_defaults(
        session=session,  # type: ignore[arg-type]
        default_timezone=settings.runtime.timezone_default,
        strategy_defaults={
            "entry_window_min_sec": settings.strategy_defaults.entry_window_min_sec,
            "entry_window_max_sec": settings.strategy_defaults.entry_window_max_sec,
            "min_dtt": settings.strategy_defaults.min_dtt,
            "min_gain_usd": settings.strategy_defaults.min_gain_usd,
            "position_size_usd": settings.strategy_defaults.position_size_usd,
            "snapshot_interval_ms": settings.strategy_defaults.snapshot_interval_ms,
            "logging_window_buffer_sec": settings.strategy_defaults.logging_window_buffer_sec,
        },
    )
