from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.models import (
    CollectedItemInput,
    IgnoredMaterialInput,
    Item,
    LoadoutCreate,
    LoadoutImport,
    LoadoutItemInput,
    RecipeChoiceInput,
)
from app.services.calculator import _item_recipes, calculate_loadout
from app.services.storage import (
    create_loadout,
    delete_loadout,
    delete_loadout_item,
    clear_collected_items,
    import_loadout,
    item_metadata,
    load_items,
    load_loadouts,
    set_collected_item,
    set_ignored_material,
    set_recipe_choice,
    upsert_loadout_item,
)


CATEGORY_ORDER = [
    "Tools",
    "Bows",
    "Projectiles",
    "Weapons",
    "Deployables",
    "Structures",
    "Armor",
    "Storage",
    "Consumables",
    "Resources",
    "Mission Items",
    "Other",
]


app = FastAPI(title="ICARUS Resource Calculator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/favicon.ico")
def favicon() -> FileResponse:
    return FileResponse(static_dir / "favicon.ico")


@app.get("/gather")
def gather() -> FileResponse:
    return FileResponse(static_dir / "gather.html")


@app.get("/api/meta")
def meta() -> dict:
    return item_metadata()


def filter_items(
    items: list[Item],
    q: str | None = None,
    category: str | None = None,
    subcategory: str | None = None,
    tier: str | None = None,
) -> list[Item]:
    if category:
        category_needle = category.lower()
        items = [
            item
            for item in items
            if item.primary_category.lower() == category_needle
            or any(category_needle == item_category.lower() for item_category in item.categories)
        ]
    if subcategory:
        subcategory_needle = subcategory.lower()
        items = [
            item
            for item in items
            if any(subcategory_needle == item_category.lower() for item_category in item.categories)
        ]
    if tier:
        tier_needle = tier.lower()
        items = [item for item in items if item.tier and item.tier.lower() == tier_needle]
    if q:
        needle = q.lower()
        items = [
            item
            for item in items
            if needle in item.name.lower()
            or any(needle in effect.lower() for effect in item.effects)
            or any(needle in buff.lower() for buff in item.buffs)
            or any(needle in bench.lower() for bench in item.benches)
            or (item.tier and needle in item.tier.lower())
            or any(
                needle in ingredient.name.lower()
                for recipe in _item_recipes(item)
                for ingredient in recipe.inputs
            )
            or any(needle in category.lower() for category in item.categories)
        ]
    return items


@app.get("/api/items")
def items(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    subcategory: str | None = Query(default=None),
    tier: str | None = Query(default=None),
) -> dict:
    items = filter_items(load_items(), q=q, category=category, subcategory=subcategory, tier=tier)
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/foods")
def foods(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    subcategory: str | None = Query(default=None),
    tier: str | None = Query(default=None),
) -> dict:
    return items(q=q, category=category, subcategory=subcategory, tier=tier)


@app.get("/api/categories")
def categories() -> dict:
    counts: dict[str, int] = {}
    for item in load_items():
        counts[item.primary_category] = counts.get(item.primary_category, 0) + 1
    return {
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(
                counts.items(),
                key=lambda entry: (
                    CATEGORY_ORDER.index(entry[0]) if entry[0] in CATEGORY_ORDER else len(CATEGORY_ORDER),
                    entry[0].lower(),
                ),
            )
        ]
    }


@app.get("/api/subcategories")
def subcategories(category: str | None = Query(default=None)) -> dict:
    counts: dict[str, int] = {}
    for item in load_items():
        if category and item.primary_category.lower() != category.lower():
            continue
        for subcategory in item.categories:
            counts[subcategory] = counts.get(subcategory, 0) + 1
    return {
        "subcategories": [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda entry: entry[0].lower())
        ]
    }


def _tier_sort_key(entry: tuple[str, int]) -> tuple[int, int | str]:
    parts = entry[0].split()
    last = parts[-1] if parts else entry[0]
    return (0, int(last)) if last.isdigit() else (1, entry[0])


@app.get("/api/tiers")
def tiers() -> dict:
    counts: dict[str, int] = {}
    for item in load_items():
        if item.tier:
            counts[item.tier] = counts.get(item.tier, 0) + 1
    return {
        "tiers": [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=_tier_sort_key)
        ]
    }


@app.get("/api/loadouts")
def loadouts() -> dict:
    return {"loadouts": [loadout.model_dump() for loadout in load_loadouts()]}


@app.get("/api/loadouts/{loadout_id}")
def get_loadout(loadout_id: str) -> dict:
    loadout = next((entry for entry in load_loadouts() if entry.id == loadout_id), None)
    if not loadout:
        raise HTTPException(status_code=404, detail="Loadout not found")
    return loadout.model_dump()


@app.post("/api/loadouts")
def add_loadout(payload: LoadoutCreate) -> dict:
    return create_loadout(payload).model_dump()


@app.post("/api/loadouts/import")
def import_loadout_file(payload: LoadoutImport) -> dict:
    return import_loadout(payload).model_dump()


@app.delete("/api/loadouts/{loadout_id}")
def remove_loadout(loadout_id: str) -> dict:
    try:
        delete_loadout(loadout_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc
    return {"ok": True}


@app.put("/api/loadouts/{loadout_id}/items")
def put_loadout_item(loadout_id: str, payload: LoadoutItemInput) -> dict:
    try:
        return upsert_loadout_item(loadout_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.delete("/api/loadouts/{loadout_id}/items/{item_name}")
def remove_loadout_item(loadout_id: str, item_name: str) -> dict:
    try:
        return delete_loadout_item(loadout_id, item_name).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.put("/api/loadouts/{loadout_id}/collected")
def put_collected_item(loadout_id: str, payload: CollectedItemInput) -> dict:
    try:
        return set_collected_item(loadout_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.delete("/api/loadouts/{loadout_id}/collected")
def clear_collected(loadout_id: str) -> dict:
    try:
        return clear_collected_items(loadout_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.put("/api/loadouts/{loadout_id}/recipe-choice")
def put_recipe_choice(loadout_id: str, payload: RecipeChoiceInput) -> dict:
    try:
        return set_recipe_choice(loadout_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.put("/api/loadouts/{loadout_id}/ignored-materials")
def put_ignored_material(loadout_id: str, payload: IgnoredMaterialInput) -> dict:
    try:
        return set_ignored_material(loadout_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.put("/api/loadouts/{loadout_id}/farmed")
def put_farmed_item(loadout_id: str, payload: CollectedItemInput) -> dict:
    return put_collected_item(loadout_id, payload)


@app.delete("/api/loadouts/{loadout_id}/farmed")
def clear_farmed(loadout_id: str) -> dict:
    return clear_collected(loadout_id)


@app.get("/api/loadouts/{loadout_id}/resources")
def loadout_resources(loadout_id: str) -> dict:
    loadout = next((entry for entry in load_loadouts() if entry.id == loadout_id), None)
    if not loadout:
        raise HTTPException(status_code=404, detail="Loadout not found")
    return calculate_loadout(loadout, load_items())


@app.get("/api/buckets")
def buckets() -> dict:
    return {"buckets": loadouts()["loadouts"]}


@app.get("/api/buckets/{bucket_id}")
def get_bucket(bucket_id: str) -> dict:
    return get_loadout(bucket_id)


@app.post("/api/buckets")
def add_bucket(payload: LoadoutCreate) -> dict:
    return add_loadout(payload)


@app.delete("/api/buckets/{bucket_id}")
def remove_bucket(bucket_id: str) -> dict:
    return remove_loadout(bucket_id)


@app.put("/api/buckets/{bucket_id}/items")
def put_bucket_item(bucket_id: str, payload: LoadoutItemInput) -> dict:
    return put_loadout_item(bucket_id, payload)


@app.delete("/api/buckets/{bucket_id}/items/{food}")
def remove_bucket_item(bucket_id: str, food: str) -> dict:
    return remove_loadout_item(bucket_id, food)


@app.put("/api/buckets/{bucket_id}/collected")
def put_bucket_collected_item(bucket_id: str, payload: CollectedItemInput) -> dict:
    return put_collected_item(bucket_id, payload)


@app.delete("/api/buckets/{bucket_id}/collected")
def clear_bucket_collected(bucket_id: str) -> dict:
    return clear_collected(bucket_id)


@app.put("/api/buckets/{bucket_id}/farmed")
def put_bucket_farmed_item(bucket_id: str, payload: CollectedItemInput) -> dict:
    return put_collected_item(bucket_id, payload)


@app.delete("/api/buckets/{bucket_id}/farmed")
def clear_bucket_farmed(bucket_id: str) -> dict:
    return clear_collected(bucket_id)


@app.get("/api/buckets/{bucket_id}/resources")
def bucket_resources(bucket_id: str) -> dict:
    return loadout_resources(bucket_id)
