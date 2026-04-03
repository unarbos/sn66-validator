module.exports = {
  apps: [{
    name: "sn66-validator",
    script: "run_validator.py",
    interpreter: "/mnt/global/buff/arbos/workspace/swe/.venv/bin/python",
    interpreter_args: "-u",
    cwd: __dirname,
    max_restarts: 50,
    restart_delay: 30000,  // 30s between restarts
    autorestart: true,
    log_date_format: "YYYY-MM-DD HH:mm:ss.SSS",
    error_file: "logs/validator-error.log",
    out_file: "logs/validator-out.log",
    merge_logs: true,
    max_memory_restart: "4G",
    env: {
      OPENROUTER_KEY: process.env.OPENROUTER_KEY,
      CURSOR_API_KEY: process.env.CURSOR_API_KEY,
      DISCORD_BOT_TOKEN: process.env.DISCORD_BOT_TOKEN,
      ARBOS_GITHUH_TOKEN: process.env.ARBOS_GITHUH_TOKEN,
    },
  }]
};
