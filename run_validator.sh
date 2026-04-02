#!/bin/bash
# Validator runner for pm2 - uses tau validate (king-of-the-hill)
set -euo pipefail

cd /mnt/global/buff/arbos/workspace/swe/tau
source /mnt/global/buff/arbos/workspace/swe/.venv/bin/activate

exec sg docker "OPENROUTER_API_KEY=$OPENROUTER_KEY CURSOR_API_KEY=$CURSOR_API_KEY python -m src.cli validate \
  --wallet-name sn66 \
  --wallet-hotkey sn66_hk \
  --netuid 66 \
  --rounds 3 \
  --concurrency 2 \
  --agent-timeout 300 \
  --weight-interval-blocks 360 \
  --poll-interval-seconds 60 \
  --workspace-root /mnt/global/buff/arbos/workspace/swe/workspace"
