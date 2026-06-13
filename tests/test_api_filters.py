from app.main import _tier_sort_key, filter_items
from app.services.wiki import classify_primary_category
from app.models import Ingredient, Item, Recipe


def test_category_filter_applies_before_search():
    items = [
        Item(
            name="Banana Bread",
            slug="Banana_Bread",
            primary_category="Consumables",
            categories=["Food", "Consumables"],
            buffs=["Maximum Stamina"],
        ),
        Item(
            name="Iron Knife",
            slug="Iron_Knife",
            primary_category="Weapons",
            categories=["Weapons"],
            tier="Tier 2",
            recipe=Recipe(inputs=[Ingredient(name="Iron Ingot", quantity=2)]),
        ),
    ]

    result = filter_items(items, q="iron", category="Food")

    assert result == []


def test_search_matches_tier():
    items = [
        Item(name="Stone Axe", slug="Stone_Axe", categories=["Tools"], tier="Tier 1"),
        Item(name="Iron Knife", slug="Iron_Knife", categories=["Weapons"], tier="Tier 2"),
    ]

    result = filter_items(items, q="tier 2")

    assert [item.name for item in result] == ["Iron Knife"]


def test_tier_filter_applies_before_search():
    items = [
        Item(name="Iron Knife", slug="Iron_Knife", categories=["Weapons"], tier="Tier 2"),
        Item(name="Steel Knife", slug="Steel_Knife", categories=["Weapons"], tier="Tier 3"),
    ]

    result = filter_items(items, q="knife", tier="Tier 3")

    assert [item.name for item in result] == ["Steel Knife"]


def test_primary_and_subcategory_filters_apply_before_search():
    items = [
        Item(name="9mm Round", slug="9mm_Round", primary_category="Projectiles", categories=["Ammo", "9mm Rounds"]),
        Item(name="Iron Knife", slug="Iron_Knife", primary_category="Weapons", categories=["Weapons", "Knives"]),
    ]

    result = filter_items(items, q="round", category="Projectiles", subcategory="9mm Rounds")

    assert [item.name for item in result] == ["9mm Round"]


def test_name_fallback_classifies_uncategorized_projectiles():
    assert classify_primary_category(["Items"], "9mm Lithium Round") == "Projectiles"


def test_tier_sort_key_handles_mixed_numeric_and_text_tiers():
    entries = [("Tier 10", 1), ("Tier 2", 1), ("Bonus", 1), ("Tier 1", 1)]

    result = sorted(entries, key=_tier_sort_key)

    assert [name for name, _ in result] == ["Tier 1", "Tier 2", "Tier 10", "Bonus"]
