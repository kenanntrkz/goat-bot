"""Base agent class for goat agents."""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"


class BaseAgent:
    """Base class for all goat agents."""

    agent_id: str = ""
    name: str = ""
    role: str = ""
    category: str = ""

    def __init__(self):
        self.run_log = []

    def log(self, message: str):
        entry = {"time": datetime.now().isoformat(), "message": message}
        self.run_log.append(entry)

    def load_data(self, path: str):
        full_path = DATA_DIR / path
        if full_path.exists():
            with open(full_path) as f:
                return json.load(f)
        return {}

    def save_output(self, filename: str, data):
        out_dir = OUTPUT_DIR / "reports"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        self.log(f"Saved output to {path}")

    def save_data(self, path: str, data):
        """Save data to the data directory."""
        full_path = DATA_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def load_config(self) -> dict:
        """Load the user's agency profile."""
        config_path = DATA_DIR / "config" / "user_profile.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}

    def call_claude(self, prompt: str, timeout: int = 120):
        """Call Claude via Anthropic SDK (preferred) or CLI. Returns text or None."""
        # 1. Try Anthropic SDK (no CLI needed)
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                msg = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                return msg.content[0].text
            except Exception:
                pass

        # 2. Fall back to CLI
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(BASE_DIR),
            )
            if result.stdout and result.stdout.strip():
                return result.stdout.strip()
            return None
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def run(self) -> dict:
        raise NotImplementedError

    def get_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "category": self.category,
            "last_run": self.run_log[-1] if self.run_log else None,
            "total_runs": len(self.run_log),
        }
