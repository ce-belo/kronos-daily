import sys
import time
import datetime

import numpy as np

import config
import db
import engine


def main():
    run_date = datetime.date.today().isoformat()
    print(f"Kronos daily run — {run_date}")
    print(f"Watchlist: {', '.join(config.WATCHLIST)}")

    db.init_db()

    print("Loading model...")
    t0 = time.time()
    predictor = engine.load_predictor()
    print(f"  done in {time.time()-t0:.1f}s")

    for ticker in config.WATCHLIST:
        print(f"\n{ticker}")
        try:
            df = engine.fetch_history(ticker)
        except Exception as e:
            print(f"  skipped: {e}")
            continue

        t0 = time.time()
        close_paths, y_timestamp = engine.run_forecast(predictor, df)
        print(f"  forecast done in {time.time()-t0:.1f}s ({config.N_PATHS} paths)")

        signals = engine.compute_signals(ticker, df, close_paths)
        db.save_signals(run_date, ticker, signals)

        mean_close = close_paths.mean(axis=0)
        low_close = np.percentile(close_paths, 10, axis=0)
        high_close = np.percentile(close_paths, 90, axis=0)
        db.save_forecast(
            run_date, ticker,
            last_close=float(df['close'].iloc[-1]),
            forecast_dates=[d.isoformat() for d in y_timestamp],
            mean_close=mean_close.tolist(),
            low_close=low_close.tolist(),
            high_close=high_close.tolist(),
            history_dates=[d.isoformat() for d in df['timestamps']],
            history_close=df['close'].tolist(),
        )

        if signals:
            for s in signals:
                print(f"  [{s['bucket']}] {s['label']} ({s['confidence']}%) — {s['detail']}")
        else:
            print("  no signals triggered")

    print(f"\nDone. Results saved to {config.DB_PATH}")


if __name__ == "__main__":
    sys.exit(main())
