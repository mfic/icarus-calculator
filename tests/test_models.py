import pytest
from pydantic import ValidationError

from app.models import LoadoutImport, LoadoutItem, LoadoutItemInput


def test_loadout_item_rejects_empty_name():
    with pytest.raises(ValidationError):
        LoadoutItem(item="")


def test_loadout_item_rejects_overlong_name():
    with pytest.raises(ValidationError):
        LoadoutItem(item="x" * 121)


def test_loadout_item_input_rejects_empty_name():
    with pytest.raises(ValidationError):
        LoadoutItemInput(item="")


def test_loadout_import_rejects_too_many_items():
    with pytest.raises(ValidationError):
        LoadoutImport(
            name="Big Loadout",
            items=[LoadoutItem(item=f"Item {i}") for i in range(501)],
        )


def test_loadout_import_rejects_too_many_collected_entries():
    with pytest.raises(ValidationError):
        LoadoutImport(name="Big Loadout", collected={f"item-{i}": 1 for i in range(501)})


def test_loadout_import_rejects_overlong_collected_key():
    with pytest.raises(ValidationError):
        LoadoutImport(name="Big Loadout", collected={"x" * 121: 1})


def test_loadout_import_rejects_too_many_recipe_choice_entries():
    with pytest.raises(ValidationError):
        LoadoutImport(name="Big Loadout", recipe_choices={f"item-{i}": "recipe" for i in range(501)})


def test_loadout_import_rejects_overlong_recipe_choice_key():
    with pytest.raises(ValidationError):
        LoadoutImport(name="Big Loadout", recipe_choices={"x" * 121: "recipe"})


def test_loadout_import_rejects_overlong_recipe_choice_value():
    with pytest.raises(ValidationError):
        LoadoutImport(name="Big Loadout", recipe_choices={"Epoxy": "x" * 201})
