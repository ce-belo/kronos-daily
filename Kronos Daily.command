#!/bin/bash
cd ~/Desktop/kronos-daily
source ~/Desktop/Kronos/venv/bin/activate
nohup streamlit run dashboard.py < /dev/null > streamlit.log 2>&1 &
disown
echo "Kronos dashboard launched in the background (PID $!)."
echo "It will keep running even if you close this window."
echo "Open http://localhost:8501 in your browser."
sleep 3
