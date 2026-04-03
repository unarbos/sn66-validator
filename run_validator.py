#!/usr/bin/env python3
"""Validator runner for pm2 — invokes tau validate directly."""
import os
import sys

# Force unbuffered output
os.environ["PYTHONUNBUFFERED"] = "1"
os.environ.setdefault("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_KEY", ""))
os.environ.setdefault("GITHUB_TOKEN", os.environ.get("ARBOS_GITHUH_TOKEN", ""))

# Add tau src to path
sys.path.insert(0, "/mnt/global/buff/arbos/workspace/swe/tau/src")
os.chdir("/mnt/global/buff/arbos/workspace/swe/tau")

print("validator starting", flush=True)

from validate import validate_loop_run  # noqa: E402
from config import RunConfig  # noqa: E402
from pathlib import Path  # noqa: E402
from pipeline import _setup_logging  # noqa: E402

_setup_logging(debug=False)

import logging
log = logging.getLogger("swe-eval.validate")
log.info("Starting validate loop")
print("setup complete, entering loop", flush=True)

config = RunConfig(
    workspace_root=Path("/mnt/global/buff/arbos/workspace/swe/workspace").resolve(),
    validate_wallet_name="sn66",
    validate_wallet_hotkey="sn66_hk",
    validate_netuid=66,
    validate_rounds=3,
    validate_concurrency=2,
    agent_timeout=300,
    validate_weight_interval_blocks=360,
    validate_poll_interval_seconds=60,
)

validate_loop_run(config=config)
