set shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

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

stop:
    docker compose down

restart: stop start

logs:
    docker compose logs -f

test:
    python -m pytest

update:
    python -c "from app.services.wiki import refresh_food_data; print(refresh_food_data())"

status:
    python -c "from app.services.storage import food_metadata; print(food_metadata())"

api:
    Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/meta' | ConvertTo-Json

clean:
    $root = (Resolve-Path '.').Path; \
    $targets = @('.pytest_cache') + (Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' | ForEach-Object { $_.FullName }); \
    foreach ($target in $targets) { \
      $resolved = Resolve-Path -LiteralPath $target -ErrorAction SilentlyContinue; \
      if ($resolved -and $resolved.Path.StartsWith($root)) { Remove-Item -LiteralPath $resolved.Path -Recurse -Force } \
    }

reset-buckets:
    Set-Content -Path data/buckets.json -Value '{ "buckets": [] }'

docker-build:
    docker build -t icarus-calculator .
