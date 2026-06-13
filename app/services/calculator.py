from collections import defaultdict
from typing import Any

from app.models import Ingredient, Item, Loadout


def _item_index(items: list[Item]) -> dict[str, Item]:
    return {item.name.lower(): item for item in items}


def _round(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 3)


def resolve_materials(
    item_name: str,
    quantity: float,
    items_by_name: dict[str, Item],
    trail: tuple[str, ...] = (),
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    item = items_by_name.get(item_name.lower())
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
            items_by_name,
            trail + (item.name,),
        )
        for name, amount in child_totals.items():
            totals[name] += amount
        steps.extend(child_steps)

    return dict(totals), steps


def calculate_loadout(loadout: Loadout, items: list[Item]) -> dict[str, Any]:
    items_by_name = _item_index(items)
    materials: dict[str, float] = defaultdict(float)
    steps: list[dict[str, Any]] = []
    missing: list[str] = []

    for loadout_item in loadout.items:
        totals, item_steps = resolve_materials(loadout_item.item, loadout_item.quantity, items_by_name)
        if loadout_item.item.lower() not in items_by_name:
            missing.append(loadout_item.item)
        for name, amount in totals.items():
            materials[name] += amount
        steps.extend(item_steps)

    return {
        "loadout": loadout.model_dump(),
        "bucket": loadout.model_dump(),
        "materials": [
            {
                "name": name,
                "quantity": _round(amount),
                "collected": _round(float(loadout.collected.get(name, 0))),
                "remaining": _round(max(amount - float(loadout.collected.get(name, 0)), 0)),
            }
            for name, amount in sorted(materials.items(), key=lambda entry: entry[0].lower())
        ],
        "collected": loadout.collected,
        "steps": steps,
        "missing": missing,
    }


calculate_bucket = calculate_loadout
