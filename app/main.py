from contextlib import asynccontextmanager
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, FOODS_PATH
from app.models import BucketCreate, BucketItemInput, FoodItem
from app.services.calculator import calculate_bucket
from app.services.storage import (
    create_bucket,
    delete_bucket,
    delete_bucket_item,
    food_metadata,
    load_buckets,
    load_foods,
    upsert_bucket_item,
)
from app.services.wiki import refresh_food_data


scheduler = BackgroundScheduler(timezone="UTC")


def refresh_if_needed() -> None:
    metadata = food_metadata()
    refreshed_at = metadata.get("refreshed_at")
    if not FOODS_PATH.exists() or not refreshed_at or metadata.get("count", 0) == 0:
        try:
            refresh_food_data()
        except Exception:
            pass
        return
    then = datetime.fromisoformat(str(refreshed_at).replace("Z", "+00:00"))
    age = datetime.now(timezone.utc) - then
    if age.total_seconds() >= 24 * 60 * 60:
        try:
            refresh_food_data()
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    refresh_if_needed()
    scheduler.add_job(refresh_food_data, "interval", days=1, id="daily-wiki-refresh", replace_existing=True)
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
    return food_metadata()


@app.post("/api/refresh")
def refresh() -> dict:
    return refresh_food_data()


def filter_items(items: list[FoodItem], q: str | None = None, category: str | None = None) -> list[FoodItem]:
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
    items = filter_items(load_foods(), q=q, category=category)
    return {"items": [item.model_dump() for item in items]}


@app.get("/api/foods")
def foods(q: str | None = Query(default=None), category: str | None = Query(default=None)) -> dict:
    return items(q=q, category=category)


@app.get("/api/categories")
def categories() -> dict:
    counts: dict[str, int] = {}
    for item in load_foods():
        for category in item.categories:
            counts[category] = counts.get(category, 0) + 1
    return {
        "categories": [
            {"name": name, "count": count}
            for name, count in sorted(counts.items(), key=lambda entry: entry[0].lower())
        ]
    }


@app.get("/api/buckets")
def buckets() -> dict:
    return {"buckets": [bucket.model_dump() for bucket in load_buckets()]}


@app.post("/api/buckets")
def add_bucket(payload: BucketCreate) -> dict:
    return create_bucket(payload).model_dump()


@app.delete("/api/buckets/{bucket_id}")
def remove_bucket(bucket_id: str) -> dict:
    try:
        delete_bucket(bucket_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Bucket not found") from exc
    return {"ok": True}


@app.put("/api/buckets/{bucket_id}/items")
def put_bucket_item(bucket_id: str, payload: BucketItemInput) -> dict:
    try:
        return upsert_bucket_item(bucket_id, payload).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Bucket not found") from exc


@app.delete("/api/buckets/{bucket_id}/items/{food}")
def remove_bucket_item(bucket_id: str, food: str) -> dict:
    try:
        return delete_bucket_item(bucket_id, food).model_dump()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Bucket not found") from exc


@app.get("/api/buckets/{bucket_id}/resources")
def bucket_resources(bucket_id: str) -> dict:
    bucket = next((entry for entry in load_buckets() if entry.id == bucket_id), None)
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")
    return calculate_bucket(bucket, load_foods())
