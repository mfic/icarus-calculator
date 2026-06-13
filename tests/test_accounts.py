import pytest

from app.models import CollectedItemInput, LoadoutCreate, ShareInput
from app.services.storage import (
    create_loadout,
    delete_loadout,
    get_authorized_loadout,
    loadouts_for_account,
    set_collected_item,
    set_loadout_share,
    set_storage_item,
)


def test_create_loadout_sets_owner(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Test"), owner_id="acct-1")

    assert loadout.owner_id == "acct-1"
    assert loadout.shared_with == []


def test_loadouts_for_account_filters_by_owner_and_shared(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    owned = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")
    create_loadout(LoadoutCreate(name="Other"), owner_id="acct-2")
    shared = set_loadout_share(owned.id, "acct-1", ShareInput(account_id="acct-2", shared=True))

    visible_to_owner = {loadout.id for loadout in loadouts_for_account("acct-1")}
    visible_to_shared = {loadout.id for loadout in loadouts_for_account("acct-2")}

    assert visible_to_owner == {owned.id}
    assert shared.id in visible_to_shared
    assert owned.id in visible_to_shared


def test_mutation_raises_keyerror_for_unauthorized_account(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    with pytest.raises(KeyError):
        set_collected_item(loadout.id, "acct-2", CollectedItemInput(item="Stick", quantity=1))


def test_set_storage_item_sets_and_clears(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    updated = set_storage_item(loadout.id, "acct-1", CollectedItemInput(item="Dough", quantity=2))
    assert updated.in_storage == {"Dough": 2}

    cleared = set_storage_item(loadout.id, "acct-1", CollectedItemInput(item="Dough", quantity=0))
    assert cleared.in_storage == {}


def test_set_storage_item_raises_keyerror_for_unauthorized_account(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    with pytest.raises(KeyError):
        set_storage_item(loadout.id, "acct-2", CollectedItemInput(item="Dough", quantity=2))


def test_get_authorized_loadout_returns_none_without_access(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    assert get_authorized_loadout(loadout.id, "acct-1") is not None
    assert get_authorized_loadout(loadout.id, "acct-2") is None


def test_set_loadout_share_add_and_remove(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    shared = set_loadout_share(loadout.id, "acct-1", ShareInput(account_id="acct-2", shared=True))
    assert shared.shared_with == ["acct-2"]

    unshared = set_loadout_share(loadout.id, "acct-1", ShareInput(account_id="acct-2", shared=False))
    assert unshared.shared_with == []


def test_set_loadout_share_requires_owner(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")
    set_loadout_share(loadout.id, "acct-1", ShareInput(account_id="acct-2", shared=True))

    with pytest.raises(PermissionError):
        set_loadout_share(loadout.id, "acct-2", ShareInput(account_id="acct-3", shared=True))


def test_set_loadout_share_raises_keyerror_without_access(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")

    with pytest.raises(KeyError):
        set_loadout_share(loadout.id, "acct-2", ShareInput(account_id="acct-3", shared=True))


def test_delete_loadout_requires_owner(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Owned"), owner_id="acct-1")
    set_loadout_share(loadout.id, "acct-1", ShareInput(account_id="acct-2", shared=True))

    with pytest.raises(PermissionError):
        delete_loadout(loadout.id, "acct-2")

    delete_loadout(loadout.id, "acct-1")
    assert loadouts_for_account("acct-1") == []
