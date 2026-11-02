"""Pure functions converting between SQLAlchemy models and domain entities/value objects."""
from __future__ import annotations

import json
from datetime import timezone

from src.domain.entities.daily_summary import DailySummary
from src.domain.entities.market_resolution import MarketResolution
from src.domain.entities.market_summary import MarketSummary
from src.domain.entities.runtime_settings import RuntimeSettings
from src.domain.entities.signal import ActionTaken, Signal, SkipReason
from src.domain.entities.snapshot import Snapshot
from src.domain.entities.trade import Trade, TradeMode, TradeStatus
from src.domain.repositories.performance_repository import PerformanceSnapshot
from src.domain.value_objects.strategy_params import StrategyParams
from src.domain.value_objects.time_window import TimeWindow
from src.infrastructure.persistence.models import (
    DailySummaryModel,
    MarketResolutionModel,
    MarketSnapshotModel,
    MarketSummaryModel,
    PerformanceSnapshotModel,
    RuntimeSettingsModel,
    SignalEventModel,
    StrategyParamsModel,
    TradeModel,
)


def _utc(dt) -> object:  # type: ignore[no-untyped-def]
    """Ensure datetime has UTC timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

def signal_to_model(signal: Signal) -> SignalEventModel:
    return SignalEventModel(
        timestamp=signal.timestamp.replace(tzinfo=None),
        market_id=signal.market_id,
        side=signal.side,
        yes_price=signal.yes_price,
        no_price=signal.no_price,
        btc_price=signal.btc_price,
        btc_price_source=signal.btc_price_source,
        dtt=signal.dtt,
        time_to_close_sec=signal.time_to_close_sec,
        potential_gain=signal.potential_gain,
        action_taken=signal.action_taken.value,
        skip_reason=signal.skip_reason.value if signal.skip_reason else None,
        strategy_params_id=signal.strategy_params_id,
    )


def signal_from_model(m: SignalEventModel) -> Signal:
    return Signal(
        timestamp=_utc(m.timestamp),  # type: ignore[arg-type]
        market_id=m.market_id,
        side=m.side,
        yes_price=m.yes_price,
        no_price=m.no_price,
        btc_price=m.btc_price,
        btc_price_source=m.btc_price_source,
        dtt=m.dtt,
        time_to_close_sec=m.time_to_close_sec,
        potential_gain=m.potential_gain,
        action_taken=ActionTaken(m.action_taken),
        skip_reason=SkipReason(m.skip_reason) if m.skip_reason else None,
        strategy_params_id=m.strategy_params_id,
    )


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

def snapshot_to_model(snap: Snapshot) -> MarketSnapshotModel:
    return MarketSnapshotModel(
        timestamp=snap.timestamp.replace(tzinfo=None),
        market_id=snap.market_id,
        time_to_close_sec=snap.time_to_close_sec,
        btc_price=snap.btc_price,
        btc_price_source=snap.btc_price_source,
        threshold=snap.threshold,
        dtt=snap.dtt,
        yes_price=snap.yes_price,
        no_price=snap.no_price,
        spread=snap.spread,
        book_depth_yes=snap.book_depth_yes,
        book_depth_no=snap.book_depth_no,
        book_levels_yes=json.dumps(list(snap.book_levels_yes)),
        book_levels_no=json.dumps(list(snap.book_levels_no)),
        potential_gain_yes=snap.potential_gain_yes,
        potential_gain_no=snap.potential_gain_no,
        strategy_params_id=snap.strategy_params_id,
    )


def snapshot_from_model(m: MarketSnapshotModel) -> Snapshot:
    return Snapshot(
        timestamp=_utc(m.timestamp),  # type: ignore[arg-type]
        market_id=m.market_id,
        time_to_close_sec=m.time_to_close_sec,
        btc_price=m.btc_price,
        btc_price_source=m.btc_price_source,
        threshold=m.threshold,
        dtt=m.dtt,
        yes_price=m.yes_price,
        no_price=m.no_price,
        spread=m.spread,
        book_depth_yes=m.book_depth_yes,
        book_depth_no=m.book_depth_no,
        book_levels_yes=tuple(tuple(level) for level in json.loads(m.book_levels_yes)),
        book_levels_no=tuple(tuple(level) for level in json.loads(m.book_levels_no)),
        potential_gain_yes=m.potential_gain_yes,
        potential_gain_no=m.potential_gain_no,
        strategy_params_id=m.strategy_params_id,
    )


# ---------------------------------------------------------------------------
# Trade
# ---------------------------------------------------------------------------

def trade_to_model(trade: Trade) -> TradeModel:
    return TradeModel(
        signal_id=trade.signal_id,
        market_id=trade.market_id,
        side=trade.side,
        entry_price=trade.entry_price,
        entry_btc_price=trade.entry_btc_price,
        entry_dtt=trade.entry_dtt,
        entry_time_to_close=trade.entry_time_to_close,
        position_size_usd=trade.position_size_usd,
        status=trade.status.value,
        exit_price=trade.exit_price,
        resolved_at=trade.resolved_at.replace(tzinfo=None) if trade.resolved_at else None,
        pnl_usd=trade.pnl_usd,
        pnl_pct=trade.pnl_pct,
        mode=trade.mode.value,
        opened_at=trade.opened_at.replace(tzinfo=None),
    )


def trade_from_model(m: TradeModel) -> Trade:
    return Trade(
        signal_id=m.signal_id,
        market_id=m.market_id,
        side=m.side,
        entry_price=m.entry_price,
        entry_btc_price=m.entry_btc_price,
        entry_dtt=m.entry_dtt,
        entry_time_to_close=m.entry_time_to_close,
        position_size_usd=m.position_size_usd,
        status=TradeStatus(m.status),
        exit_price=m.exit_price,
        resolved_at=_utc(m.resolved_at),  # type: ignore[arg-type]
        pnl_usd=m.pnl_usd,
        pnl_pct=m.pnl_pct,
        mode=TradeMode(m.mode),
        opened_at=_utc(m.opened_at),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# MarketResolution
# ---------------------------------------------------------------------------

def resolution_to_model(r: MarketResolution) -> MarketResolutionModel:
    return MarketResolutionModel(
        market_id=r.market_id,
        resolved_at=r.resolved_at.replace(tzinfo=None),
        threshold=r.threshold,
        btc_price_at_close=r.btc_price_at_close,
        btc_price_source=r.btc_price_source,
        outcome=r.outcome,
        had_position=r.had_position,
    )


def resolution_from_model(m: MarketResolutionModel) -> MarketResolution:
    return MarketResolution(
        market_id=m.market_id,
        resolved_at=_utc(m.resolved_at),  # type: ignore[arg-type]
        threshold=m.threshold,
        btc_price_at_close=m.btc_price_at_close,
        btc_price_source=m.btc_price_source,
        outcome=m.outcome,
        had_position=bool(m.had_position),
    )


# ---------------------------------------------------------------------------
# StrategyParams
# ---------------------------------------------------------------------------

def strategy_params_from_model(m: StrategyParamsModel) -> StrategyParams:
    return StrategyParams(
        entry_window=TimeWindow(
            min_sec=m.entry_window_min_sec,
            max_sec=m.entry_window_max_sec,
        ),
        min_dtt=m.min_dtt,
        min_gain_usd=m.min_gain_usd,
        position_size_usd=m.position_size_usd,
        snapshot_interval_ms=m.snapshot_interval_ms,
        logging_window_buffer_sec=m.logging_window_buffer_sec,
    )


def strategy_params_to_model(
    params: StrategyParams,
    valid_from,  # type: ignore[no-untyped-def]
    valid_to,  # type: ignore[no-untyped-def]
    updated_by: str,
) -> StrategyParamsModel:
    return StrategyParamsModel(
        valid_from=valid_from.replace(tzinfo=None) if valid_from else valid_from,
        valid_to=valid_to.replace(tzinfo=None) if valid_to else None,
        entry_window_min_sec=params.entry_window.min_sec,
        entry_window_max_sec=params.entry_window.max_sec,
        min_dtt=params.min_dtt,
        min_gain_usd=params.min_gain_usd,
        position_size_usd=params.position_size_usd,
        snapshot_interval_ms=params.snapshot_interval_ms,
        logging_window_buffer_sec=params.logging_window_buffer_sec,
        updated_by=updated_by,
    )


# ---------------------------------------------------------------------------
# RuntimeSettings
# ---------------------------------------------------------------------------

def runtime_settings_from_model(m: RuntimeSettingsModel) -> RuntimeSettings:
    return RuntimeSettings(
        timezone=m.timezone,
        updated_at=_utc(m.updated_at),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# MarketSummary
# ---------------------------------------------------------------------------

def market_summary_to_model(s: MarketSummary) -> MarketSummaryModel:
    return MarketSummaryModel(
        market_id=s.market_id,
        archived_at=s.archived_at.replace(tzinfo=None),
        closes_at=s.closes_at.replace(tzinfo=None),
        threshold=s.threshold,
        outcome=s.outcome,
        snapshots_count=s.snapshots_count,
        btc_price_min=s.btc_price_min,
        btc_price_max=s.btc_price_max,
        btc_price_avg=s.btc_price_avg,
        btc_price_at_close=s.btc_price_at_close,
        dtt_min=s.dtt_min,
        dtt_max=s.dtt_max,
        dtt_avg=s.dtt_avg,
        yes_price_min=s.yes_price_min,
        yes_price_max=s.yes_price_max,
        yes_price_avg=s.yes_price_avg,
        no_price_min=s.no_price_min,
        no_price_max=s.no_price_max,
        no_price_avg=s.no_price_avg,
        spread_avg=s.spread_avg,
        book_depth_yes_avg=s.book_depth_yes_avg,
        book_depth_no_avg=s.book_depth_no_avg,
        signals_count=s.signals_count,
        signals_entered=s.signals_entered,
        trades_count=s.trades_count,
        trades_pnl_usd=s.trades_pnl_usd,
    )


def market_summary_from_model(m: MarketSummaryModel) -> MarketSummary:
    return MarketSummary(
        market_id=m.market_id,
        archived_at=_utc(m.archived_at),  # type: ignore[arg-type]
        closes_at=_utc(m.closes_at),  # type: ignore[arg-type]
        threshold=m.threshold,
        outcome=m.outcome,
        snapshots_count=m.snapshots_count,
        btc_price_min=m.btc_price_min,
        btc_price_max=m.btc_price_max,
        btc_price_avg=m.btc_price_avg,
        btc_price_at_close=m.btc_price_at_close,
        dtt_min=m.dtt_min,
        dtt_max=m.dtt_max,
        dtt_avg=m.dtt_avg,
        yes_price_min=m.yes_price_min,
        yes_price_max=m.yes_price_max,
        yes_price_avg=m.yes_price_avg,
        no_price_min=m.no_price_min,
        no_price_max=m.no_price_max,
        no_price_avg=m.no_price_avg,
        spread_avg=m.spread_avg,
        book_depth_yes_avg=m.book_depth_yes_avg,
        book_depth_no_avg=m.book_depth_no_avg,
        signals_count=m.signals_count,
        signals_entered=m.signals_entered,
        trades_count=m.trades_count,
        trades_pnl_usd=m.trades_pnl_usd,
    )


# ---------------------------------------------------------------------------
# DailySummary
# ---------------------------------------------------------------------------

def daily_summary_to_model(ds: DailySummary) -> DailySummaryModel:
    total = ds.paper_trades_count + ds.live_trades_count
    win_rate = (
        (ds.paper_winning_trades + ds.live_winning_trades) / total if total > 0 else 0.0
    )
    return DailySummaryModel(
        date=ds.date,
        total_markets_archived=ds.total_markets_archived,
        total_snapshots_archived=ds.total_snapshots_archived,
        total_signals=ds.total_signals,
        signals_entered=ds.signals_entered,
        signals_skipped=ds.signals_skipped,
        paper_trades_count=ds.paper_trades_count,
        paper_winning_trades=ds.paper_winning_trades,
        paper_pnl_usd=ds.paper_pnl_usd,
        paper_invested_usd=ds.paper_invested_usd,
        live_trades_count=ds.live_trades_count,
        live_winning_trades=ds.live_winning_trades,
        live_pnl_usd=ds.live_pnl_usd,
        live_invested_usd=ds.live_invested_usd,
        win_rate=win_rate,
        cleanup_ran_at=ds.cleanup_ran_at.replace(tzinfo=None),
    )


def daily_summary_from_model(m: DailySummaryModel) -> DailySummary:
    return DailySummary(
        date=m.date,
        total_markets_archived=m.total_markets_archived,
        total_snapshots_archived=m.total_snapshots_archived,
        total_signals=m.total_signals,
        signals_entered=m.signals_entered,
        signals_skipped=m.signals_skipped,
        paper_trades_count=m.paper_trades_count,
        paper_winning_trades=m.paper_winning_trades,
        paper_pnl_usd=m.paper_pnl_usd,
        paper_invested_usd=m.paper_invested_usd,
        live_trades_count=m.live_trades_count,
        live_winning_trades=m.live_winning_trades,
        live_pnl_usd=m.live_pnl_usd,
        live_invested_usd=m.live_invested_usd,
        cleanup_ran_at=_utc(m.cleanup_ran_at),  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# PerformanceSnapshot
# ---------------------------------------------------------------------------

def perf_to_model(p: PerformanceSnapshot) -> PerformanceSnapshotModel:
    return PerformanceSnapshotModel(
        period_start=p.period_start.replace(tzinfo=None),
        period_end=p.period_end.replace(tzinfo=None),
        total_signals=p.total_signals,
        signals_entered=p.signals_entered,
        signals_skipped=p.signals_skipped,
        paper_pnl=p.paper_pnl,
        live_pnl=p.live_pnl,
        win_rate=p.win_rate,
        avg_dtt_on_entry=p.avg_dtt_on_entry,
        avg_time_to_close_on_entry=p.avg_time_to_close_on_entry,
    )


def perf_from_model(m: PerformanceSnapshotModel) -> PerformanceSnapshot:
    return PerformanceSnapshot(
        period_start=_utc(m.period_start),  # type: ignore[arg-type]
        period_end=_utc(m.period_end),  # type: ignore[arg-type]
        total_signals=m.total_signals,
        signals_entered=m.signals_entered,
        signals_skipped=m.signals_skipped,
        paper_pnl=m.paper_pnl,
        live_pnl=m.live_pnl,
        win_rate=m.win_rate,
        avg_dtt_on_entry=m.avg_dtt_on_entry,
        avg_time_to_close_on_entry=m.avg_time_to_close_on_entry,
    )
