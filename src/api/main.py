"""FastAPI application factory."""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.api.dependencies import AppState, get_app_state, get_session
from src.api.routers import maintenance, performance, settings, signals, snapshots, strategy, trades
from src.infrastructure.persistence.runtime_settings_repository_impl import RuntimeSettingsRepositoryImpl
from src.infrastructure.persistence.strategy_params_repository_impl import StrategyParamsRepositoryImpl


def create_app(state: AppState, session_factory: Any) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Polymarket Bot API")

    # Store shared state directly so dependencies can access it immediately
    app.state.app_state = state
    app.state.session_factory = session_factory

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health(
        app_state: AppState = Depends(get_app_state),
        session: Session = Depends(get_session),
    ) -> dict:
        params_id = StrategyParamsRepositoryImpl(session).get_current_id()
        tz = RuntimeSettingsRepositoryImpl(session).get().timezone
        return {
            "status": "ok",
            "mode": app_state.mode,
            "current_params_id": params_id,
            "timezone": tz,
            "btc_feed_active": app_state.btc_feed_active,
        }

    app.include_router(signals.router)
    app.include_router(trades.router)
    app.include_router(snapshots.router)
    app.include_router(strategy.router)
    app.include_router(performance.router)
    app.include_router(settings.router)
    app.include_router(maintenance.router)

    return app
