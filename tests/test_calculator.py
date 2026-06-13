from app.models import Ingredient, Item, Loadout, LoadoutItem, Recipe
from app.services.calculator import calculate_loadout, resolve_materials


def test_calculate_loadout_expands_intermediate_recipes():
    items = [
        Item(
            name="Pie",
            slug="Pie",
            recipe=Recipe(
                inputs=[Ingredient(name="Dough", quantity=2), Ingredient(name="Berry", quantity=4)],
                outputs=[Ingredient(name="Pie", quantity=1)],
                benches=["Stove"],
            ),
            benches=["Stove"],
        ),
        Item(
            name="Dough",
            slug="Dough",
            recipe=Recipe(
                inputs=[Ingredient(name="Flour", quantity=1), Ingredient(name="Water", quantity=1)],
                outputs=[Ingredient(name="Dough", quantity=1)],
                benches=["Cooking Station"],
            ),
            benches=["Cooking Station"],
        ),
    ]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[LoadoutItem(item="Pie", quantity=3)],
        collected={"Flour": 2},
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert result["materials"] == [
        {"name": "Berry", "quantity": 12, "collected": 0, "remaining": 12, "sources": ["Pie"]},
        {"name": "Flour", "quantity": 6, "collected": 2, "remaining": 4, "sources": ["Pie"]},
        {"name": "Water", "quantity": 6, "collected": 0, "remaining": 6, "sources": ["Pie"]},
    ]
    assert [step["item"] for step in result["steps"]] == ["Pie", "Dough"]
    assert all(step["sources"] == ["Pie"] for step in result["steps"])


def test_calculate_loadout_merges_steps_for_shared_subrecipes():
    items = [
        Item(
            name="Plank",
            slug="Plank",
            recipe=Recipe(
                inputs=[Ingredient(name="Wood", quantity=2)],
                outputs=[Ingredient(name="Plank", quantity=1)],
                benches=["Workbench"],
            ),
        ),
        Item(
            name="Crate",
            slug="Crate",
            recipe=Recipe(
                inputs=[Ingredient(name="Plank", quantity=4)],
                outputs=[Ingredient(name="Crate", quantity=1)],
                benches=["Workbench"],
            ),
        ),
        Item(
            name="Shelf",
            slug="Shelf",
            recipe=Recipe(
                inputs=[Ingredient(name="Plank", quantity=2)],
                outputs=[Ingredient(name="Shelf", quantity=1)],
                benches=["Workbench"],
            ),
        ),
    ]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[LoadoutItem(item="Crate", quantity=1), LoadoutItem(item="Shelf", quantity=1)],
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert [step["item"] for step in result["steps"]] == ["Crate", "Plank", "Shelf"]
    plank_step = next(step for step in result["steps"] if step["item"] == "Plank")
    assert plank_step["quantity"] == 6
    assert plank_step["batches"] == 6
    assert plank_step["inputs"] == [{"name": "Wood", "quantity": 12}]
    assert plank_step["sources"] == ["Crate", "Shelf"]

    wood_material = next(material for material in result["materials"] if material["name"] == "Wood")
    assert wood_material["sources"] == ["Crate", "Shelf"]


def test_calculate_loadout_ignored_material_cascades_to_sub_ingredients():
    items = [
        Item(
            name="Plank",
            slug="Plank",
            recipe=Recipe(
                inputs=[Ingredient(name="Wood", quantity=2)],
                outputs=[Ingredient(name="Plank", quantity=1)],
                benches=["Workbench"],
            ),
        ),
        Item(
            name="Crate",
            slug="Crate",
            recipe=Recipe(
                inputs=[Ingredient(name="Plank", quantity=4)],
                outputs=[Ingredient(name="Crate", quantity=1)],
                benches=["Workbench"],
            ),
        ),
        Item(
            name="Shelf",
            slug="Shelf",
            recipe=Recipe(
                inputs=[Ingredient(name="Plank", quantity=2)],
                outputs=[Ingredient(name="Shelf", quantity=1)],
                benches=["Workbench"],
            ),
        ),
        Item(
            name="Torch",
            slug="Torch",
            recipe=Recipe(
                inputs=[Ingredient(name="Stick", quantity=1)],
                outputs=[Ingredient(name="Torch", quantity=1)],
                benches=["Workbench"],
            ),
        ),
    ]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[
            LoadoutItem(item="Crate", quantity=1),
            LoadoutItem(item="Shelf", quantity=1),
            LoadoutItem(item="Torch", quantity=1),
        ],
        ignored_materials=["Plank"],
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert result["materials"] == [
        {"name": "Stick", "quantity": 1, "collected": 0, "remaining": 1, "sources": ["Torch"]},
    ]
    assert [step["item"] for step in result["steps"]] == ["Crate", "Shelf", "Torch"]


def _epoxy_item() -> Item:
    sulfur_recipe = Recipe(
        inputs=[Ingredient(name="Sulfur", quantity=2), Ingredient(name="Tree Sap", quantity=4)],
        outputs=[Ingredient(name="Epoxy", quantity=1)],
        benches=["Mortar and Pestle"],
        id="sulfur+tree sap",
        label="2 Sulfur + 4 Tree Sap",
    )
    bone_recipe = Recipe(
        inputs=[Ingredient(name="Crushed Bone", quantity=4)],
        outputs=[Ingredient(name="Epoxy", quantity=1)],
        benches=["Mortar and Pestle"],
        id="crushed bone",
        label="4 Crushed Bone",
    )
    return Item(
        name="Epoxy",
        slug="Epoxy",
        recipe=sulfur_recipe,
        recipes=[sulfur_recipe, bone_recipe],
        benches=["Mortar and Pestle"],
    )


def test_resolve_materials_defaults_to_first_recipe():
    items_by_name = {"epoxy": _epoxy_item()}

    totals, steps = resolve_materials("Epoxy", 2, items_by_name)

    assert totals == {"Sulfur": 4, "Tree Sap": 8}
    assert steps[0]["inputs"] == [
        {"name": "Sulfur", "quantity": 4},
        {"name": "Tree Sap", "quantity": 8},
    ]


def test_resolve_materials_uses_recipe_choice():
    items_by_name = {"epoxy": _epoxy_item()}

    totals, steps = resolve_materials("Epoxy", 2, items_by_name, recipe_choices={"Epoxy": "crushed bone"})

    assert totals == {"Crushed Bone": 8}
    assert steps[0]["inputs"] == [{"name": "Crushed Bone", "quantity": 8}]


def test_resolve_materials_returns_empty_for_ignored_item():
    items_by_name = {"epoxy": _epoxy_item()}

    totals, steps = resolve_materials("Epoxy", 2, items_by_name, ignored=frozenset({"epoxy"}))

    assert totals == {}
    assert steps == []


def test_calculate_loadout_includes_recipe_options_for_multi_recipe_items():
    items = [_epoxy_item()]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[LoadoutItem(item="Epoxy", quantity=2)],
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert len(result["recipe_options"]) == 1
    options = result["recipe_options"][0]
    assert options["item"] == "Epoxy"
    assert options["selected"] == "sulfur+tree sap"
    assert [option["id"] for option in options["options"]] == ["sulfur+tree sap", "crushed bone"]


def test_calculate_loadout_recipe_options_respects_choice():
    items = [_epoxy_item()]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[LoadoutItem(item="Epoxy", quantity=2)],
        recipe_choices={"Epoxy": "crushed bone"},
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert result["recipe_options"][0]["selected"] == "crushed bone"
    assert result["materials"] == [
        {"name": "Crushed Bone", "quantity": 8, "collected": 0, "remaining": 8, "sources": ["Epoxy"]}
    ]


def test_calculate_loadout_recipe_options_empty_for_single_recipe_items():
    items = [
        Item(
            name="Plank",
            slug="Plank",
            recipe=Recipe(
                inputs=[Ingredient(name="Wood", quantity=2)],
                outputs=[Ingredient(name="Plank", quantity=1)],
                benches=["Workbench"],
            ),
        ),
    ]
    loadout = Loadout(
        id="loadout",
        name="Loadout",
        items=[LoadoutItem(item="Plank", quantity=1)],
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert result["recipe_options"] == []
