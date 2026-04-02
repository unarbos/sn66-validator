"""Evaluator: runs tau generate/solve/compare pipeline for agent matchups."""

import subprocess
import json
import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from config import ValidatorConfig

logger = logging.getLogger(__name__)


@dataclass
class SolveResult:
    agent_name: str
    task_name: str
    solution_name: str
    success: bool
    diff_path: Optional[Path] = None
    error: Optional[str] = None


@dataclass
class MatchupResult:
    """Result of comparing two agents across multiple tasks."""
    contender_repo: str
    king_repo: str
    cursor_repo: str  # always "cursor"
    tasks: list[str]
    # Similarity scores: contender vs cursor, king vs cursor
    contender_scores: list[float]  # per-task similarity to cursor
    king_scores: list[float]  # per-task similarity to cursor
    contender_avg: float
    king_avg: float


def _run_tau(args: list[str], config: ValidatorConfig, timeout: int = 600, use_docker_group: bool = False) -> subprocess.CompletedProcess:
    """Run a tau CLI command."""
    tau_cmd = f"python -m src.cli {' '.join(args)}"
    if use_docker_group:
        tau_cmd = f"sg docker \"{tau_cmd}\""
    cmd = [
        "bash", "-c",
        f"source {config.venv_activate} && cd {config.tau_dir} && "
        f"OPENROUTER_API_KEY={config.openrouter_key} "
        f"CURSOR_API_KEY={config.cursor_api_key} "
        f"{tau_cmd}"
    ]
    logger.info(f"Running tau: {' '.join(args)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(config.tau_dir))
    if result.returncode != 0:
        logger.error(f"tau failed: {result.stderr[:500]}")
    return result


def generate_task(task_name: str, config: ValidatorConfig) -> bool:
    """Generate a task using tau generate."""
    result = _run_tau([
        "generate", "--task", task_name,
        "--workspace-root", str(config.workspace_dir),
    ], config, timeout=300)
    return result.returncode == 0


def solve_task(task_name: str, solution_name: str, agent: str, config: ValidatorConfig) -> SolveResult:
    """Solve a task with a specific agent using tau solve."""
    args = [
        "solve",
        "--task", task_name,
        "--solution", solution_name,
        "--agent", agent,
        "--agent-timeout", str(config.agent_timeout),
        "--workspace-root", str(config.workspace_dir),
    ]
    # Solving requires Docker
    result = _run_tau(args, config, timeout=config.agent_timeout + 120, use_docker_group=True)

    # tau nests workspace under {workspace_root}/workspace/tasks/
    solution_dir = config.workspace_dir / "workspace" / "tasks" / task_name / "solutions" / solution_name
    diff_path = solution_dir / "solution.diff"
    solve_json = solution_dir / "solve.json"

    success = False
    if solve_json.exists():
        try:
            data = json.loads(solve_json.read_text())
            success = data.get("success", False)
        except (json.JSONDecodeError, ValueError):
            pass

    if success and diff_path.exists() and diff_path.stat().st_size > 0:
        return SolveResult(
            agent_name=agent,
            task_name=task_name,
            solution_name=solution_name,
            success=True,
            diff_path=diff_path,
        )
    else:
        return SolveResult(
            agent_name=agent,
            task_name=task_name,
            solution_name=solution_name,
            success=False,
            error=result.stderr[:500] if result.stderr else "No diff produced",
        )


def compare_solutions(task_name: str, solution_a: str, solution_b: str, config: ValidatorConfig) -> float:
    """Compare two solutions using tau compare. Returns similarity ratio."""
    args = [
        "compare",
        "--task", task_name,
        "--solutions", solution_a, solution_b,
        "--workspace-root", str(config.workspace_dir),
    ]
    result = _run_tau(args, config, timeout=120)

    if result.returncode != 0:
        logger.error(f"Compare failed for {task_name}: {result.stderr[:200]}")
        return 0.0

    # Read compare.json from the comparison output directory
    comparison_name = f"{solution_a}--vs--{solution_b}"
    compare_json = (
        config.workspace_dir / "workspace" / "tasks" / task_name
        / "comparisons" / comparison_name / "compare.json"
    )
    try:
        data = json.loads(compare_json.read_text())
        ratio = float(data.get("result", {}).get("similarity_ratio", 0.0))
        logger.info(f"Compare {comparison_name}: similarity_ratio={ratio:.4f}")
        return ratio
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to read compare.json: {e}")
        # Fallback: parse stdout for percentage
        import re
        m = re.search(r'(\d+\.\d+)%', result.stdout)
        if m:
            return float(m.group(1)) / 100.0
        return 0.0


async def run_matchup(
    contender_agent: str,
    king_agent: str,
    config: ValidatorConfig,
) -> MatchupResult:
    """Run a head-to-head matchup between contender and king.

    For each sample:
    1. Generate a task
    2. Solve with cursor, contender, and king (concurrently)
    3. Compare contender vs cursor and king vs cursor
    """
    contender_scores = []
    king_scores = []
    tasks = []

    for i in range(config.samples_per_challenge):
        task_name = f"matchup-{i}-{hash(contender_agent) % 10000:04d}"
        tasks.append(task_name)

        # Generate task
        logger.info(f"Sample {i+1}/{config.samples_per_challenge}: generating task {task_name}")
        if not generate_task(task_name, config):
            logger.error(f"Failed to generate task {task_name}, skipping")
            continue

        # Solve with all three agents concurrently
        loop = asyncio.get_event_loop()
        cursor_future = loop.run_in_executor(
            None, solve_task, task_name, f"cursor-{i}", "cursor", config
        )
        contender_future = loop.run_in_executor(
            None, solve_task, task_name, f"contender-{i}", contender_agent, config
        )
        king_future = loop.run_in_executor(
            None, solve_task, task_name, f"king-{i}", king_agent, config
        )

        cursor_result, contender_result, king_result = await asyncio.gather(
            cursor_future, contender_future, king_future
        )

        # Compare against cursor
        if contender_result.success and cursor_result.success:
            score = compare_solutions(task_name, f"contender-{i}", f"cursor-{i}", config)
            contender_scores.append(score)
            logger.info(f"  Contender similarity to cursor: {score:.4f}")
        else:
            contender_scores.append(0.0)
            logger.warning(f"  Contender or cursor failed on {task_name}")

        if king_result.success and cursor_result.success:
            score = compare_solutions(task_name, f"king-{i}", f"cursor-{i}", config)
            king_scores.append(score)
            logger.info(f"  King similarity to cursor: {score:.4f}")
        else:
            king_scores.append(0.0)
            logger.warning(f"  King or cursor failed on {task_name}")

    contender_avg = sum(contender_scores) / len(contender_scores) if contender_scores else 0.0
    king_avg = sum(king_scores) / len(king_scores) if king_scores else 0.0

    return MatchupResult(
        contender_repo=contender_agent,
        king_repo=king_agent,
        cursor_repo="cursor",
        tasks=tasks,
        contender_scores=contender_scores,
        king_scores=king_scores,
        contender_avg=contender_avg,
        king_avg=king_avg,
    )
