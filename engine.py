import sys
import numpy as np
import pandas as pd
import yfinance as yf

import config

sys.path.insert(0, config.KRONOS_PATH)
from model import Kronos, KronosTokenizer, KronosPredictor  # noqa: E402


def load_predictor():
    tokenizer = KronosTokenizer.from_pretrained(config.TOKENIZER_ID)
    model = Kronos.from_pretrained(config.MODEL_ID)
    return KronosPredictor(model, tokenizer, device=config.DEVICE, max_context=config.MAX_CONTEXT)


def fetch_history(ticker):
    raw = yf.Ticker(ticker).history(period="2y", interval="1d").reset_index()
    raw = raw.rename(columns={"Date": "timestamps", "Open": "open", "High": "high",
                               "Low": "low", "Close": "close", "Volume": "volume"})
    raw["timestamps"] = pd.to_datetime(raw["timestamps"]).dt.tz_localize(None)
    raw["amount"] = raw["volume"] * raw["close"]
    df = raw[["timestamps", "open", "high", "low", "close", "volume", "amount"]]
    if len(df) < config.LOOKBACK:
        raise ValueError(f"Not enough history for {ticker}: got {len(df)} rows, need {config.LOOKBACK}.")
    return df.tail(config.LOOKBACK).reset_index(drop=True)


def run_forecast(predictor, df):
    x_df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]
    x_timestamp = df['timestamps']
    last_date = df['timestamps'].iloc[-1]
    y_timestamp = pd.Series(pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=config.PRED_LEN))

    close_paths = []
    for _ in range(config.N_PATHS):
        pred_df = predictor.predict(df=x_df, x_timestamp=x_timestamp, y_timestamp=y_timestamp,
                                     pred_len=config.PRED_LEN, T=config.TEMPERATURE, top_p=config.TOP_P,
                                     sample_count=1, verbose=False)
        close_paths.append(pred_df['close'].values)
    close_paths = np.array(close_paths)
    return close_paths, y_timestamp


def _horizon_stats(close_paths, last_close, horizon_idx):
    finals = close_paths[:, horizon_idx]
    returns = (finals - last_close) / last_close
    expected_return = returns.mean()
    prob_up = (finals > last_close).mean()
    return expected_return, prob_up


def _plausibility_bound(horizon_days, hist_vol):
    """Rough ceiling on a 'realistic' move over horizon_days, from historical daily
    volatility scaled by sqrt(time). Kronos's autoregressive sampling can drift well
    beyond this on long horizons; moves past it get flagged rather than trusted."""
    return hist_vol * np.sqrt(horizon_days) * config.PLAUSIBILITY_STD_MULT


def _tag_plausibility(signal, expected_return, horizon_days, hist_vol):
    bound = _plausibility_bound(horizon_days, hist_vol)
    if abs(expected_return) > bound:
        signal["label"] += " (unreliable)"
        signal["detail"] += (f". Flagged unreliable: {abs(expected_return)*100:.1f}% exceeds the "
                              f"~{bound*100:.1f}% plausible range for {horizon_days}d given recent volatility "
                              f"— likely model drift, not a real signal.")
    return signal


def compute_signals(ticker, df, close_paths):
    last_close = df['close'].iloc[-1]
    hist_vol = df['close'].pct_change().dropna().std()

    sma200 = df['close'].mean()  # lookback window is exactly 200 trading days
    sma20 = df['close'].tail(20).mean()
    std20 = df['close'].tail(20).std()

    exp_ret_1, prob_1 = _horizon_stats(close_paths, last_close, 0)
    swing_idx = min(config.SWING_HORIZON_DAYS - 1, close_paths.shape[1] - 1)
    exp_ret_swing, prob_swing = _horizon_stats(close_paths, last_close, swing_idx)
    exp_ret_30, prob_30 = _horizon_stats(close_paths, last_close, close_paths.shape[1] - 1)

    path_returns = np.diff(close_paths, axis=1) / close_paths[:, :-1]
    vol_amp_prob = (path_returns.std(axis=1) > hist_vol).mean()

    signals = []

    # 1. Daytrade
    direction_prob = prob_1 if exp_ret_1 >= 0 else (1 - prob_1)
    if abs(exp_ret_1) >= config.DAYTRADE_RETURN_THRESH and direction_prob >= config.DAYTRADE_PROB_THRESH:
        signals.append(_tag_plausibility({
            "bucket": "daytrade",
            "label": "Bullish" if exp_ret_1 > 0 else "Bearish",
            "confidence": round(direction_prob * 100, 1),
            "expected_return_pct": round(exp_ret_1 * 100, 2),
            "detail": f"Day-1 expected move {exp_ret_1*100:+.2f}%, {direction_prob*100:.0f}% of paths agree",
        }, exp_ret_1, 1, hist_vol))

    # 2. Swing
    direction_prob = prob_swing if exp_ret_swing >= 0 else (1 - prob_swing)
    swing_horizon_days = swing_idx + 1
    if abs(exp_ret_swing) >= config.SWING_RETURN_THRESH and direction_prob >= config.SWING_PROB_THRESH:
        signals.append(_tag_plausibility({
            "bucket": "swing",
            "label": "Bullish" if exp_ret_swing > 0 else "Bearish",
            "confidence": round(direction_prob * 100, 1),
            "expected_return_pct": round(exp_ret_swing * 100, 2),
            "detail": f"{config.SWING_HORIZON_DAYS}-day expected move {exp_ret_swing*100:+.2f}%, "
                      f"{direction_prob*100:.0f}% of paths agree",
        }, exp_ret_swing, swing_horizon_days, hist_vol))

    # 3. 200-day trend (always reported, not gated by a threshold)
    trend_dir = "above" if last_close > sma200 else "below"
    forecast_dir = "up" if exp_ret_30 > 0 else "down"
    confirmed = (trend_dir == "above" and forecast_dir == "up") or (trend_dir == "below" and forecast_dir == "down")
    trend_horizon_days = close_paths.shape[1]
    signals.append(_tag_plausibility({
        "bucket": "trend_200d",
        "label": "Confirmed" if confirmed else "Diverging",
        "confidence": round(max(prob_30, 1 - prob_30) * 100, 1),
        "expected_return_pct": round(exp_ret_30 * 100, 2),
        "detail": f"Price is {trend_dir} 200-day avg (${sma200:.2f}); 30-day forecast trends {forecast_dir} "
                  f"({exp_ret_30*100:+.2f}%) — {'confirms' if confirmed else 'diverges from'} the trend",
    }, exp_ret_30, trend_horizon_days, hist_vol))

    # 4. Volatility breakout
    if vol_amp_prob >= config.VOL_BREAKOUT_PROB_THRESH:
        signals.append({
            "bucket": "vol_breakout",
            "label": "Breakout candidate",
            "confidence": round(vol_amp_prob * 100, 1),
            "expected_return_pct": None,
            "detail": f"{vol_amp_prob*100:.0f}% of paths show higher volatility than recent history "
                      f"(direction ambiguous)",
        })

    # 5. Mean-reversion
    if std20 and std20 > 0:
        z = (last_close - sma20) / std20
        if abs(z) >= config.MEANREV_Z_THRESH:
            if z > 0:
                reversion_prob = 1 - prob_swing  # expecting a decline back toward mean
                expected = exp_ret_swing
            else:
                reversion_prob = prob_swing  # expecting a rise back toward mean
                expected = exp_ret_swing
            if reversion_prob >= config.MEANREV_PROB_THRESH:
                signals.append(_tag_plausibility({
                    "bucket": "mean_reversion",
                    "label": "Reversion candidate (down)" if z > 0 else "Reversion candidate (up)",
                    "confidence": round(reversion_prob * 100, 1),
                    "expected_return_pct": round(expected * 100, 2),
                    "detail": f"Price is {abs(z):.1f} std devs {'above' if z > 0 else 'below'} its 20-day "
                              f"average; forecast leans toward reversion",
                }, expected, swing_idx + 1, hist_vol))

    return signals
