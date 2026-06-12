import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import BUCKETS_PATH, DATA_DIR, FOODS_PATH
from app.models import Bucket, BucketCreate, BucketItem, BucketItemInput, FoodItem


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


def load_foods() -> list[FoodItem]:
    payload = read_json(FOODS_PATH, {"items": []})
    return [FoodItem.model_validate(item) for item in payload.get("items", [])]


def save_foods(items: list[FoodItem], refreshed_at: str) -> None:
    write_json(
        FOODS_PATH,
        {
            "refreshed_at": refreshed_at,
            "source": "https://icarus.wiki.gg",
            "items": [item.model_dump() for item in items],
        },
    )


def food_metadata() -> dict[str, Any]:
    payload = read_json(FOODS_PATH, {"items": []})
    return {
        "refreshed_at": payload.get("refreshed_at"),
        "source": payload.get("source", "https://icarus.wiki.gg"),
        "count": len(payload.get("items", [])),
    }


def load_buckets() -> list[Bucket]:
    payload = read_json(BUCKETS_PATH, {"buckets": []})
    return [Bucket.model_validate(bucket) for bucket in payload.get("buckets", [])]


def save_buckets(buckets: list[Bucket]) -> None:
    write_json(BUCKETS_PATH, {"buckets": [bucket.model_dump() for bucket in buckets]})


def create_bucket(data: BucketCreate) -> Bucket:
    buckets = load_buckets()
    now = utc_now()
    bucket = Bucket(id=str(uuid.uuid4()), name=data.name.strip(), created_at=now, updated_at=now)
    buckets.append(bucket)
    save_buckets(buckets)
    return bucket


def upsert_bucket_item(bucket_id: str, item: BucketItemInput) -> Bucket:
    buckets = load_buckets()
    for bucket in buckets:
        if bucket.id == bucket_id:
            existing = next((entry for entry in bucket.items if entry.food == item.food), None)
            if existing:
                existing.quantity = item.quantity
            else:
                bucket.items.append(BucketItem(food=item.food, quantity=item.quantity))
            bucket.updated_at = utc_now()
            save_buckets(buckets)
            return bucket
    raise KeyError(bucket_id)


def delete_bucket_item(bucket_id: str, food: str) -> Bucket:
    buckets = load_buckets()
    for bucket in buckets:
        if bucket.id == bucket_id:
            bucket.items = [item for item in bucket.items if item.food != food]
            bucket.updated_at = utc_now()
            save_buckets(buckets)
            return bucket
    raise KeyError(bucket_id)


def delete_bucket(bucket_id: str) -> None:
    buckets = load_buckets()
    next_buckets = [bucket for bucket in buckets if bucket.id != bucket_id]
    if len(next_buckets) == len(buckets):
        raise KeyError(bucket_id)
    save_buckets(next_buckets)
