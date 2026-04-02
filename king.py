"""King-of-the-hill mechanism for subnet 66 validation."""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from chain import MinerCommitment, get_all_miner_commitments, set_weights_to_king
from evaluator import run_matchup, MatchupResult
from config import ValidatorConfig

logger = logging.getLogger(__name__)

STATE_FILE = Path("/mnt/global/buff/arbos/workspace/swe/validator/king_state.json")


@dataclass
class KingState:
    """Persistent state for the king-of-the-hill mechanism."""
    king_hotkey: Optional[str] = None
    king_uid: Optional[int] = None
    king_repo: Optional[str] = None
    king_commit: Optional[str] = None
    king_avg_score: float = 0.0  # avg similarity to cursor

    # Track tested agents so we never re-test
    tested_hotkeys: set = field(default_factory=set)

    # Queue of pending commitments (hotkey -> commitment)
    last_processed_block: int = 0

    def save(self):
        data = {
            "king_hotkey": self.king_hotkey,
            "king_uid": self.king_uid,
            "king_repo": self.king_repo,
            "king_commit": self.king_commit,
            "king_avg_score": self.king_avg_score,
            "tested_hotkeys": list(self.tested_hotkeys),
            "last_processed_block": self.last_processed_block,
        }
        STATE_FILE.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved king state: king={self.king_repo}@{self.king_commit or 'none'}")

    @classmethod
    def load(cls) -> "KingState":
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            state = cls(
                king_hotkey=data.get("king_hotkey"),
                king_uid=data.get("king_uid"),
                king_repo=data.get("king_repo"),
                king_commit=data.get("king_commit"),
                king_avg_score=data.get("king_avg_score", 0.0),
                tested_hotkeys=set(data.get("tested_hotkeys", [])),
                last_processed_block=data.get("last_processed_block", 0),
            )
            return state
        return cls()


def build_challenge_queue(state: KingState) -> list[MinerCommitment]:
    """Build queue of untested miners from chain commitments."""
    commitments = get_all_miner_commitments()

    # Filter out already-tested hotkeys and the current king
    queue = []
    for c in commitments:
        if c.hotkey in state.tested_hotkeys:
            continue
        if c.hotkey == state.king_hotkey:
            continue
        queue.append(c)

    logger.info(f"Challenge queue: {len(queue)} untested agents")
    return queue


async def run_challenge(
    contender: MinerCommitment,
    state: KingState,
    config: ValidatorConfig,
) -> bool:
    """Run a single challenge. Returns True if contender becomes new king."""
    contender_agent = f"{contender.repo}@{contender.commit_sha}"

    # If no king yet, the contender just needs to solve tasks successfully
    if state.king_repo is None:
        logger.info(f"No king yet. Testing {contender_agent} as first king candidate...")
        # Run against cursor only
        result = await run_matchup(
            contender_agent=contender_agent,
            king_agent="cursor",  # king is cursor by default
            config=config,
        )

        # Any agent that can produce solutions becomes king
        if result.contender_avg > 0:
            state.king_hotkey = contender.hotkey
            state.king_uid = contender.uid
            state.king_repo = contender.repo
            state.king_commit = contender.commit_sha
            state.king_avg_score = result.contender_avg
            logger.info(f"NEW KING: {contender_agent} with score {result.contender_avg:.4f}")
            return True
        else:
            logger.info(f"Candidate {contender_agent} failed to produce valid solutions")
            return False

    # Head-to-head: contender vs king
    king_agent = f"{state.king_repo}@{state.king_commit}"
    logger.info(f"CHALLENGE: {contender_agent} vs KING {king_agent}")

    result = await run_matchup(
        contender_agent=contender_agent,
        king_agent=king_agent,
        config=config,
    )

    improvement = result.contender_avg - result.king_avg
    logger.info(
        f"Result: contender={result.contender_avg:.4f} king={result.king_avg:.4f} "
        f"delta={improvement:+.4f} (need +{config.epsilon:.4f})"
    )

    if improvement > config.epsilon:
        # Contender wins!
        state.king_hotkey = contender.hotkey
        state.king_uid = contender.uid
        state.king_repo = contender.repo
        state.king_commit = contender.commit_sha
        state.king_avg_score = result.contender_avg
        logger.info(f"DETHRONED! New king: {contender_agent}")
        return True
    else:
        logger.info(f"King holds. Discarding {contender_agent}")
        return False


def discord_notify(message: str):
    """Send a notification to Discord (fire-and-forget)."""
    try:
        import subprocess
        script = Path(__file__).parent / "send_discord.py"
        subprocess.Popen(
            ["python3", str(script), message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning(f"Discord notify failed: {e}")


async def validation_loop(config: ValidatorConfig):
    """Main validation loop: process challenge queue, set weights."""
    import bittensor as bt

    wallet = bt.Wallet(name=config.wallet_name, hotkey=config.hotkey_name)
    state = KingState.load()

    logger.info(f"Starting validation loop. Current king: {state.king_repo or 'none'}")
    discord_notify(
        f"**SN66 Validator started**\n"
        f"Current king: {state.king_repo or 'none'}\n"
        f"Tested agents: {len(state.tested_hotkeys)}"
    )

    while True:
        try:
            # Build queue of untested agents
            queue = build_challenge_queue(state)

            if not queue:
                logger.info("No new agents to test. Sleeping for 1 tempo (360 blocks ~ 72 min)...")
                # Set weights if we have a king
                if state.king_uid is not None:
                    set_weights_to_king(config.netuid, state.king_uid, wallet)
                await asyncio.sleep(360 * 12)  # 360 blocks * 12s/block
                continue

            # Process one agent at a time
            contender = queue[0]
            logger.info(f"Next challenger: UID {contender.uid} - {contender.repo}@{contender.commit_sha[:8]}")
            discord_notify(
                f"**SN66 Challenge starting**\n"
                f"Contender: UID {contender.uid} `{contender.repo}@{contender.commit_sha[:8]}`\n"
                f"vs King: {state.king_repo or 'none'}"
            )

            won = await run_challenge(contender, state, config)

            # Mark as tested (win or lose, never test again)
            state.tested_hotkeys.add(contender.hotkey)
            state.save()

            if won:
                discord_notify(
                    f"**SN66 New King!**\n"
                    f"`{state.king_repo}@{state.king_commit[:8] if state.king_commit else '?'}`\n"
                    f"Score: {state.king_avg_score:.2%} similarity to Cursor\n"
                    f"UID: {state.king_uid}"
                )
            else:
                discord_notify(
                    f"**SN66 King defended**\n"
                    f"Contender `{contender.repo}@{contender.commit_sha[:8]}` failed to dethrone.\n"
                    f"King: {state.king_repo or 'cursor (default)'}"
                )

            # Set weights after each challenge
            if state.king_uid is not None:
                set_weights_to_king(config.netuid, state.king_uid, wallet)

        except Exception as e:
            logger.error(f"Error in validation loop: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait 1 min on error


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("/mnt/global/buff/arbos/workspace/swe/validator/validator.log"),
        ],
    )
    config = ValidatorConfig()
    asyncio.run(validation_loop(config))


if __name__ == "__main__":
    main()
