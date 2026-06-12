from app.main import filter_items
from app.models import FoodItem, Ingredient, Recipe


def test_category_filter_applies_before_search():
    items = [
        FoodItem(
            name="Banana Bread",
            slug="Banana_Bread",
            categories=["Food", "Consumables"],
            buffs=["Maximum Stamina"],
        ),
        FoodItem(
            name="Iron Knife",
            slug="Iron_Knife",
            categories=["Weapons"],
            recipe=Recipe(inputs=[Ingredient(name="Iron Ingot", quantity=2)]),
        ),
    ]

    result = filter_items(items, q="iron", category="Food")

    assert result == []
