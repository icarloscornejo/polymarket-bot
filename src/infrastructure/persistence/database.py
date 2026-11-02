from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.persistence.models import (
    Base,
    RuntimeSettingsModel,
    StrategyParamsModel,
)


def build_engine(url: str) -> Engine:
    engine = create_engine(url, echo=False)
    # Enable WAL mode and foreign keys for SQLite
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_conn: Any, _: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def init_schema(engine: Engine) -> None:
    """Create all tables if they do not exist (idempotent)."""
    Base.metadata.create_all(engine)


def seed_defaults(
    session: Session,
    default_timezone: str = "America/El_Salvador",
    strategy_defaults: dict | None = None,
) -> None:
    """Seed strategy_params and runtime_settings if they are empty."""
    _seed_strategy_params(session, strategy_defaults or {})
    _seed_runtime_settings(session, default_timezone)
    session.commit()


def _seed_strategy_params(session: Session, defaults: dict) -> None:
    existing = session.query(StrategyParamsModel).filter_by(valid_to=None).first()
    if existing is not None:
        return
    now = datetime.now(tz=timezone.utc)
    session.add(StrategyParamsModel(
        valid_from=now,
        valid_to=None,
        entry_window_min_sec=defaults.get("entry_window_min_sec", 5),
        entry_window_max_sec=defaults.get("entry_window_max_sec", 25),
        min_dtt=defaults.get("min_dtt", 10.0),
        min_gain_usd=defaults.get("min_gain_usd", 0.75),
        position_size_usd=defaults.get("position_size_usd", 10.0),
        snapshot_interval_ms=defaults.get("snapshot_interval_ms", 1000),
        logging_window_buffer_sec=defaults.get("logging_window_buffer_sec", 10),
        updated_by="CONFIG",
    ))


def _seed_runtime_settings(session: Session, timezone_str: str) -> None:
    existing = session.query(RuntimeSettingsModel).filter_by(id=1).first()
    if existing is not None:
        return
    session.add(RuntimeSettingsModel(
        id=1,
        timezone=timezone_str,
        updated_at=datetime.now(tz=timezone.utc),
    ))


def make_session_factory(url: str) -> sessionmaker:
    engine = build_engine(url)
    init_schema(engine)
    return sessionmaker(bind=engine)
