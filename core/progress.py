"""Small local progress store for endless mode."""

import json
from pathlib import Path


DEFAULT_PROGRESS_PATH = Path(__file__).resolve().parents[1] / "data" / "endless_progress.json"


def load_endless_level(path: Path = DEFAULT_PROGRESS_PATH) -> int:
    """Return the next endless level to play, defaulting to level one."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        level = int(payload["next_level"])
        return max(1, level)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return 1


def save_endless_level(level: int, path: Path = DEFAULT_PROGRESS_PATH) -> None:
    """Persist the next endless level, creating its parent directory if needed."""
    if level < 1:
        raise ValueError("endless level must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"next_level": level}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
