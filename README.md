# ICARUS Resource Calculator

A small hosted PoC for ICARUS item and food loadouts. It fetches item data from the ICARUS wiki.gg API once a day, stores the cached item data in JSON, and keeps team loadout buckets persistent in `data/buckets.json`.

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

## Just Commands

```bash
just install       # install runtime and test dependencies
just dev           # run Docker Compose dev server with reload
just local-dev     # run the local Python FastAPI server with reload
just start         # build and start Docker compose
just stop          # stop Docker compose
just update        # refresh wiki data cache
just test          # run tests
just clean         # remove Python/test cache files
```

## Docker

```bash
docker compose up --build
```

The `data/` folder is mounted as a volume so wiki cache and buckets survive restarts.

## Data Refresh

The app refreshes wiki data:

- on startup when the cache is empty or older than 24 hours
- every 24 hours while the server is running
- manually via the **Refresh Wiki Data** button or `POST /api/refresh`

## API

- `GET /api/items`
- `GET /api/items?q=stamina&category=Food`
- `GET /api/categories`
- `GET /api/foods` compatibility alias for items
- `GET /api/buckets`
- `POST /api/buckets`
- `PUT /api/buckets/{bucket_id}/items`
- `GET /api/buckets/{bucket_id}/resources`

## Persistence

Server state is JSON-file based:

- `data/foods.json`: current wiki cache
- `data/buckets.json`: shared bucket/loadout data

The browser also mirrors the selected bucket and latest bucket snapshot in `localStorage` as a client-side convenience.
