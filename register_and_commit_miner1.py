"""Register miner1 on subnet 66 and commit agent to chain."""
import sys
import time

import bittensor as bt

NETUID = 66
WALLET_NAME = "miner_test"
HOTKEY_NAME = "miner1"
AGENT_COMMITMENT = "unarbos/tau@b071460"

sub = bt.Subtensor()
wallet = bt.Wallet(name=WALLET_NAME, hotkey=HOTKEY_NAME)

print(f"Hotkey: {wallet.hotkey.ss58_address}", flush=True)

# Phase 1: Register
block = sub.block
interval = 360
next_interval = ((block // interval) + 1) * interval
print(f"Current block: {block}, next interval: {next_interval}, wait: {next_interval - block} blocks", flush=True)

while True:
    block = sub.block
    remaining = next_interval - block
    if remaining <= 1:
        print(f"Block {block} — attempting registration!", flush=True)
        result = sub.burned_register(wallet=wallet, netuid=NETUID)
        if result.success:
            print("REGISTRATION SUCCESSFUL!", flush=True)
            break
        print(f"Failed: {result.message}", flush=True)
        # Try a few more times with delays
        success = False
        for attempt in range(5):
            time.sleep(15)
            block = sub.block
            print(f"Retry {attempt+1} at block {block}...", flush=True)
            result = sub.burned_register(wallet=wallet, netuid=NETUID)
            if result.success:
                print("REGISTRATION SUCCESSFUL!", flush=True)
                success = True
                break
            print(f"Failed: {result.message}", flush=True)
        if success:
            break
        # Move to next interval
        next_interval += interval
        print(f"Moving to next interval: {next_interval}", flush=True)
    else:
        sleep_time = min(max(remaining * 12 - 20, 5), 120)
        print(f"Block {block}, {remaining} blocks remaining, sleeping {sleep_time}s", flush=True)
        time.sleep(sleep_time)

# Phase 2: Commit agent to chain
print(f"\nCommitting agent: {AGENT_COMMITMENT}", flush=True)
time.sleep(12)  # Wait for 1 block after registration
result = sub.set_commitment(wallet=wallet, netuid=NETUID, data=AGENT_COMMITMENT)
print(f"Commitment result: {result}", flush=True)

# Verify
time.sleep(12)
comms = sub.get_all_commitments(NETUID)
our_commitment = comms.get(wallet.hotkey.ss58_address)
print(f"Verified commitment: {our_commitment}", flush=True)

# Get UID
uid = sub.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, NETUID)
print(f"Assigned UID: {uid}", flush=True)
print("DONE!", flush=True)
