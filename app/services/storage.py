import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import DATA_DIR, ITEMS_PATH, LOADOUTS_PATH
from app.models import (
    CollectedItemInput,
    IgnoredMaterialInput,
    Item,
    Loadout,
    LoadoutCreate,
    LoadoutImport,
    LoadoutItem,
    LoadoutItemInput,
    RecipeChoiceInput,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    ensure_data_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


_items_cache: list[Item] | None = None
_items_cache_mtime: float | None = None


def load_items() -> list[Item]:
    global _items_cache, _items_cache_mtime
    try:
        mtime = ITEMS_PATH.stat().st_mtime
    except FileNotFoundError:
        mtime = None
    if _items_cache is None or mtime != _items_cache_mtime:
        payload = read_json(ITEMS_PATH, {"items": []})
        _items_cache = [Item.model_validate(item) for item in payload.get("items", [])]
        _items_cache_mtime = mtime
    return _items_cache


def save_items(items: list[Item], refreshed_at: str) -> None:
    global _items_cache, _items_cache_mtime
    write_json(
        ITEMS_PATH,
        {
            "refreshed_at": refreshed_at,
            "source": "https://icarus.wiki.gg",
            "items": [item.model_dump() for item in items],
        },
    )
    _items_cache = items
    _items_cache_mtime = ITEMS_PATH.stat().st_mtime


def item_metadata() -> dict[str, Any]:
    payload = read_json(ITEMS_PATH, {"items": []})
    return {
        "refreshed_at": payload.get("refreshed_at"),
        "source": payload.get("source", "https://icarus.wiki.gg"),
        "count": len(payload.get("items", [])),
    }


def load_loadouts() -> list[Loadout]:
    payload = read_json(LOADOUTS_PATH, {"loadouts": []})
    raw_loadouts = payload.get("loadouts", payload.get("buckets", []))
    return [Loadout.model_validate(loadout) for loadout in raw_loadouts]


def save_loadouts(loadouts: list[Loadout]) -> None:
    write_json(LOADOUTS_PATH, {"loadouts": [loadout.model_dump() for loadout in loadouts]})


_loadouts_lock = threading.Lock()


def create_loadout(data: LoadoutCreate) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        now = utc_now()
        loadout = Loadout(id=str(uuid.uuid4()), name=data.name.strip(), created_at=now, updated_at=now)
        loadouts.append(loadout)
        save_loadouts(loadouts)
        return loadout


def import_loadout(data: LoadoutImport) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        now = utc_now()
        loadout = Loadout(
            id=str(uuid.uuid4()),
            name=data.name.strip(),
            items=data.items,
            collected=data.collected,
            recipe_choices=data.recipe_choices,
            ignored_materials=data.ignored_materials,
            created_at=now,
            updated_at=now,
        )
        loadouts.append(loadout)
        save_loadouts(loadouts)
        return loadout


def upsert_loadout_item(loadout_id: str, item: LoadoutItemInput) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                existing = next((entry for entry in loadout.items if entry.item == item.item), None)
                if existing:
                    existing.quantity = item.quantity
                else:
                    loadout.items.append(LoadoutItem(item=item.item, quantity=item.quantity))
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def delete_loadout_item(loadout_id: str, item_name: str) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                loadout.items = [item for item in loadout.items if item.item != item_name]
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def set_collected_item(loadout_id: str, collected_item: CollectedItemInput) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                if collected_item.quantity > 0:
                    loadout.collected[collected_item.item] = collected_item.quantity
                else:
                    loadout.collected.pop(collected_item.item, None)
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def set_recipe_choice(loadout_id: str, choice: RecipeChoiceInput) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                if choice.recipe_id:
                    loadout.recipe_choices[choice.item] = choice.recipe_id
                else:
                    loadout.recipe_choices.pop(choice.item, None)
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def set_ignored_material(loadout_id: str, payload: IgnoredMaterialInput) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                if payload.ignored:
                    if payload.item.lower() not in {name.lower() for name in loadout.ignored_materials}:
                        loadout.ignored_materials.append(payload.item)
                else:
                    loadout.ignored_materials = [
                        name for name in loadout.ignored_materials if name.lower() != payload.item.lower()
                    ]
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def clear_collected_items(loadout_id: str) -> Loadout:
    with _loadouts_lock:
        loadouts = load_loadouts()
        for loadout in loadouts:
            if loadout.id == loadout_id:
                loadout.collected = {}
                loadout.updated_at = utc_now()
                save_loadouts(loadouts)
                return loadout
    raise KeyError(loadout_id)


def delete_loadout(loadout_id: str) -> None:
    with _loadouts_lock:
        loadouts = load_loadouts()
        next_loadouts = [loadout for loadout in loadouts if loadout.id != loadout_id]
        if len(next_loadouts) == len(loadouts):
            raise KeyError(loadout_id)
        save_loadouts(next_loadouts)


load_foods = load_items
save_foods = save_items
food_metadata = item_metadata
load_buckets = load_loadouts
save_buckets = save_loadouts
create_bucket = create_loadout
upsert_bucket_item = upsert_loadout_item
delete_bucket_item = delete_loadout_item
delete_bucket = delete_loadout
set_farmed_item = set_collected_item
clear_farmed_items = clear_collected_items
