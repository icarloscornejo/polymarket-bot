"""FastAPI dependency injection helpers and shared app state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generator

from fastapi import Request
from sqlalchemy.orm import Session


@dataclass
class AppState:
    """Mutable runtime state shared between the API and the bot runner."""

    mode: str = "PAPER"
    btc_feed_active: str = "binance"
    active_markets: list[str] = field(default_factory=list)
    cleanup_run_hour: int = 3


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state  # type: ignore[no-any-return]


def get_session(request: Request) -> Generator[Session, None, None]:
    session: Session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()
