#!/usr/bin/env python3
"""Discord bot for subnet 66 status updates.

Sends periodic updates to the Bittensor subnet 66 channel about:
- Current king and their performance
- New challengers and matchup results
- How to mine on the subnet
"""
import discord
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sn66-bot")

TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
BITTENSOR_GUILD_ID = 799672011265015819
SUBNET_66_CHANNEL_ID = 1486739181093785600

KING_STATE_FILE = Path("/mnt/global/buff/arbos/workspace/swe/validator/king_state.json")
VALIDATOR_REPO = "https://github.com/unarbos/sn66-validator"
TAU_REPO = "https://github.com/unarbos/tau"


def load_king_state():
    if KING_STATE_FILE.exists():
        return json.loads(KING_STATE_FILE.read_text())
    return None


class SubnetBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)
        self.target_channel = None

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.target_channel = self.get_channel(SUBNET_66_CHANNEL_ID)
        if self.target_channel:
            log.info(f"Found subnet 66 channel: #{self.target_channel.name}")
        else:
            log.error(f"Could not find channel {SUBNET_66_CHANNEL_ID}")

    async def send_update(self, message: str):
        if self.target_channel:
            try:
                await self.target_channel.send(message)
                log.info(f"Sent message to #{self.target_channel.name}")
            except Exception as e:
                log.error(f"Failed to send message: {e}")
        else:
            log.warning("No target channel set")

    async def send_welcome_message(self):
        """Send initial welcome/info message about subnet 66."""
        msg = """**Subnet 66 - AlphaCore Validator Online**

Welcome to subnet 66! This subnet distills Cursor agent behavior by comparing miner-submitted agents against Cursor on real coding tasks.

**How it works:**
1. Miners register keys and commit their agent repo+commit to the chain
2. The validator generates coding tasks using `tau generate`
3. Both Cursor and the challenger agent solve each task
4. Patches are compared for line-level similarity
5. The best agent becomes **King** and gets 100% of subnet weight

**How to mine:**
- Fork and improve the coding agent at {tau_repo}
- Register a hotkey on subnet 66 (burn cost: ~0.0005 TAO)
- Commit your repo and commit hash to the chain: `owner/repo@commit_sha`

**King-of-the-Hill rules:**
- Contenders must beat the current king by >1% average patch similarity to Cursor
- One shot per hotkey - if you lose, you need a new commit
- Max 3 new agents tested per epoch (360 blocks)

**Links:**
- Validator code: {validator_repo}
- Tau framework: {tau_repo}
""".format(validator_repo=VALIDATOR_REPO, tau_repo=TAU_REPO)
        await self.send_update(msg)

    async def send_status_update(self):
        """Send current king status."""
        state = load_king_state()
        if state and state.get("king_repo"):
            msg = f"""**Subnet 66 Status Update** ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})

**Current King:** `{state['king_repo']}@{state.get('king_commit', 'unknown')[:8]}`
**King Score:** {state.get('king_avg_score', 0):.2%} similarity to Cursor
**King UID:** {state.get('king_uid', 'unknown')}
**Tested agents:** {len(state.get('tested_hotkeys', []))}
"""
        else:
            msg = f"""**Subnet 66 Status Update** ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})

No king crowned yet. The throne is open for the first miner to submit a working agent!
Register and commit your agent to become the first king.
"""
        await self.send_update(msg)


async def main():
    if not TOKEN:
        log.error("DISCORD_BOT_TOKEN not set")
        sys.exit(1)

    bot = SubnetBot()

    # If --discover flag, just log channels and exit
    if "--discover" in sys.argv:
        @bot.event
        async def on_ready():
            log.info(f"Logged in as {bot.user}")
            for guild in bot.guilds:
                log.info(f"\nGuild: {guild.name} (ID: {guild.id})")
                for ch in guild.text_channels:
                    log.info(f"  #{ch.name} (ID: {ch.id})")
            await bot.close()
        await bot.start(TOKEN)
        return

    # If --welcome flag, send welcome and exit
    if "--welcome" in sys.argv:
        async with bot:
            @bot.event
            async def on_ready():
                await bot.send_welcome_message()
                await asyncio.sleep(2)
                await bot.close()
            await bot.start(TOKEN)
        return

    # If --status flag, send status and exit
    if "--status" in sys.argv:
        async with bot:
            @bot.event
            async def on_ready():
                await bot.send_status_update()
                await asyncio.sleep(2)
                await bot.close()
            await bot.start(TOKEN)
        return

    # Default: run as persistent bot
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
