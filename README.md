# ICARUS Resource Calculator

A small hosted PoC for ICARUS item loadouts. It fetches item data from the ICARUS wiki.gg API once a day, stores the cached item data in JSON, and keeps team loadouts persistent in `data/loadouts.json`.

Items include wiki categories, tier metadata, and effects/stats when the wiki exposes them.
Each loadout can also track collected material quantities, so the material summary shows what is still remaining.

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

The `data/` folder is mounted as a volume so wiki cache and loadouts survive restarts.

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
- `GET /api/loadouts`
- `POST /api/loadouts`
- `PUT /api/loadouts/{loadout_id}/items`
- `GET /api/loadouts/{loadout_id}/resources`
- `GET /api/buckets` compatibility alias for loadouts

## Persistence

Server state is JSON-file based:

- `data/items.json`: current wiki cache
- `data/loadouts.json`: shared loadout data

The browser also mirrors the selected loadout and latest loadout snapshot in `localStorage` as a client-side convenience.
