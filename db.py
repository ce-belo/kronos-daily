import sqlite3
import json
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    bucket TEXT NOT NULL,
    label TEXT NOT NULL,
    confidence REAL,
    expected_return_pct REAL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS daily_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    ticker TEXT NOT NULL,
    last_close REAL,
    forecast_dates TEXT,   -- JSON list of ISO dates
    mean_close TEXT,       -- JSON list
    low_close TEXT,        -- JSON list (10th pct)
    high_close TEXT,       -- JSON list (90th pct)
    history_dates TEXT,    -- JSON list
    history_close TEXT     -- JSON list
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def save_signals(run_date, ticker, signals):
    with connect() as conn:
        # Replace, don't accumulate, if this (date, ticker) was already run today
        conn.execute("DELETE FROM daily_signals WHERE run_date = ? AND ticker = ?", (run_date, ticker))
        conn.executemany(
            """INSERT INTO daily_signals (run_date, ticker, bucket, label, confidence, expected_return_pct, detail)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(run_date, ticker, s["bucket"], s["label"], s["confidence"], s["expected_return_pct"], s["detail"])
             for s in signals],
        )


def save_forecast(run_date, ticker, last_close, forecast_dates, mean_close, low_close, high_close,
                   history_dates, history_close):
    with connect() as conn:
        conn.execute("DELETE FROM daily_forecasts WHERE run_date = ? AND ticker = ?", (run_date, ticker))
        conn.execute(
            """INSERT INTO daily_forecasts (run_date, ticker, last_close, forecast_dates, mean_close,
               low_close, high_close, history_dates, history_close)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_date, ticker, last_close,
             json.dumps(forecast_dates), json.dumps(mean_close), json.dumps(low_close), json.dumps(high_close),
             json.dumps(history_dates), json.dumps(history_close)),
        )


def latest_run_date():
    with connect() as conn:
        row = conn.execute("SELECT MAX(run_date) FROM daily_signals").fetchone()
        return row[0] if row else None


def signals_for_date(run_date):
    with connect() as conn:
        cur = conn.execute(
            "SELECT ticker, bucket, label, confidence, expected_return_pct, detail "
            "FROM daily_signals WHERE run_date = ? ORDER BY ticker, bucket", (run_date,)
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def forecast_for(run_date, ticker):
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM daily_forecasts WHERE run_date = ? AND ticker = ? ORDER BY id DESC LIMIT 1",
            (run_date, ticker),
        )
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None


def all_run_dates():
    with connect() as conn:
        cur = conn.execute("SELECT DISTINCT run_date FROM daily_signals ORDER BY run_date")
        return [r[0] for r in cur.fetchall()]


def history_for_ticker(ticker):
    with connect() as conn:
        cur = conn.execute(
            "SELECT run_date, bucket, label, confidence, expected_return_pct "
            "FROM daily_signals WHERE ticker = ? ORDER BY run_date", (ticker,)
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
