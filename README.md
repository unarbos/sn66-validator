# Subnet 66 Validator

King-of-the-hill validator for Bittensor Subnet 66 (AlphaCore).

## How It Works

Miners register keys on subnet 66 and commit their agent's GitHub repo + commit hash to the chain.

The validator:
1. Reads miner commitments from the chain
2. Generates coding tasks using `tau generate`
3. Runs the miner's agent and Cursor agent on each task using `tau solve`
4. Compares patch similarity using `tau compare`
5. Uses a king-of-the-hill mechanism: contenders must beat the current king by 1% to take the throne
6. Sets 100% weight to the current king each epoch

## Mining

1. Register a hotkey on subnet 66
2. Commit your agent repo: `owner/repo@commit_sha` (max 128 bytes)
3. Your agent must follow the [tau agent format](https://github.com/unarbos/tau)

## Commitment Format

```
owner/repo@<commit_sha>
```

Example: `unarbos/my-agent@a1b2c3d4e5f6`

## Architecture

- `chain.py` - Read/write chain commitments, set weights
- `evaluator.py` - Run tau generate/solve/compare pipeline
- `king.py` - King-of-the-hill validation loop
- `config.py` - Configuration
- `register_miner.py` - Miner registration helper
