import pytest

from app.models import IgnoredMaterialInput, LoadoutCreate
from app.services.storage import create_loadout, set_ignored_material


def test_set_ignored_material_adds_and_removes(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Test"))

    updated = set_ignored_material(loadout.id, IgnoredMaterialInput(item="Milk Bottle", ignored=True))
    assert updated.ignored_materials == ["Milk Bottle"]

    again = set_ignored_material(loadout.id, IgnoredMaterialInput(item="Milk Bottle", ignored=True))
    assert again.ignored_materials == ["Milk Bottle"]

    restored = set_ignored_material(loadout.id, IgnoredMaterialInput(item="milk bottle", ignored=False))
    assert restored.ignored_materials == []


def test_set_ignored_material_raises_for_missing_loadout(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    with pytest.raises(KeyError):
        set_ignored_material("missing", IgnoredMaterialInput(item="Milk Bottle", ignored=True))
