from collections import defaultdict
from typing import Any

from app.models import Ingredient, Item, Loadout, Recipe


def _item_index(items: list[Item]) -> dict[str, Item]:
    return {item.name.lower(): item for item in items}


def _round(value: float) -> int | float:
    return int(value) if value.is_integer() else round(value, 3)


def _item_recipes(item: Item) -> list[Recipe]:
    return item.recipes or ([item.recipe] if item.recipe else [])


def _select_recipe(item: Item, recipe_choices: dict[str, str]) -> Recipe | None:
    recipes = _item_recipes(item)
    if not recipes:
        return None
    chosen_id = recipe_choices.get(item.name)
    if chosen_id:
        for recipe in recipes:
            if recipe.id == chosen_id:
                return recipe
    return recipes[0]


def resolve_materials(
    item_name: str,
    quantity: float,
    items_by_name: dict[str, Item],
    recipe_choices: dict[str, str] | None = None,
    trail: tuple[str, ...] = (),
    ignored: frozenset[str] = frozenset(),
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    recipe_choices = recipe_choices or {}
    if item_name.lower() in ignored:
        return {}, []
    item = items_by_name.get(item_name.lower())
    recipe = _select_recipe(item, recipe_choices) if item else None
    if not item or not recipe or not recipe.inputs or item.name in trail:
        return {item_name: quantity}, []

    output_qty = recipe.outputs[0].quantity if recipe.outputs else 1
    batches = quantity / output_qty
    step_inputs: list[Ingredient] = [
        Ingredient(name=ingredient.name, quantity=ingredient.quantity * batches)
        for ingredient in recipe.inputs
    ]
    steps: list[dict[str, Any]] = [
        {
            "item": item.name,
            "quantity": _round(quantity),
            "batches": _round(batches),
            "benches": recipe.benches or item.benches,
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
            recipe_choices,
            trail + (item.name,),
            ignored,
        )
        for name, amount in child_totals.items():
            totals[name] += amount
        steps.extend(child_steps)

    return dict(totals), steps


def _merge_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for step in steps:
        key = step["item"]
        if key not in merged:
            merged[key] = {
                "item": step["item"],
                "quantity": 0.0,
                "batches": 0.0,
                "benches": step["benches"],
                "inputs": {},
            }
            order.append(key)
        entry = merged[key]
        entry["quantity"] += step["quantity"]
        entry["batches"] += step["batches"]
        for ingredient in step["inputs"]:
            entry["inputs"][ingredient["name"]] = entry["inputs"].get(ingredient["name"], 0.0) + ingredient["quantity"]

    return [
        {
            "item": entry["item"],
            "quantity": _round(entry["quantity"]),
            "batches": _round(entry["batches"]),
            "benches": entry["benches"],
            "inputs": [
                {"name": name, "quantity": _round(quantity)}
                for name, quantity in entry["inputs"].items()
            ],
        }
        for entry in (merged[key] for key in order)
    ]


def calculate_loadout(loadout: Loadout, items: list[Item]) -> dict[str, Any]:
    items_by_name = _item_index(items)
    materials: dict[str, float] = defaultdict(float)
    material_sources: dict[str, list[str]] = {}
    step_sources: dict[str, list[str]] = {}
    steps: list[dict[str, Any]] = []
    missing: list[str] = []

    ignored = frozenset(name.lower() for name in loadout.ignored_materials)
    for loadout_item in loadout.items:
        totals, item_steps = resolve_materials(
            loadout_item.item, loadout_item.quantity, items_by_name, loadout.recipe_choices, ignored=ignored
        )
        if loadout_item.item.lower() not in items_by_name:
            missing.append(loadout_item.item)
        for name, amount in totals.items():
            materials[name] += amount
            sources = material_sources.setdefault(name, [])
            if loadout_item.item not in sources:
                sources.append(loadout_item.item)
        for step in item_steps:
            sources = step_sources.setdefault(step["item"], [])
            if loadout_item.item not in sources:
                sources.append(loadout_item.item)
        steps.extend(item_steps)

    merged_steps = _merge_steps(steps)
    for step in merged_steps:
        step["sources"] = step_sources.get(step["item"], [])

    crafted_totals = {step["item"]: step["quantity"] for step in merged_steps}
    storage_items = [
        {
            "name": name,
            "quantity": _round(total),
            "have": _round(float(loadout.in_storage.get(name, 0))),
            "remaining": _round(max(total - float(loadout.in_storage.get(name, 0)), 0)),
        }
        for name, total in sorted(crafted_totals.items(), key=lambda entry: entry[0].lower())
    ]

    reduced_materials: dict[str, float] = dict(materials)
    reduced_steps = [
        {**step, "inputs": [dict(ingredient) for ingredient in step["inputs"]]} for step in merged_steps
    ]
    for name, have in loadout.in_storage.items():
        amount = min(float(have), crafted_totals.get(name, 0))
        if amount <= 0:
            continue
        reduction_materials, reduction_steps = resolve_materials(
            name, amount, items_by_name, loadout.recipe_choices, ignored=ignored
        )
        for material_name, material_amount in reduction_materials.items():
            if material_name in reduced_materials:
                reduced_materials[material_name] = max(reduced_materials[material_name] - material_amount, 0)

        reduction_by_item: dict[str, dict[str, Any]] = {}
        for reduction_step in reduction_steps:
            entry = reduction_by_item.setdefault(
                reduction_step["item"], {"quantity": 0.0, "batches": 0.0, "inputs": defaultdict(float)}
            )
            entry["quantity"] += reduction_step["quantity"]
            entry["batches"] += reduction_step["batches"]
            for ingredient in reduction_step["inputs"]:
                entry["inputs"][ingredient["name"]] += ingredient["quantity"]

        for step in reduced_steps:
            reduction = reduction_by_item.get(step["item"])
            if not reduction:
                continue
            step["quantity"] = max(step["quantity"] - reduction["quantity"], 0)
            step["batches"] = max(step["batches"] - reduction["batches"], 0)
            for ingredient in step["inputs"]:
                ingredient["quantity"] = max(
                    ingredient["quantity"] - reduction["inputs"].get(ingredient["name"], 0), 0
                )

    merged_steps = [step for step in reduced_steps if step["quantity"] > 0]
    for step in merged_steps:
        step["quantity"] = _round(step["quantity"])
        step["batches"] = _round(step["batches"])
        step["inputs"] = [
            {"name": ingredient["name"], "quantity": _round(ingredient["quantity"])}
            for ingredient in step["inputs"]
            if ingredient["quantity"] > 0
        ]
    materials = reduced_materials

    recipe_options: list[dict[str, Any]] = []
    for step in merged_steps:
        item = items_by_name.get(step["item"].lower())
        if not item:
            continue
        recipes = _item_recipes(item)
        if len(recipes) <= 1:
            continue
        selected = _select_recipe(item, loadout.recipe_choices)
        recipe_options.append(
            {
                "item": item.name,
                "selected": selected.id if selected else "",
                "options": [
                    {
                        "id": recipe.id,
                        "label": recipe.label,
                        "inputs": [
                            {"name": ingredient.name, "quantity": _round(ingredient.quantity)}
                            for ingredient in recipe.inputs
                        ],
                        "benches": recipe.benches,
                    }
                    for recipe in recipes
                ],
            }
        )

    return {
        "loadout": loadout.model_dump(),
        "bucket": loadout.model_dump(),
        "materials": [
            {
                "name": name,
                "quantity": quantity,
                "collected": _round(float(loadout.collected.get(name, 0))),
                "remaining": _round(max(amount - float(loadout.collected.get(name, 0)), 0)),
                "sources": material_sources.get(name, []),
            }
            for name, amount in sorted(materials.items(), key=lambda entry: entry[0].lower())
            if (quantity := _round(amount))
        ],
        "collected": loadout.collected,
        "steps": merged_steps,
        "storage_items": storage_items,
        "recipe_options": recipe_options,
        "missing": missing,
    }


calculate_bucket = calculate_loadout
