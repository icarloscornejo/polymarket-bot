from __future__ import annotations

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Index, Integer, String, Text,
    UniqueConstraint, CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class MarketSnapshotModel(Base):
    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    market_id = Column(String, nullable=False)
    time_to_close_sec = Column(Integer, nullable=False)
    btc_price = Column(Float, nullable=False)
    btc_price_source = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)
    dtt = Column(Float, nullable=False)
    yes_price = Column(Float, nullable=False)
    no_price = Column(Float, nullable=False)
    spread = Column(Float, nullable=False)
    book_depth_yes = Column(Float, nullable=False)
    book_depth_no = Column(Float, nullable=False)
    book_levels_yes = Column(Text, nullable=False)  # JSON
    book_levels_no = Column(Text, nullable=False)   # JSON
    potential_gain_yes = Column(Float, nullable=False)
    potential_gain_no = Column(Float, nullable=False)
    strategy_params_id = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_snapshots_market_time", "market_id", "timestamp"),
        Index("idx_snapshots_timestamp", "timestamp"),
    )


class SignalEventModel(Base):
    __tablename__ = "signal_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False)
    market_id = Column(String, nullable=False)
    side = Column(String, nullable=False)
    yes_price = Column(Float, nullable=False)
    no_price = Column(Float, nullable=False)
    btc_price = Column(Float, nullable=False)
    btc_price_source = Column(String, nullable=False)
    dtt = Column(Float, nullable=False)
    time_to_close_sec = Column(Integer, nullable=False)
    potential_gain = Column(Float, nullable=False)
    action_taken = Column(String, nullable=False)
    skip_reason = Column(String, nullable=True)
    strategy_params_id = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_signals_market_time", "market_id", "timestamp"),
    )


class TradeModel(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False)
    market_id = Column(String, nullable=False)
    side = Column(String, nullable=False)
    entry_price = Column(Float, nullable=False)
    entry_btc_price = Column(Float, nullable=False)
    entry_dtt = Column(Float, nullable=False)
    entry_time_to_close = Column(Integer, nullable=False)
    position_size_usd = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    exit_price = Column(Float, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    pnl_usd = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    mode = Column(String, nullable=False)
    opened_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_trades_market", "market_id"),
        Index("idx_trades_status_mode", "status", "mode"),
        Index("idx_trades_resolved_at", "resolved_at"),
    )


class MarketResolutionModel(Base):
    __tablename__ = "market_resolutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, nullable=False, unique=True)
    resolved_at = Column(DateTime, nullable=False)
    threshold = Column(Float, nullable=False)
    btc_price_at_close = Column(Float, nullable=False)
    btc_price_source = Column(String, nullable=False)
    outcome = Column(String, nullable=False)
    had_position = Column(Boolean, nullable=False, default=False)


class StrategyParamsModel(Base):
    __tablename__ = "strategy_params"

    id = Column(Integer, primary_key=True, autoincrement=True)
    valid_from = Column(DateTime, nullable=False)
    valid_to = Column(DateTime, nullable=True)
    entry_window_min_sec = Column(Integer, nullable=False)
    entry_window_max_sec = Column(Integer, nullable=False)
    min_dtt = Column(Float, nullable=False)
    min_gain_usd = Column(Float, nullable=False)
    position_size_usd = Column(Float, nullable=False)
    snapshot_interval_ms = Column(Integer, nullable=False, default=1000)
    logging_window_buffer_sec = Column(Integer, nullable=False, default=10)
    updated_by = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_strategy_params_valid", "valid_from", "valid_to"),
    )


class RuntimeSettingsModel(Base):
    __tablename__ = "runtime_settings"

    id = Column(Integer, primary_key=True)  # singleton: always id=1
    timezone = Column(String, nullable=False, default="America/El_Salvador")
    updated_at = Column(DateTime, nullable=False)


class MarketSummaryModel(Base):
    __tablename__ = "market_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, nullable=False, unique=True)
    archived_at = Column(DateTime, nullable=False)
    closes_at = Column(DateTime, nullable=False)
    threshold = Column(Float, nullable=False)
    outcome = Column(String, nullable=True)
    snapshots_count = Column(Integer, nullable=False)
    btc_price_min = Column(Float, nullable=False)
    btc_price_max = Column(Float, nullable=False)
    btc_price_avg = Column(Float, nullable=False)
    btc_price_at_close = Column(Float, nullable=True)
    dtt_min = Column(Float, nullable=False)
    dtt_max = Column(Float, nullable=False)
    dtt_avg = Column(Float, nullable=False)
    yes_price_min = Column(Float, nullable=False)
    yes_price_max = Column(Float, nullable=False)
    yes_price_avg = Column(Float, nullable=False)
    no_price_min = Column(Float, nullable=False)
    no_price_max = Column(Float, nullable=False)
    no_price_avg = Column(Float, nullable=False)
    spread_avg = Column(Float, nullable=False)
    book_depth_yes_avg = Column(Float, nullable=False)
    book_depth_no_avg = Column(Float, nullable=False)
    signals_count = Column(Integer, nullable=False, default=0)
    signals_entered = Column(Integer, nullable=False, default=0)
    trades_count = Column(Integer, nullable=False, default=0)
    trades_pnl_usd = Column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("idx_market_summaries_closes_at", "closes_at"),
    )


class DailySummaryModel(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False, unique=True)
    total_markets_archived = Column(Integer, nullable=False)
    total_snapshots_archived = Column(Integer, nullable=False)
    total_signals = Column(Integer, nullable=False)
    signals_entered = Column(Integer, nullable=False)
    signals_skipped = Column(Integer, nullable=False)
    paper_trades_count = Column(Integer, nullable=False)
    paper_winning_trades = Column(Integer, nullable=False)
    paper_pnl_usd = Column(Float, nullable=False)
    paper_invested_usd = Column(Float, nullable=False)
    live_trades_count = Column(Integer, nullable=False)
    live_winning_trades = Column(Integer, nullable=False)
    live_pnl_usd = Column(Float, nullable=False)
    live_invested_usd = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    cleanup_ran_at = Column(DateTime, nullable=False)


class PerformanceSnapshotModel(Base):
    __tablename__ = "performance_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_signals = Column(Integer, nullable=False)
    signals_entered = Column(Integer, nullable=False)
    signals_skipped = Column(Integer, nullable=False)
    paper_pnl = Column(Float, nullable=False)
    live_pnl = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    avg_dtt_on_entry = Column(Float, nullable=True)
    avg_time_to_close_on_entry = Column(Float, nullable=True)
