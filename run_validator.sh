#!/bin/bash
# Validator runner for pm2 - uses tau validate (king-of-the-hill)
set -euo pipefail

cd /mnt/global/buff/arbos/workspace/swe/tau
source /mnt/global/buff/arbos/workspace/swe/.venv/bin/activate

export OPENROUTER_API_KEY="$OPENROUTER_KEY"
export CURSOR_API_KEY="$CURSOR_API_KEY"
export GITHUB_TOKEN="$ARBOS_GITHUH_TOKEN"
export PYTHONUNBUFFERED=1

exec python -u -m src.cli validate \
  --wallet-name sn66 \
  --wallet-hotkey sn66_hk \
  --netuid 66 \
  --rounds 3 \
  --concurrency 2 \
  --agent-timeout 300 \
  --weight-interval-blocks 360 \
  --poll-interval-seconds 60 \
  --workspace-root /mnt/global/buff/arbos/workspace/swe/workspace \
  2>&1
