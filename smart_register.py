#!/usr/bin/env python3
"""Smart miner registration: waits for interval boundary then registers immediately."""
import bittensor as bt
import time
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/miner_registration.log', mode='w')
    ]
)
log = logging.getLogger()

NETUID = 66
TEMPO = 360

wallet = bt.Wallet(name='miner_test', hotkey='miner0')
hk = wallet.hotkey.ss58_address
log.info(f"Hotkey: {hk}")

for attempt in range(30):
    sub = bt.Subtensor()
    metagraph = sub.metagraph(NETUID)

    if hk in metagraph.hotkeys:
        uid = metagraph.hotkeys.index(hk)
        log.info(f"SUCCESS: Already registered at UID {uid}")
        sys.exit(0)

    block = sub.block
    interval_pos = block % TEMPO
    blocks_left = TEMPO - interval_pos

    log.info(f"Attempt {attempt+1}: block={block}, interval_pos={interval_pos}/{TEMPO}, blocks_left={blocks_left}")

    # If we're near the start of an interval (first 10 blocks), try now
    if interval_pos < 10:
        log.info(f"Near interval start, attempting burn registration...")
        try:
            result = sub.burned_register(
                wallet=wallet,
                netuid=NETUID,
                wait_for_inclusion=True,
                wait_for_finalization=True
            )
            if result is True or (hasattr(result, 'success') and result.success):
                metagraph = sub.metagraph(NETUID)
                if hk in metagraph.hotkeys:
                    uid = metagraph.hotkeys.index(hk)
                    log.info(f"SUCCESS: Registered at UID {uid}")
                    sys.exit(0)
                else:
                    log.info("Registration returned success but hotkey not found in metagraph yet")
            else:
                error = getattr(result, 'error', result)
                log.info(f"Registration failed: {str(error)[:200]}")
        except Exception as e:
            log.info(f"Registration exception: {str(e)[:200]}")

        # Wait a bit before retrying
        time.sleep(24)  # 2 blocks
    else:
        # Wait until near the next interval boundary
        wait_blocks = max(blocks_left - 5, 1)  # arrive 5 blocks early
        wait_seconds = wait_blocks * 12
        log.info(f"Waiting {wait_blocks} blocks (~{wait_seconds}s) until next interval boundary...")
        time.sleep(wait_seconds)

log.info("Exhausted all attempts. Registration not completed.")
sys.exit(1)
