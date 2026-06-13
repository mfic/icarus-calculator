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

start-traefik:
    python -c "from pathlib import Path; raise SystemExit(0 if Path('docker-compose.traefik.yml').exists() else 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.')"
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml up -d --build

stop:
    docker compose down

stop-traefik:
    python -c "from pathlib import Path; raise SystemExit(0 if Path('docker-compose.traefik.yml').exists() else 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.')"
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml down

restart: stop start

restart-traefik: stop-traefik start-traefik

logs:
    docker compose logs -f

logs-traefik:
    python -c "from pathlib import Path; raise SystemExit(0 if Path('docker-compose.traefik.yml').exists() else 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.')"
    docker compose -f docker-compose.yml -f docker-compose.traefik.yml logs -f

dev-traefik:
    python -c "from pathlib import Path; raise SystemExit(0 if Path('docker-compose.traefik.yml').exists() else 'Missing docker-compose.traefik.yml. Copy docker-compose.traefik.example.yml and edit it first.')"
    docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.traefik.yml up --build

test:
    python -m pytest

update:
    python -c "from app.services.wiki import refresh_item_data; print(refresh_item_data())"

refresh:
    docker compose exec icarus-calculator python -c "from app.services.wiki import refresh_item_data; print(refresh_item_data())"

status:
    python -c "from app.services.storage import item_metadata; print(item_metadata())"

api:
    python -c "import json, urllib.request; print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/meta')), indent=2))"

clean:
    python -c "from pathlib import Path; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in [Path('.pytest_cache'), *Path('.').rglob('__pycache__')]]"

reset-loadouts:
    python -c "from pathlib import Path; import json; Path('data/loadouts.json').write_text(json.dumps({'loadouts': []}, indent=2) + '\n', encoding='utf-8')"

reset-buckets:
    just reset-loadouts

docker-build:
    docker build -t icarus-calculator .
