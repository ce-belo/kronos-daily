"""MCP server exposing Kronos signals, forecasts, run control, and settings.

Run standalone (does not need Streamlit running):
    python mcp_server.py

Then point an MCP client (e.g. Claude Desktop/Code config) at this script.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP

import db
import run_manager
import settings as settings_mod

mcp = FastMCP("kronos-daily")

db.init_db()


# --- Read: signals & forecasts ----------------------------------------------

@mcp.tool()
def list_run_dates() -> list[str]:
    """List all dates for which Kronos signals have been generated, oldest first."""
    return db.all_run_dates()


@mcp.tool()
def get_signals(run_date: str | None = None) -> list[dict]:
    """Get all signals for a run date. Omit run_date to use the latest available run."""
    date = run_date or db.latest_run_date()
    if date is None:
        return []
    return db.signals_for_date(date)


@mcp.tool()
def get_forecast(ticker: str, run_date: str | None = None) -> dict | None:
    """Get the stored forecast (history + predicted mean/low/high close) for a ticker.

    Omit run_date to use the latest available run.
    """
    date = run_date or db.latest_run_date()
    if date is None:
        return None
    return db.forecast_for(date, ticker)


@mcp.tool()
def get_ticker_history(ticker: str) -> list[dict]:
    """Get every past signal recorded for a ticker across all run dates."""
    return db.history_for_ticker(ticker)


# --- Run control --------------------------------------------------------------

@mcp.tool()
def get_run_status() -> dict:
    """Check whether a daily forecast run is currently in progress, and when the last one finished."""
    return run_manager.get_status()


@mcp.tool()
def start_run() -> dict:
    """Kick off a new forecast run for the current watchlist (like the Settings page's 'Run now' button).

    Runs in the background; poll get_run_status() to see when it's done. This can take
    several minutes (roughly n_paths * 3.5-11 seconds per ticker on CPU).
    """
    return run_manager.start_run()


@mcp.tool()
def get_run_log(lines: int = 200) -> str:
    """Tail the log output of the most recent (or currently running) forecast run."""
    return run_manager.tail_log(lines)


# --- Settings -------------------------------------------------------------

@mcp.tool()
def get_settings() -> dict:
    """Get the current Kronos settings: watchlist, model choice, forecast params, and signal thresholds."""
    return settings_mod.load_settings()


@mcp.tool()
def get_model_choices() -> dict:
    """List the available Kronos model choices (id, tokenizer, context length, param count, notes)."""
    return settings_mod.MODEL_CHOICES


@mcp.tool()
def update_settings(changes: dict) -> dict:
    """Update one or more Kronos settings and persist them to settings.json.

    Pass only the keys you want to change, e.g. {"watchlist": ["AAPL", "MSFT"]} or
    {"n_paths": 50, "lookback": 300}. Unknown keys are ignored. Returns the full
    settings after the update. Changes take effect on the next forecast run.
    """
    cfg = settings_mod.load_settings()
    valid_keys = set(settings_mod.DEFAULTS.keys())
    applied = {k: v for k, v in changes.items() if k in valid_keys}
    cfg.update(applied)
    settings_mod.save_settings(cfg)
    return cfg


@mcp.tool()
def set_model(model_key: str) -> dict:
    """Switch the active Kronos model by shorthand name: 'kronos-mini', 'kronos-small', or 'kronos-base'."""
    if model_key not in settings_mod.MODEL_CHOICES:
        raise ValueError(f"Unknown model '{model_key}'. Choices: {list(settings_mod.MODEL_CHOICES)}")
    info = settings_mod.MODEL_CHOICES[model_key]
    cfg = settings_mod.load_settings()
    cfg.update({
        "model_id": info["model_id"],
        "tokenizer_id": info["tokenizer_id"],
        "max_context": info["max_context"],
    })
    settings_mod.save_settings(cfg)
    return cfg


if __name__ == "__main__":
    mcp.run()
