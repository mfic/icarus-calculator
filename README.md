# ICARUS Resource Calculator

A small hosted PoC for ICARUS item loadouts. It fetches item data from the ICARUS wiki.gg API once a day, stores the cached item data in JSON, and keeps team loadouts persistent in `data/loadouts.json`.

Items include wiki categories, tier metadata, and effects/stats when the wiki exposes them.
Some items (e.g. Epoxy) have multiple alternative recipes scraped from the wiki; each loadout
can pick which alternative to use via a recipe selector in the Crafting Steps panel, and the
choice is saved with the loadout.
Each loadout can also track collected material quantities, so the material summary shows what is still remaining, and loadout item quantities can be edited inline.
Loadouts have UUIDs for shareable links, and can be exported/imported as JSON files without user accounts.
The main category filter uses normalized in-game categories; wiki categories remain available as subcategories, and items can additionally be filtered by tier. A Reset button clears all active filters and the search box.
The Bare Materials and Crafting Steps lists show small color-coded dots indicating which loadout item(s) each material or step comes from.

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

### Items

- `GET /api/items`
- `GET /api/items?q=stamina&category=Consumables&subcategory=Food&tier=Tier%202`
- `GET /api/categories`
- `GET /api/subcategories`
- `GET /api/tiers`
- `GET /api/foods` compatibility alias for items

### Loadouts

- `GET /api/loadouts`
- `POST /api/loadouts`
- `POST /api/loadouts/import`
- `GET /api/loadouts/{loadout_id}`
- `DELETE /api/loadouts/{loadout_id}`
- `PUT /api/loadouts/{loadout_id}/items`
- `DELETE /api/loadouts/{loadout_id}/items/{item_name}`
- `PUT /api/loadouts/{loadout_id}/collected`
- `DELETE /api/loadouts/{loadout_id}/collected`
- `PUT /api/loadouts/{loadout_id}/recipe-choice`
- `GET /api/loadouts/{loadout_id}/resources`
- `GET /api/buckets` compatibility alias for loadouts

## Persistence

Server state is JSON-file based:

- `data/items.json`: current wiki cache
- `data/loadouts.json`: shared loadout data
- `data/item_overrides.json`: manual corrections (tier, primary category, extra categories), keyed by item name and merged into the wiki-scraped item data on each refresh

The browser also mirrors the selected loadout and latest loadout snapshot in `localStorage` as a client-side convenience.
