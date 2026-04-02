"""Register miner1 hotkey on subnet 66, waiting for next interval."""
import sys
import time

import bittensor as bt

NETUID = 66
TARGET_BLOCK = 7883280
WALLET_NAME = "miner_test"
HOTKEY_NAME = "miner1"

sub = bt.Subtensor()
wallet = bt.Wallet(name=WALLET_NAME, hotkey=HOTKEY_NAME)

print(f"Hotkey: {wallet.hotkey.ss58_address}", flush=True)
print(f"Waiting for block >= {TARGET_BLOCK} to register...", flush=True)

while True:
    block = sub.block
    remaining = TARGET_BLOCK - block
    if remaining <= 1:
        print(f"Block {block} — attempting registration!", flush=True)
        result = sub.burned_register(wallet=wallet, netuid=NETUID)
        print(f"Result: success={result.success}", flush=True)
        if result.success:
            print("REGISTRATION SUCCESSFUL!", flush=True)
            sys.exit(0)
        else:
            print(f"Failed: {result.message}", flush=True)
            # Try a few more times
            for attempt in range(3):
                time.sleep(12)
                block = sub.block
                print(f"Retry {attempt+1} at block {block}...", flush=True)
                result = sub.burned_register(wallet=wallet, netuid=NETUID)
                if result.success:
                    print("REGISTRATION SUCCESSFUL!", flush=True)
                    sys.exit(0)
                print(f"Failed: {result.message}", flush=True)
            print("All retries failed", flush=True)
            sys.exit(1)
    else:
        sleep_time = min(max(remaining * 12 - 20, 5), 60)
        print(f"Block {block}, {remaining} blocks remaining, sleeping {sleep_time}s", flush=True)
        time.sleep(sleep_time)
