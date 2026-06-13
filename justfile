set shell := ["sh", "-cu"]
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    just --list

install:
    python -m pip install -r requirements-dev.txt

dev:
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

local-dev:
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

start:
    docker compose up -d --build

start-traefik: _check-traefik
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build

stop:
    docker compose down

stop-traefik: _check-traefik
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml down

restart: stop start

restart-traefik: stop-traefik start-traefik

logs:
    docker compose logs -f

logs-traefik: _check-traefik
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml logs -f

dev-traefik: _check-traefik
    docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.traefik.yml up --build

test:
    python -m pytest

update:
    docker compose run --rm icarus-calculator python -c "from app.services.wiki import refresh_item_data; print(refresh_item_data())"

local-update:
    python -c "from app.services.wiki import refresh_item_data; print(refresh_item_data())"

refresh:
    docker compose exec icarus-calculator python -c "from app.services.wiki import refresh_item_data; print(refresh_item_data())"

status:
    docker compose exec icarus-calculator python -c "from app.services.storage import item_metadata; print(item_metadata())"

local-status:
    python -c "from app.services.storage import item_metadata; print(item_metadata())"

[unix]
api:
    curl -fsS http://127.0.0.1:8000/api/meta

[unix]
clean:
    rm -rf .pytest_cache
    find . -type d -name __pycache__ -prune -exec rm -rf {} +

[unix]
reset-loadouts:
    printf '{\n  "loadouts": []\n}\n' > data/loadouts.json

reset-buckets:
    just reset-loadouts

docker-build:
    docker build -t icarus-calculator .

[unix]
_check-traefik:
    test -f docker-compose.traefik.yml || { echo 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.' >&2; exit 1; }

[windows]
_check-traefik:
    if (!(Test-Path docker-compose.traefik.yml)) { throw 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.' }

[windows]
api:
    Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/meta' | ConvertTo-Json

[windows]
clean:
    $root = (Resolve-Path '.').Path; \
    $targets = @('.pytest_cache') + (Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' | ForEach-Object { $_.FullName }); \
    foreach ($target in $targets) { \
      $resolved = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue; \
      if ($resolved -and $resolved.Path.StartsWith($root)) { Remove-Item -LiteralPath $resolved.Path -Recurse -Force } \
    }

[windows]
reset-loadouts:
    Set-Content -Path data/loadouts.json -Value '{ "loadouts": [] }'
