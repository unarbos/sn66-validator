#!/usr/bin/env python3
"""Simple one-shot Discord message sender for subnet 66 channel using REST API."""
import json
import os
import sys
import urllib.request
import urllib.error

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
# Channels the bot can write to:
# - owners: 1194085035389747280  (subnet owner channel)
# - general: 799672011814862902  (main general)
# - unclaimed-66: 1486739181093785600  (subnet 66 - needs 'verified' role)
OWNERS_CHANNEL_ID = "1194085035389747280"
SUBNET_66_CHANNEL_ID = "1486739181093785600"
DEFAULT_CHANNEL_ID = OWNERS_CHANNEL_ID
API_BASE = "https://discord.com/api/v10"


def send_message(channel_id: str = DEFAULT_CHANNEL_ID, message: str = "") -> bool:
    url = f"{API_BASE}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (https://github.com/unarbos/sn66-validator, 1.0)",
    }

    # Split long messages
    chunks = [message[i:i+2000] for i in range(0, len(message), 2000)] if len(message) > 2000 else [message]

    for chunk in chunks:
        data = json.dumps({"content": chunk}).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status in (200, 201):
                    print(f"Message sent (status {resp.status})")
                else:
                    print(f"Unexpected status: {resp.status}")
                    return False
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"HTTP {e.code}: {body}")
            return False

    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python send_discord.py 'message'")
        print("  or pipe: echo 'msg' | python send_discord.py -")
        sys.exit(1)

    if sys.argv[1] == "-":
        msg = sys.stdin.read().strip()
    else:
        msg = " ".join(sys.argv[1:])

    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN not set")
        sys.exit(1)

    channel = DEFAULT_CHANNEL_ID
    if "--channel" in sys.argv:
        idx = sys.argv.index("--channel")
        channel = sys.argv[idx + 1]
        sys.argv.pop(idx)
        sys.argv.pop(idx)

    success = send_message(channel, msg)
    sys.exit(0 if success else 1)
