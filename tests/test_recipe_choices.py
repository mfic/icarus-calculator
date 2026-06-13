import pytest

from app.models import LoadoutCreate, RecipeChoiceInput
from app.services.storage import create_loadout, set_recipe_choice


def test_set_recipe_choice_sets_and_resets(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    loadout = create_loadout(LoadoutCreate(name="Test"), owner_id="acct-1")

    updated = set_recipe_choice(loadout.id, "acct-1", RecipeChoiceInput(item="Epoxy", recipe_id="crushed bone"))
    assert updated.recipe_choices == {"Epoxy": "crushed bone"}

    reset = set_recipe_choice(loadout.id, "acct-1", RecipeChoiceInput(item="Epoxy", recipe_id=""))
    assert reset.recipe_choices == {}


def test_set_recipe_choice_raises_for_missing_loadout(monkeypatch, tmp_path):
    import app.services.storage as storage

    monkeypatch.setattr(storage, "LOADOUTS_PATH", tmp_path / "loadouts.json")

    with pytest.raises(KeyError):
        set_recipe_choice("missing", "acct-1", RecipeChoiceInput(item="Epoxy", recipe_id="crushed bone"))
