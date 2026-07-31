from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATABASE = ROOT / "database" / "lottery.db"

DATASETS = ROOT / "datasets"

EXPORTS = ROOT / "exports"

LOGS = ROOT / "logs"
