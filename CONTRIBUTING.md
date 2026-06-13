# Contributing

Thanks for helping improve ICARUS Resource Calculator.

## Development

Use the `justfile` for common tasks:

```bash
just install
just test
just dev
```

For Docker-based development:

```bash
just dev
```

For a Traefik-backed local or hosted setup:

```bash
cp docker-compose.traefik.example.yml docker-compose.traefik.yml
# Windows PowerShell:
# Copy-Item docker-compose.traefik.example.yml docker-compose.traefik.yml
just dev-traefik
```

## Pull Requests

- Keep changes focused and explain the user-facing impact.
- Add or update tests when behavior changes.
- Do not commit local deployment overrides, secrets, generated caches, or personal loadout data.
- Prefer existing project patterns over new abstractions.
- Run `just test` before opening a pull request.

## Data And Scraping

The wiki cache is stored in `data/items.json`. Scraper fixes should update parser code and tests first. Refreshing the cache is useful when parser behavior changes:

```bash
just update
```

Manual corrections belong in `data/item_overrides.json`.

## Conduct

Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
