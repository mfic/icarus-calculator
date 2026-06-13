# ICARUS Resource Calculator

A small hosted PoC for ICARUS item loadouts. It fetches item data from the ICARUS wiki.gg API once a day, stores the cached item data in JSON, and keeps loadouts persistent in `data/loadouts.json`.

Items include wiki categories, tier metadata, and effects/stats when the wiki exposes them.
Some items (e.g. Epoxy) have multiple alternative recipes scraped from the wiki; each loadout
can pick which alternative to use via a recipe selector in the Crafting Steps panel, and the
choice is saved with the loadout.
Each loadout can also track collected material quantities, so the material summary shows what is still remaining, and loadout item quantities can be edited inline.
Materials can be marked as ignored (e.g. ones you already have stockpiled), removing them from the Bare Materials totals and Crafting Steps for that loadout.
Loadouts have UUIDs for shareable links, and can be exported/imported as JSON files.
Each browser gets a private [account code](#accounts--sharing); loadouts are only visible to their owner unless explicitly shared with another account code.
The main category filter uses normalized in-game categories; wiki categories remain available as subcategories, and items can additionally be filtered by tier. A Reset button clears all active filters and the search box.
The Bare Materials and Crafting Steps lists show small color-coded dots indicating which loadout item(s) each material or step comes from.
A [Gather tab](#gather-view) shows a large-print, touch-friendly Bare Materials checklist for the active loadout in place, and the same view is also available as a standalone page (`/gather`) for a second monitor or tablet while out gathering.

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
just start-traefik # start with docker-compose.traefik.yml override
just stop          # stop Docker compose
just stop-traefik  # stop the Traefik override stack
just restart       # stop then start Docker compose
just restart-traefik # restart with Traefik override
just logs          # follow Docker compose logs
just logs-traefik  # follow logs with Traefik override
just dev-traefik   # run dev compose with Traefik override
just test          # run tests
just update        # refresh wiki data cache (Docker one-shot)
just local-update  # refresh wiki data cache (local Python env)
just refresh       # refresh wiki data cache (running Docker container)
just status        # print cached item metadata (running Docker container)
just local-status  # print cached item metadata (local Python env)
just api           # call /api/meta on the local dev server
just reset-loadouts # reset data/loadouts.json to an empty list
just docker-build  # build the icarus-calculator image directly
just clean         # remove Python/test cache files
```

## Docker

```bash
docker compose up --build
```

This starts two services:

- `icarus-calculator`: the web app (port 8001)
- `icarus-refresh`: a sidecar that refreshes the wiki data cache once on startup and
  then every 24 hours

The `data/` folder is mounted as a volume in both services, so the wiki cache and
loadouts survive restarts and the web app picks up the refreshed `items.json`
automatically (no restart needed).

### Optional Traefik Override

Traefik labels are optional and live in a local override file that is ignored by
git:

```bash
cp docker-compose.traefik.example.yml docker-compose.traefik.yml
# Windows PowerShell:
# Copy-Item docker-compose.traefik.example.yml docker-compose.traefik.yml
```

Edit `docker-compose.traefik.yml` for your hostname, certificate resolver, and
external Traefik network, then run:

```bash
just start-traefik
```

For development behind Traefik, use `just dev-traefik`.

## Data Refresh

The wiki data cache is refreshed:

- automatically by the `icarus-refresh` compose service (once on startup, then every
  24 hours)
- manually via `just update` (Docker one-shot), `just refresh` (running Docker
  container), or `just local-update` (local Python env). There is no
  internet-facing refresh endpoint or button, so the re-scrape can only be
  triggered by the operator.

## Gather View

`/gather` is a standalone, full-page view of a loadout's Bare Materials list, meant
to be opened in its own browser tab/window (e.g. on a second monitor or a tablet next
to the game). It shares the loadout's collected-material tracking with the main
calculator, refreshes itself periodically to pick up changes made elsewhere, and has
a "Hide completed" toggle plus large touch-friendly +/- steppers for updating
collected amounts.

## Accounts & Sharing

There is no registration or login. On first visit, the browser generates a random
account code (UUID), stores it in `localStorage`, and sends it as the
`X-Account-Id` header on every API request. Loadouts are private to the account
that created them.

- The account code is shown in the UI with a "Copy" button. Pasting it into "Use
  different code" on another browser/device gives that browser access to the same
  account's loadouts — this is the only way to move or back up an account.
- A loadout's owner can share it with another account code via the "Share" button.
  Shared accounts can view and edit the loadout's items, collected amounts, recipe
  choices, and ignored materials, but only the owner can manage sharing or delete
  the loadout.
- The account code *is* the credential — anyone with it has full access to that
  account's loadouts, so treat it like a password.

## API

### Items

- `GET /api/meta`
- `GET /api/items`
- `GET /api/items?q=stamina&category=Consumables&subcategory=Food&tier=Tier%202`
- `GET /api/categories`
- `GET /api/subcategories`
- `GET /api/tiers`
- `GET /api/foods` compatibility alias for items

### Loadouts

All loadout endpoints require an `X-Account-Id` header (see
[Accounts & Sharing](#accounts--sharing)); a missing header returns `422`, and
a loadout the account can't access returns `404`.

- `GET /api/loadouts`
- `POST /api/loadouts`
- `POST /api/loadouts/import`
- `GET /api/loadouts/{loadout_id}`
- `DELETE /api/loadouts/{loadout_id}` owner only (`403` otherwise)
- `PUT /api/loadouts/{loadout_id}/items`
- `DELETE /api/loadouts/{loadout_id}/items/{item_name}`
- `PUT /api/loadouts/{loadout_id}/collected`
- `DELETE /api/loadouts/{loadout_id}/collected`
- `PUT /api/loadouts/{loadout_id}/recipe-choice`
- `PUT /api/loadouts/{loadout_id}/ignored-materials`
- `PUT /api/loadouts/{loadout_id}/share` owner only (`403` otherwise)
- `GET /api/loadouts/{loadout_id}/resources`
- `GET /api/buckets` compatibility alias for loadouts; `farmed` is a
  compatibility alias for `collected`

## Persistence

Server state is JSON-file based:

- `data/items.json`: current wiki cache
- `data/loadouts.json`: all loadouts, each tagged with an `owner_id` account code and a `shared_with` list of account codes
- `data/item_overrides.json`: manual corrections (tier, primary category, extra categories), keyed by item name and merged into the wiki-scraped item data on each refresh

The browser also mirrors its account code, the selected loadout, and the latest loadout snapshot in `localStorage` as a client-side convenience.

## Community & License

This project uses the [GNU Affero General Public License v3.0](LICENSE). Please read the
[Code of Conduct](CODE_OF_CONDUCT.md), [Contributing Guide](CONTRIBUTING.md),
and [Security Policy](SECURITY.md) before opening issues or pull requests.
