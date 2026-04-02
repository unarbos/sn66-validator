"""Register a miner on subnet 66 and commit an agent repo."""

import bittensor as bt
import time
import logging
import sys
import os

from chain import commit_agent

logger = logging.getLogger(__name__)

NETUID = 66


def register_miner(wallet_name: str, hotkey_name: str, max_retries: int = 10) -> int:
    """Register a miner on subnet 66. Returns UID or -1 on failure."""
    wallet = bt.Wallet(name=wallet_name, hotkey=hotkey_name)
    sub = bt.Subtensor()
    hk = wallet.hotkey.ss58_address

    # Check if already registered
    meta = sub.metagraph(netuid=NETUID)
    if hk in meta.hotkeys:
        uid = meta.hotkeys.index(hk)
        logger.info(f"Already registered at UID {uid}")
        return uid

    for attempt in range(max_retries):
        logger.info(f"Registration attempt {attempt + 1}/{max_retries}...")
        result = sub.burned_register(
            wallet=wallet,
            netuid=NETUID,
            wait_for_inclusion=True,
            wait_for_finalization=True,
        )

        if result.success:
            meta = sub.metagraph(netuid=NETUID)
            if hk in meta.hotkeys:
                uid = meta.hotkeys.index(hk)
                logger.info(f"Registered at UID {uid}!")
                return uid

        error_str = str(result.error) if result.error else ""
        if "Custom error: 6" in error_str:
            # Rate limit / registration interval full
            logger.info("Registration interval full. Waiting for next interval (~6 min)...")
            time.sleep(360 * 12 // 6)  # Wait ~1/6 of a tempo
        else:
            logger.error(f"Registration failed: {result.message}")
            time.sleep(30)

    return -1


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    wallet_name = sys.argv[1] if len(sys.argv) > 1 else "miner_test"
    hotkey_name = sys.argv[2] if len(sys.argv) > 2 else "miner0"
    repo = sys.argv[3] if len(sys.argv) > 3 else None
    commit_sha = sys.argv[4] if len(sys.argv) > 4 else None

    uid = register_miner(wallet_name, hotkey_name)
    if uid < 0:
        logger.error("Failed to register after retries")
        sys.exit(1)

    if repo and commit_sha:
        wallet = bt.Wallet(name=wallet_name, hotkey=hotkey_name)
        success = commit_agent(wallet, NETUID, repo, commit_sha)
        if success:
            logger.info(f"Committed {repo}@{commit_sha} for UID {uid}")
        else:
            logger.error("Failed to commit agent")
            sys.exit(1)


if __name__ == "__main__":
    main()
