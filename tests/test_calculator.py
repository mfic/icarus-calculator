from app.models import Ingredient, Item, Loadout, LoadoutItem, Recipe
from app.services.calculator import calculate_loadout


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
        farmed={"Flour": 2},
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_loadout(loadout, items)

    assert result["materials"] == [
        {"name": "Berry", "quantity": 12, "farmed": 0, "remaining": 12},
        {"name": "Flour", "quantity": 6, "farmed": 2, "remaining": 4},
        {"name": "Water", "quantity": 6, "farmed": 0, "remaining": 6},
    ]
    assert [step["item"] for step in result["steps"]] == ["Pie", "Dough"]
