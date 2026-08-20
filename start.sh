#!/bin/bash
cd "$(dirname "$0")"
source ~/Desktop/Kronos/venv/bin/activate
streamlit run dashboard.py < /dev/null
