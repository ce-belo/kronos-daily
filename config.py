import os

from settings import load_settings

# Path to the Kronos repo (for importing model code and its venv's site-packages)
KRONOS_PATH = os.path.expanduser("~/Desktop/Kronos")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.db")

_s = load_settings()

# --- Watchlist -------------------------------------------------------------
WATCHLIST = _s["watchlist"]

# --- Model / forecast settings ----------------------------------------------
MODEL_ID = _s["model_id"]
TOKENIZER_ID = _s["tokenizer_id"]
MAX_CONTEXT = _s["max_context"]
DEVICE = _s["device"]

LOOKBACK = _s["lookback"]
PRED_LEN = _s["pred_len"]
N_PATHS = _s["n_paths"]
TEMPERATURE = _s["temperature"]
TOP_P = _s["top_p"]

# --- Signal thresholds (tunable) --------------------------------------------
DAYTRADE_RETURN_THRESH = _s["daytrade_return_thresh"]
DAYTRADE_PROB_THRESH = _s["daytrade_prob_thresh"]

SWING_HORIZON_DAYS = _s["swing_horizon_days"]
SWING_RETURN_THRESH = _s["swing_return_thresh"]
SWING_PROB_THRESH = _s["swing_prob_thresh"]

VOL_BREAKOUT_PROB_THRESH = _s["vol_breakout_prob_thresh"]

MEANREV_Z_THRESH = _s["meanrev_z_thresh"]
MEANREV_PROB_THRESH = _s["meanrev_prob_thresh"]

# --- Plausibility guardrail -------------------------------------------------
# Kronos's autoregressive sampling can drift into unrealistic long-horizon moves
# (e.g. -50%+ over 30 days). Flag any expected return beyond
# hist_daily_vol * sqrt(horizon_days) * PLAUSIBILITY_STD_MULT as "unreliable"
# instead of presenting it as a clean directional signal.
PLAUSIBILITY_STD_MULT = _s["plausibility_std_mult"]

# --- Schedule ----------------------------------------------------------------
RUN_HOUR = _s["run_hour"]
RUN_MINUTE = _s["run_minute"]
WEEKDAYS_ONLY = _s["weekdays_only"]
