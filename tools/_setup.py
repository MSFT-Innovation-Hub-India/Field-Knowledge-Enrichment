"""Shared setup for CLI tools: make the package importable and load settings."""
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
for noisy in ("azure", "urllib3", "httpx", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
