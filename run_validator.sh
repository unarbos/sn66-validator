#!/bin/bash
# Validator runner for pm2
set -euo pipefail

cd /mnt/global/buff/arbos/workspace/swe/validator
source /mnt/global/buff/arbos/workspace/swe/.venv/bin/activate

exec python3 king.py
