#!/usr/bin/env bash
# illinoisK Strategy Data Pipeline
# Runs: collect_realtime.py → strategy_generator.py
# Called by: cronjob (토 06:00 KST — US market close 반영)
set -e
cd /mnt/g/Ddrive/BatangD/task/workdiary/illinoisK

echo "[$(date)] Starting strategy pipeline..."
echo ""

echo "=== Step 1: Collect realtime prices ==="
python3 scripts/collect_realtime.py 2>&1 | tail -3
echo ""

echo "=== Step 2: Generate strategy data ==="
python3 scripts/strategy_generator.py 2>&1 | tail -5
echo ""

echo "[$(date)] Pipeline complete."
