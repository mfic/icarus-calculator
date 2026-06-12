from app.models import Bucket, BucketItem, FoodItem, Ingredient, Recipe
from app.services.calculator import calculate_bucket


def test_calculate_bucket_expands_intermediate_recipes():
    foods = [
        FoodItem(
            name="Pie",
            slug="Pie",
            recipe=Recipe(
                inputs=[Ingredient(name="Dough", quantity=2), Ingredient(name="Berry", quantity=4)],
                outputs=[Ingredient(name="Pie", quantity=1)],
                benches=["Stove"],
            ),
            benches=["Stove"],
        ),
        FoodItem(
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
    bucket = Bucket(
        id="loadout",
        name="Loadout",
        items=[BucketItem(food="Pie", quantity=3)],
        created_at="2026-06-12T00:00:00+00:00",
        updated_at="2026-06-12T00:00:00+00:00",
    )

    result = calculate_bucket(bucket, foods)

    assert result["materials"] == [
        {"name": "Berry", "quantity": 12},
        {"name": "Flour", "quantity": 6},
        {"name": "Water", "quantity": 6},
    ]
    assert [step["item"] for step in result["steps"]] == ["Pie", "Dough"]
