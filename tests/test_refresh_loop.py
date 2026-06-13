from datetime import datetime, timedelta, timezone

from app.scripts.refresh_loop import REFRESH_INTERVAL_SECONDS, seconds_since_last_refresh
from app.services.storage import write_json


def test_seconds_since_last_refresh_returns_none_without_data(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "ITEMS_PATH", tmp_path / "items.json")

    assert seconds_since_last_refresh() is None


def test_seconds_since_last_refresh_recent_data_is_below_interval(monkeypatch, tmp_path):
    import app.services.storage as storage

    items_path = tmp_path / "items.json"
    monkeypatch.setattr(storage, "ITEMS_PATH", items_path)

    refreshed_at = datetime.now(timezone.utc).isoformat()
    write_json(items_path, {"refreshed_at": refreshed_at, "items": []})

    age = seconds_since_last_refresh()
    assert age is not None
    assert 0 <= age < REFRESH_INTERVAL_SECONDS


def test_seconds_since_last_refresh_stale_data_exceeds_interval(monkeypatch, tmp_path):
    import app.services.storage as storage

    items_path = tmp_path / "items.json"
    monkeypatch.setattr(storage, "ITEMS_PATH", items_path)

    refreshed_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    write_json(items_path, {"refreshed_at": refreshed_at, "items": []})

    age = seconds_since_last_refresh()
    assert age is not None
    assert age > REFRESH_INTERVAL_SECONDS
