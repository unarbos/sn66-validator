"""Validator configuration for subnet 66."""

from dataclasses import dataclass, field
from pathlib import Path
import os


@dataclass
class ValidatorConfig:
    # Bittensor
    netuid: int = 66
    wallet_name: str = "sn66"
    hotkey_name: str = "sn66_hk"
    network: str = "finney"

    # King-of-the-hill
    epsilon: float = 0.01  # 1% improvement needed to dethrone king
    samples_per_challenge: int = 10  # concurrent task samples per matchup
    max_new_agents_per_tempo: int = 3  # max agents queued per 360 blocks

    # Tau pipeline
    tau_dir: Path = field(default_factory=lambda: Path("/mnt/global/buff/arbos/workspace/swe/tau"))
    workspace_dir: Path = field(default_factory=lambda: Path("/mnt/global/buff/arbos/workspace/swe/workspace"))
    venv_activate: str = "/mnt/global/buff/arbos/workspace/swe/.venv/bin/activate"

    # Agent timeout
    agent_timeout: int = 300  # 5 minutes per solve

    # Environment
    openrouter_key: str = field(default_factory=lambda: os.environ.get("OPENROUTER_KEY", ""))
    cursor_api_key: str = field(default_factory=lambda: os.environ.get("CURSOR_API_KEY", ""))

    # Concurrency limits
    max_concurrent_solves: int = 3  # limit parallel solves to avoid overloading
