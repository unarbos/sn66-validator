"""Chain interaction: read commitments, set weights, manage keys."""

import bittensor as bt
import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Commitment format: "owner/repo@commit_sha"
# e.g. "unarbos/my-agent@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
COMMITMENT_RE = re.compile(r'^([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@([0-9a-f]{7,40})$')


@dataclass
class MinerCommitment:
    hotkey: str
    uid: int
    repo: str  # "owner/repo"
    commit_sha: str
    raw: str


def parse_commitment(raw: str) -> tuple[str, str] | None:
    """Parse 'owner/repo@sha' format. Returns (repo, sha) or None."""
    m = COMMITMENT_RE.match(raw.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def get_all_miner_commitments(netuid: int = 66) -> list[MinerCommitment]:
    """Fetch all commitments from chain for a subnet."""
    sub = bt.Subtensor()
    meta = sub.metagraph(netuid=netuid)

    all_commits = sub.get_all_commitments(netuid=netuid)
    results = []

    # Build hotkey -> uid map
    hotkey_to_uid = {}
    for uid in range(meta.n):
        hotkey_to_uid[meta.hotkeys[uid]] = uid

    for hotkey, raw_data in all_commits.items():
        parsed = parse_commitment(raw_data)
        if parsed is None:
            logger.warning(f"Skipping invalid commitment from {hotkey[:16]}...: {raw_data!r}")
            continue
        repo, sha = parsed
        uid = hotkey_to_uid.get(hotkey, -1)
        results.append(MinerCommitment(
            hotkey=hotkey,
            uid=uid,
            repo=repo,
            commit_sha=sha,
            raw=raw_data,
        ))

    logger.info(f"Found {len(results)} valid commitments on subnet {netuid}")
    return results


def set_weights_to_king(netuid: int, king_uid: int, wallet: bt.Wallet) -> bool:
    """Set 100% weight to the king UID."""
    sub = bt.Subtensor()
    try:
        result = sub.set_weights(
            wallet=wallet,
            netuid=netuid,
            uids=[king_uid],
            weights=[1.0],
            wait_for_inclusion=True,
            wait_for_finalization=True,
        )
        logger.info(f"Set weights: 100% to UID {king_uid}, result={result}")
        return bool(result)
    except Exception as e:
        logger.error(f"Failed to set weights: {e}")
        return False


def commit_agent(wallet: bt.Wallet, netuid: int, repo: str, commit_sha: str) -> bool:
    """Commit an agent repo+sha to the chain as a miner."""
    data = f"{repo}@{commit_sha}"
    if len(data.encode()) > 128:
        logger.error(f"Commitment too long ({len(data.encode())} bytes): {data}")
        return False

    sub = bt.Subtensor()
    try:
        response = sub.set_commitment(
            wallet=wallet,
            netuid=netuid,
            data=data,
        )
        logger.info(f"Committed '{data}' to subnet {netuid}: {response}")
        return True
    except Exception as e:
        logger.error(f"Failed to commit: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    commitments = get_all_miner_commitments(66)
    for c in commitments:
        print(f"  UID {c.uid}: {c.repo}@{c.commit_sha[:8]} (hotkey={c.hotkey[:16]}...)")
    if not commitments:
        print("  No valid commitments found on subnet 66")
