import logging
import time
from datetime import datetime, timezone

from app.services.storage import item_metadata
from app.services.wiki import refresh_item_data

REFRESH_INTERVAL_SECONDS = 24 * 60 * 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("refresh-loop")


def seconds_since_last_refresh() -> float | None:
    refreshed_at = item_metadata().get("refreshed_at")
    if not refreshed_at:
        return None
    try:
        last_refresh = datetime.fromisoformat(refreshed_at)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - last_refresh).total_seconds()


def main() -> None:
    age = seconds_since_last_refresh()
    if age is not None and age < REFRESH_INTERVAL_SECONDS:
        wait = REFRESH_INTERVAL_SECONDS - age
        logger.info("Cached wiki data is %.0fs old, skipping initial refresh; next refresh in %.0fs", age, wait)
        time.sleep(wait)

    while True:
        try:
            result = refresh_item_data()
            logger.info("Refreshed wiki data: %s", result)
        except Exception:
            logger.exception("Wiki data refresh failed")
        time.sleep(REFRESH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
