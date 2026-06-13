import logging
import time

from app.services.wiki import refresh_item_data

REFRESH_INTERVAL_SECONDS = 24 * 60 * 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("refresh-loop")


def main() -> None:
    while True:
        try:
            result = refresh_item_data()
            logger.info("Refreshed wiki data: %s", result)
        except Exception:
            logger.exception("Wiki data refresh failed")
        time.sleep(REFRESH_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
