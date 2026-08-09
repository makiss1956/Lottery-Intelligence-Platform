"""
Centralized configuration loader for Lottery Intelligence Platform.
Supports YAML config with environment variable overrides.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from src.core.logger import get_logger

logger = get_logger("Config")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


class Config:
    """Singleton-style configuration manager."""

    _instance: Optional["Config"] = None
    _data: Dict[str, Any] = {}

    def __new__(cls, config_path: Optional[Path] = None) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(config_path or DEFAULT_CONFIG_PATH)
        return cls._instance

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning(f"Config file not found at {path}. Using defaults.")
            self._data = self._defaults()
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
            # Override with environment variables (e.g., LOTTERY_DB_PATH)
            self._apply_env_overrides()
            logger.info(f"Configuration loaded from {path}")
        except Exception as e:
            logger.error(f"Error loading config file at {path}: {e}")
            self._data = self._defaults()

    def _defaults(self) -> Dict[str, Any]:
        return {
            "database": {"path": "data/lottery.db"},
            "analytics": {
                "default_primary_candidates": 7,
                "default_euro_candidates": 3,
                "cache_ttl_minutes": 60,
            },
            "importer": {"timeout_seconds": 30, "max_retries": 3},
        }

    def _apply_env_overrides(self) -> None:
        """Allow env vars like LOTTERY_DB_PATH to override YAML values."""
        env_map = {
            "LOTTERY_DB_PATH": ("database", "path"),
            "LOTTERY_SMTP_SERVER": ("notifications", "email", "smtp_server"),
            "LOTTERY_SMTP_PORT": ("notifications", "email", "smtp_port"),
        }
        for env_var, keys in env_map.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(keys, value)

    def _set_nested(self, keys: tuple, value: Any) -> None:
        d = self._data
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get nested config value: config.get('database', 'path')."""
        d = self._data
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d

    @property
    def database_path(self) -> str:
        return self.get("database", "path", default="data/lottery.db")

    @property
    def cache_ttl(self) -> int:
        return self.get("analytics", "cache_ttl_minutes", default=60)


# Global accessor
def get_config() -> Config:
    return Config()
