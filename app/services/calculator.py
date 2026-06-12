from collections import defaultdict
from typing import Any

from app.models import Bucket, FoodItem, Ingredient


def _food_index(foods: list[FoodItem]) -> dict[str, FoodItem]:
    return {food.name.lower(): food for food in foods}


def _round(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 3)


def resolve_materials(
    item_name: str,
    quantity: float,
    foods_by_name: dict[str, FoodItem],
    trail: tuple[str, ...] = (),
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    item = foods_by_name.get(item_name.lower())
    if not item or not item.recipe or not item.recipe.inputs or item.name in trail:
        return {item_name: quantity}, []

    output_qty = item.recipe.outputs[0].quantity if item.recipe.outputs else 1
    batches = quantity / output_qty
    step_inputs: list[Ingredient] = [
        Ingredient(name=ingredient.name, quantity=ingredient.quantity * batches)
        for ingredient in item.recipe.inputs
    ]
    steps: list[dict[str, Any]] = [
        {
            "item": item.name,
            "quantity": _round(quantity),
            "batches": _round(batches),
            "benches": item.recipe.benches or item.benches,
            "inputs": [
                {"name": ingredient.name, "quantity": _round(ingredient.quantity)}
                for ingredient in step_inputs
            ],
        }
    ]

    totals: dict[str, float] = defaultdict(float)
    for ingredient in step_inputs:
        child_totals, child_steps = resolve_materials(
            ingredient.name,
            ingredient.quantity,
            foods_by_name,
            trail + (item.name,),
        )
        for name, amount in child_totals.items():
            totals[name] += amount
        steps.extend(child_steps)

    return dict(totals), steps


def calculate_bucket(bucket: Bucket, foods: list[FoodItem]) -> dict[str, Any]:
    foods_by_name = _food_index(foods)
    materials: dict[str, float] = defaultdict(float)
    steps: list[dict[str, Any]] = []
    missing: list[str] = []

    for item in bucket.items:
        totals, item_steps = resolve_materials(item.food, item.quantity, foods_by_name)
        if item.food.lower() not in foods_by_name:
            missing.append(item.food)
        for name, amount in totals.items():
            materials[name] += amount
        steps.extend(item_steps)

    return {
        "bucket": bucket.model_dump(),
        "materials": [
            {"name": name, "quantity": _round(amount)}
            for name, amount in sorted(materials.items(), key=lambda entry: entry[0].lower())
        ],
        "steps": steps,
        "missing": missing,
    }
