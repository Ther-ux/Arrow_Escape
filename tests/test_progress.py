import json

from core.progress import load_endless_level, save_endless_level


def test_endless_progress_round_trip(tmp_path):
    path = tmp_path / "progress.json"
    save_endless_level(7, path)
    assert load_endless_level(path) == 7


def test_invalid_endless_progress_falls_back_to_first_level(tmp_path):
    path = tmp_path / "progress.json"
    path.write_text(json.dumps({"next_level": "not a number"}), encoding="utf-8")
    assert load_endless_level(path) == 1


def test_missing_endless_progress_starts_at_first_level(tmp_path):
    assert load_endless_level(tmp_path / "missing.json") == 1
