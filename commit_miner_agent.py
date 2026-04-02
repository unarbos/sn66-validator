#!/usr/bin/env python3
"""Commit a test miner agent to the chain after registration."""
import bittensor as bt
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()

NETUID = 66
WALLET_NAME = "miner_test"
HOTKEY_NAME = "miner0"
AGENT_REPO = "unarbos/tau"
AGENT_COMMIT = "a37c229"

wallet = bt.Wallet(name=WALLET_NAME, hotkey=HOTKEY_NAME)
hk = wallet.hotkey.ss58_address
log.info(f"Miner hotkey: {hk}")

# Check registration
sub = bt.Subtensor()
meta = sub.metagraph(NETUID)
if hk not in meta.hotkeys:
    log.error("Miner not registered yet. Run smart_register.py first.")
    sys.exit(1)

uid = meta.hotkeys.index(hk)
log.info(f"Miner registered at UID {uid}")

# Commit agent
data = f"{AGENT_REPO}@{AGENT_COMMIT}"
log.info(f"Committing: {data}")

try:
    result = sub.set_commitment(
        wallet=wallet,
        netuid=NETUID,
        data=data,
    )
    log.info(f"Commitment result: {result}")
except Exception as e:
    log.error(f"Failed to commit: {e}")
    sys.exit(1)

# Verify
try:
    commitments = sub.get_all_commitments(netuid=NETUID)
    if hk in commitments:
        log.info(f"Verified commitment on chain: {commitments[hk]}")
    else:
        log.warning("Commitment not found in chain data yet (may need a block)")
except Exception as e:
    log.warning(f"Could not verify: {e}")
