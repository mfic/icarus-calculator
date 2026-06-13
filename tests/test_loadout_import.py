from app.models import LoadoutImport, LoadoutItem
from app.services.storage import import_loadout


def test_import_loadout_gets_new_uuid(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = import_loadout(
        LoadoutImport(
            name="Shared Run",
            items=[LoadoutItem(item="Dirt Ramp", quantity=2)],
            collected={"Dirt": 5},
        )
    )

    assert loadout.id
    assert loadout.name == "Shared Run"
    assert loadout.items[0].item == "Dirt Ramp"
    assert loadout.collected == {"Dirt": 5}
