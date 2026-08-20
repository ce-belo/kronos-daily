import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULTS = {
    "watchlist": ["AAPL", "NVDA", "RGTI", "TSLA", "AMD"],

    "model_id": "NeoQuasar/Kronos-base",
    "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
    "max_context": 512,
    "device": "cpu",

    "lookback": 200,
    "pred_len": 30,
    "n_paths": 30,
    "temperature": 1.0,
    "top_p": 0.9,

    "daytrade_return_thresh": 0.005,
    "daytrade_prob_thresh": 0.60,

    "swing_horizon_days": 7,
    "swing_return_thresh": 0.015,
    "swing_prob_thresh": 0.65,

    "vol_breakout_prob_thresh": 0.60,

    "meanrev_z_thresh": 1.5,
    "meanrev_prob_thresh": 0.55,

    "plausibility_std_mult": 3,

    "run_hour": 7,
    "run_minute": 30,
    "weekdays_only": True,
}

MODEL_CHOICES = {
    "kronos-mini": {"model_id": "NeoQuasar/Kronos-mini", "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-2k",
                     "max_context": 2048, "params": "4.1M", "note": "fastest, lowest quality"},
    "kronos-small": {"model_id": "NeoQuasar/Kronos-small", "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
                      "max_context": 512, "params": "24.7M", "note": "fast, decent quality"},
    "kronos-base": {"model_id": "NeoQuasar/Kronos-base", "tokenizer_id": "NeoQuasar/Kronos-Tokenizer-base",
                     "max_context": 512, "params": "102.3M", "note": "slower, best quality (default)"},
}


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULTS)
        return dict(DEFAULTS)
    with open(SETTINGS_PATH) as f:
        data = json.load(f)
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_settings(settings):
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
