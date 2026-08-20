import os
import subprocess
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import settings as settings_mod
import run_manager

st.set_page_config(page_title="Kronos — Settings", layout="wide")
st.title("Settings")

cfg = settings_mod.load_settings()

# --- Watchlist ---------------------------------------------------------------
st.subheader("Watchlist")
watchlist_text = st.text_area("Tickers (one per line or comma-separated)",
                               value="\n".join(cfg["watchlist"]), height=120)

# --- Model ---------------------------------------------------------------
st.subheader("Model")
model_keys = list(settings_mod.MODEL_CHOICES.keys())
current_key = next((k for k, v in settings_mod.MODEL_CHOICES.items() if v["model_id"] == cfg["model_id"]),
                    "kronos-base")
model_key = st.selectbox("Kronos model", options=model_keys, index=model_keys.index(current_key),
                          format_func=lambda k: f"{k} ({settings_mod.MODEL_CHOICES[k]['params']} params) — "
                                                 f"{settings_mod.MODEL_CHOICES[k]['note']}")

col1, col2, col3 = st.columns(3)
n_paths = col1.number_input("Simulation paths per ticker", min_value=1, max_value=200, value=cfg["n_paths"])
lookback = col2.number_input("Lookback (trading days)", min_value=50, max_value=1000, value=cfg["lookback"])
pred_len = col3.number_input("Forecast horizon (trading days)", min_value=5, max_value=90, value=cfg["pred_len"])

st.caption(f"Estimated runtime: ~{n_paths * 3.5 / 60:.0f}-{n_paths * 11 / 60:.0f} min per ticker "
           f"({'kronos-base' if 'base' in model_key else model_key} on CPU) — "
           f"~{len(watchlist_text.split()) * n_paths * 3.5 / 60:.0f} min total for this watchlist.")

# --- Signal thresholds ---------------------------------------------------------------
with st.expander("Signal thresholds (advanced)"):
    c1, c2 = st.columns(2)
    daytrade_return = c1.number_input("Daytrade: min expected move (%)", value=cfg["daytrade_return_thresh"] * 100,
                                       step=0.1) / 100
    daytrade_prob = c2.number_input("Daytrade: min path agreement (%)", value=cfg["daytrade_prob_thresh"] * 100,
                                     step=1.0) / 100

    swing_horizon = c1.number_input("Swing horizon (days)", value=cfg["swing_horizon_days"], step=1)
    swing_return = c2.number_input("Swing: min expected move (%)", value=cfg["swing_return_thresh"] * 100,
                                    step=0.1) / 100
    swing_prob = c1.number_input("Swing: min path agreement (%)", value=cfg["swing_prob_thresh"] * 100,
                                  step=1.0) / 100

    vol_thresh = c2.number_input("Volatility breakout: min probability (%)",
                                  value=cfg["vol_breakout_prob_thresh"] * 100, step=1.0) / 100

    meanrev_z = c1.number_input("Mean-reversion: min z-score", value=cfg["meanrev_z_thresh"], step=0.1)
    meanrev_prob = c2.number_input("Mean-reversion: min reversion probability (%)",
                                    value=cfg["meanrev_prob_thresh"] * 100, step=1.0) / 100

    plaus_mult = st.number_input("Plausibility guardrail (std-dev multiplier)",
                                  value=float(cfg["plausibility_std_mult"]), step=0.5,
                                  help="Forecasts beyond hist_vol * sqrt(horizon) * this get flagged 'unreliable'.")

if st.button("Save settings", type="primary"):
    tickers = [t.strip().upper() for t in watchlist_text.replace(",", "\n").splitlines() if t.strip()]
    model_info = settings_mod.MODEL_CHOICES[model_key]
    new_cfg = dict(cfg)
    new_cfg.update({
        "watchlist": tickers,
        "model_id": model_info["model_id"],
        "tokenizer_id": model_info["tokenizer_id"],
        "max_context": model_info["max_context"],
        "n_paths": int(n_paths),
        "lookback": int(lookback),
        "pred_len": int(pred_len),
        "daytrade_return_thresh": daytrade_return,
        "daytrade_prob_thresh": daytrade_prob,
        "swing_horizon_days": int(swing_horizon),
        "swing_return_thresh": swing_return,
        "swing_prob_thresh": swing_prob,
        "vol_breakout_prob_thresh": vol_thresh,
        "meanrev_z_thresh": meanrev_z,
        "meanrev_prob_thresh": meanrev_prob,
        "plausibility_std_mult": plaus_mult,
    })
    settings_mod.save_settings(new_cfg)
    st.success(f"Saved. Watchlist: {', '.join(tickers)}")

st.divider()

# --- Manual run ---------------------------------------------------------------
st.subheader("Run now")
status = run_manager.get_status()

run_col, refresh_col = st.columns([1, 1])
if run_col.button("Run now", disabled=(status.get("status") == "running")):
    run_manager.start_run()
    st.rerun()
if refresh_col.button("Refresh status"):
    st.rerun()

if status.get("status") == "running":
    st.info(f"Run in progress (started {status.get('started_at', '?')}). Click 'Refresh status' to update.")
elif status.get("status") == "done":
    st.success(f"Last run finished {status.get('finished_at', '?')} (started {status.get('started_at', '?')}).")
else:
    st.caption("No run in progress.")

log = run_manager.tail_log()
if log:
    st.text_area("Log (tail)", value=log, height=300)

st.divider()

# --- Schedule ---------------------------------------------------------------
st.subheader("Daily schedule")

PLIST_LABEL = "com.marco.kronos-daily"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_LABEL}.plist")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def schedule_installed():
    result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    return PLIST_LABEL in result.stdout and os.path.exists(PLIST_PATH)


def render_plist(hour, minute, weekdays_only):
    days_xml = ""
    if weekdays_only:
        days_xml = "".join(
            f"<dict><key>Hour</key><integer>{hour}</integer><key>Minute</key><integer>{minute}</integer>"
            f"<key>Weekday</key><integer>{d}</integer></dict>"
            for d in range(1, 6)
        )
        interval_block = f"<key>StartCalendarInterval</key><array>{days_xml}</array>"
    else:
        interval_block = (f"<key>StartCalendarInterval</key>"
                           f"<dict><key>Hour</key><integer>{hour}</integer>"
                           f"<key>Minute</key><integer>{minute}</integer></dict>")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{os.path.join(BASE_DIR, "run_daily.py")}</string>
    </array>
    <key>WorkingDirectory</key><string>{BASE_DIR}</string>
    {interval_block}
    <key>StandardOutPath</key><string>{os.path.join(BASE_DIR, "launchd_stdout.log")}</string>
    <key>StandardErrorPath</key><string>{os.path.join(BASE_DIR, "launchd_stderr.log")}</string>
</dict>
</plist>
"""


hour = st.number_input("Hour (24h)", min_value=0, max_value=23, value=cfg["run_hour"])
minute = st.number_input("Minute", min_value=0, max_value=59, value=cfg["run_minute"])
weekdays_only = st.checkbox("Weekdays only (Mon-Fri)", value=cfg["weekdays_only"])

installed = schedule_installed()
st.caption(f"Schedule currently {'installed' if installed else 'not installed'} "
           f"(target: {hour:02d}:{minute:02d}{' weekdays' if weekdays_only else ' every day'}).")

sched_col1, sched_col2 = st.columns(2)

if sched_col1.button("Install / update schedule"):
    new_cfg = dict(cfg)
    new_cfg.update({"run_hour": int(hour), "run_minute": int(minute), "weekdays_only": weekdays_only})
    settings_mod.save_settings(new_cfg)

    plist_content = render_plist(int(hour), int(minute), weekdays_only)
    with open(PLIST_PATH, "w") as f:
        f.write(plist_content)

    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", PLIST_PATH], capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", PLIST_PATH],
                             capture_output=True, text=True)
    if result.returncode == 0:
        st.success(f"Schedule installed: runs {hour:02d}:{minute:02d}"
                   f"{' on weekdays' if weekdays_only else ' every day'}.")
    else:
        st.error(f"launchctl bootstrap failed: {result.stderr}")
    st.rerun()

if sched_col2.button("Uninstall schedule", disabled=not installed):
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", PLIST_PATH], capture_output=True)
    if os.path.exists(PLIST_PATH):
        os.remove(PLIST_PATH)
    st.success("Schedule uninstalled.")
    st.rerun()
