from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, ITEMS_PATH
from app.models import FarmedItemInput, Item, LoadoutCreate, LoadoutItemInput
from app.services.calculator import calculate_loadout
from app.services.storage import (
    create_loadout,
    delete_loadout,
    delete_loadout_item,
    clear_farmed_items,
    item_metadata,
    load_items,
    load_loadouts,
    set_farmed_item,
    upsert_loadout_item,
)
from app.services.wiki import refresh_item_data


scheduler = BackgroundScheduler(timezone="UTC")


def refresh_if_needed() -> None:
    metadata = item_metadata()
    refreshed_at = metadata.get("refreshed_at")
    if not ITEMS_PATH.exists() or not refreshed_at or metadata.get("count", 0) == 0:
        try:
            refresh_item_data()
        except Exception:
            pass
        return
    then = datetime.fromisoformat(str(refreshed_at).replace("Z", "+00:00"))
    age = datetime.now(timezone.utc) - then
    if age.total_seconds() >= 24 * 60 * 60:
        try:
            refresh_item_data()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    refresh_if_needed()
    scheduler.add_job(refresh_item_data, "interval", days=1, id="daily-wiki-refresh", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="ICARUS Resource Calculator", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/meta")
def meta() -> dict:
    return item_metadata()


@app.post("/api/refresh")
def refresh() -> dict:
    return refresh_item_data()


def filter_items(items: list[Item], q: str | None = None, category: str | None = None) -> list[Item]:
    if category:
        category_needle = category.lower()
        items = [
            item
            for item in items
            if any(category_needle == item_category.lower() for item_category in item.categories)
        ]
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
            or (
                item.recipe
                and any(needle in ingredient.name.lower() for ingredient in item.recipe.inputs)
            )
            or any(needle in category.lower() for category in item.categories)
        ]
    return items


@app.get("/api/items")
def items(q: str | None = Query(default=None), category: str | None = Query(default=None)) -> dict:
    items = filter_items(load_items(), q=q, category=category)
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/foods")
def foods(q: str | None = Query(default=None), category: str | None = Query(default=None)) -> dict:
    return items(q=q, category=category)


@app.get("/api/categories")
def categories() -> dict:
    counts: dict[str, int] = {}
    for item in load_items():
        for category in item.categories:
            counts[category] = counts.get(category, 0) + 1
    return {
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda entry: entry[0].lower())
        ]
    }


@app.get("/api/loadouts")
def loadouts() -> dict:
    return {"loadouts": [loadout.model_dump() for loadout in load_loadouts()]}


@app.post("/api/loadouts")
def add_loadout(payload: LoadoutCreate) -> dict:
    return create_loadout(payload).model_dump()


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


@app.put("/api/loadouts/{loadout_id}/farmed")
def put_farmed_item(loadout_id: str, payload: FarmedItemInput) -> dict:
    try:
        return set_farmed_item(loadout_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.delete("/api/loadouts/{loadout_id}/farmed")
def clear_farmed(loadout_id: str) -> dict:
    try:
        return clear_farmed_items(loadout_id).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Loadout not found") from exc


@app.get("/api/loadouts/{loadout_id}/resources")
def loadout_resources(loadout_id: str) -> dict:
    loadout = next((entry for entry in load_loadouts() if entry.id == loadout_id), None)
    if not loadout:
        raise HTTPException(status_code=404, detail="Loadout not found")
    return calculate_loadout(loadout, load_items())


@app.get("/api/buckets")
def buckets() -> dict:
    return {"buckets": loadouts()["loadouts"]}


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


@app.put("/api/buckets/{bucket_id}/farmed")
def put_bucket_farmed_item(bucket_id: str, payload: FarmedItemInput) -> dict:
    return put_farmed_item(bucket_id, payload)


@app.delete("/api/buckets/{bucket_id}/farmed")
def clear_bucket_farmed(bucket_id: str) -> dict:
    return clear_farmed(bucket_id)


@app.get("/api/buckets/{bucket_id}/resources")
def bucket_resources(bucket_id: str) -> dict:
    return loadout_resources(bucket_id)
