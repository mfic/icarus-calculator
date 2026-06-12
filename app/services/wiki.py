import asyncio
import re
from datetime import datetime, timezone
from html import unescape
from typing import Iterable

import httpx

from app.config import USER_AGENT, WIKI_API_URL
from app.models import FoodItem, Ingredient, Recipe
from app.services.storage import save_foods


ITEM_ICON_RE = re.compile(r"\{\{Item icon\|([^}|]+).*?\}\}")
LINK_RE = re.compile(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]")
TAG_RE = re.compile(r"<[^>]+>")


def extract_template(wikitext: str, name: str) -> str | None:
    start = wikitext.find("{{" + name)
    if start == -1:
        return None

    depth = 0
    index = start
    while index < len(wikitext) - 1:
        pair = wikitext[index : index + 2]
        if pair == "{{":
            depth += 1
            index += 2
            continue
        if pair == "}}":
            depth -= 1
            index += 2
            if depth == 0:
                return wikitext[start + len(name) + 2 : index - 2]
            continue
        index += 1
    return None


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = ITEM_ICON_RE.sub(r"\1", value)
    value = LINK_RE.sub(r"\1", value)
    value = TAG_RE.sub(" ", value)
    value = value.replace("{{PAGENAME}}", "").replace("&nbsp;", " ")
    value = unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [entry for entry in (clean_text(part) for part in value.split(",")) if entry]


def parse_quantity(value: str) -> float:
    value = value.strip()
    if not value:
        return 1
    try:
        return float(value)
    except ValueError:
        match = re.search(r"[-+]?\d*\.?\d+", value)
        return float(match.group(0)) if match else 1


def parse_ingredients(value: str | None) -> list[Ingredient]:
    ingredients: list[Ingredient] = []
    if not value:
        return ingredients
    for part in value.split(","):
        if not part.strip():
            continue
        name, _, quantity = part.partition(":")
        clean_name = clean_text(name)
        if clean_name:
            ingredients.append(Ingredient(name=clean_name, quantity=parse_quantity(quantity)))
    return ingredients


def item_icons(value: str) -> list[str]:
    return [cleaned for cleaned in (clean_text(match) for match in ITEM_ICON_RE.findall(value)) if cleaned]


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    parts: list[str] = []
    current: list[str] = []
    template_depth = 0
    link_depth = 0
    index = 0
    while index < len(body):
        pair = body[index : index + 2]
        if pair == "{{":
            template_depth += 1
            current.append(pair)
            index += 2
            continue
        if pair == "}}" and template_depth:
            template_depth -= 1
            current.append(pair)
            index += 2
            continue
        if pair == "[[":
            link_depth += 1
            current.append(pair)
            index += 2
            continue
        if pair == "]]" and link_depth:
            link_depth -= 1
            current.append(pair)
            index += 2
            continue
        if body[index] == "|" and template_depth == 0 and link_depth == 0:
            parts.append("".join(current))
            current = []
            index += 1
            continue
        current.append(body[index])
        index += 1
    parts.append("".join(current))

    for part in parts:
        key, separator, value = part.partition("=")
        if separator and re.match(r"^[A-Za-z0-9_]+$", key.strip()):
            fields[key.strip()] = value.strip()
    return fields


def table_cells(row: str) -> list[str]:
    cells: list[str] = []
    for raw_line in row.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or line.startswith("|+") or line.startswith("|-"):
            continue
        value = line[1:].strip()
        if "|" in value and not value.startswith("{{"):
            value = value.rsplit("|", 1)[-1].strip()
        cleaned = clean_text(value)
        if cleaned:
            cells.append(cleaned)
    return cells


def parse_wikitable_recipe(title: str, wikitext: str) -> Recipe | None:
    crafting_start = wikitext.find("==Crafting==")
    if crafting_start == -1:
        return None
    table_start = wikitext.find("{|", crafting_start)
    table_end = wikitext.find("|}", table_start)
    if table_start == -1 or table_end == -1:
        return None

    table = wikitext[table_start:table_end]
    caption = next((line for line in table.splitlines() if line.strip().startswith("|+")), "")
    benches = item_icons(caption)
    has_output_columns = "Output" in table
    inputs: list[Ingredient] = []
    outputs: list[Ingredient] = []

    for row in table.split("|-")[1:]:
        cells = table_cells(row)
        if has_output_columns and len(cells) >= 4:
            inputs.append(Ingredient(name=cells[1], quantity=parse_quantity(cells[0])))
            output_name = title if "PAGENAME" in cells[3] else cells[3]
            outputs.append(Ingredient(name=output_name, quantity=parse_quantity(cells[2])))
        elif len(cells) >= 2:
            inputs.append(Ingredient(name=cells[1], quantity=parse_quantity(cells[0])))

    if inputs and not outputs:
        outputs.append(Ingredient(name=title, quantity=1))
    recipe = Recipe(inputs=inputs, outputs=outputs, benches=benches)
    return recipe if recipe.inputs else None


def parse_recipe(wikitext: str) -> Recipe | None:
    body = extract_template(wikitext, "Recipe")
    if not body:
        return None
    fields = parse_fields(body)
    recipe = Recipe(
        inputs=parse_ingredients(fields.get("Inputs")),
        outputs=parse_ingredients(fields.get("Outputs")),
        benches=split_list(fields.get("Benches")),
    )
    return recipe if recipe.inputs or recipe.outputs or recipe.benches else None


def parse_consumables(wikitext: str) -> dict[str, str]:
    body = extract_template(wikitext, "Consumables")
    return parse_fields(body) if body else {}


def parse_buffs(attributes: str | None) -> list[str]:
    if not attributes:
        return []
    normalized = attributes.replace("<br />", "<br>").replace("<br/>", "<br>")
    return [entry for entry in (clean_text(part) for part in normalized.split("<br>")) if entry]


def slugify(title: str) -> str:
    return title.replace(" ", "_")


def food_from_wikitext(title: str, wikitext: str) -> FoodItem:
    consumables = parse_consumables(wikitext)
    recipe = parse_recipe(wikitext) or parse_wikitable_recipe(title, wikitext)
    bench = clean_text(consumables.get("bench"))
    benches = recipe.benches if recipe and recipe.benches else ([bench] if bench else [])
    description = clean_text(consumables.get("description"))
    return FoodItem(
        name=title,
        slug=slugify(title),
        description=description,
        duration=clean_text(consumables.get("duration")),
        spoil_time=clean_text(consumables.get("spoiltime") or consumables.get("spoil_time")),
        weight=clean_text(consumables.get("weight")),
        stack=clean_text(consumables.get("stack")),
        bench=bench,
        benches=benches,
        buffs=parse_buffs(consumables.get("attributes")),
        recipe=recipe,
        wiki_url=f"https://icarus.wiki.gg/wiki/{slugify(title)}",
    )


async def fetch_json(client: httpx.AsyncClient, params: dict[str, str | int]) -> dict:
    for attempt in range(5):
        response = await client.get(WIKI_API_URL, params=params)
        if response.status_code != 429:
            response.raise_for_status()
            return response.json()
        retry_after = response.headers.get("Retry-After")
        delay = float(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
        await asyncio.sleep(delay)
    response.raise_for_status()
    return response.json()


async def fetch_category_titles(client: httpx.AsyncClient, category: str) -> list[str]:
    titles: list[str] = []
    params: dict[str, str | int] = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": 500,
        "format": "json",
    }
    while True:
        payload = await fetch_json(client, params)
        titles.extend(
            page["title"]
            for page in payload.get("query", {}).get("categorymembers", [])
            if page.get("ns") == 0
        )
        cont = payload.get("continue")
        if not cont:
            return titles
        params.update(cont)


async def fetch_wikitext(client: httpx.AsyncClient, title: str) -> str | None:
    payload = await fetch_json(
        client,
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
        },
    )
    return payload.get("parse", {}).get("wikitext", {}).get("*")


def recipe_dependencies(items: Iterable[FoodItem]) -> set[str]:
    deps: set[str] = set()
    for item in items:
        if not item.recipe:
            continue
        for ingredient in item.recipe.inputs:
            deps.add(ingredient.name)
    return deps


async def scrape_foods(max_extra_pages: int = 300) -> list[FoodItem]:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        queue = await fetch_category_titles(client, "Category:Food")
        seen: set[str] = set()
        items: dict[str, FoodItem] = {}
        extra_pages = 0

        while queue:
            title = queue.pop(0)
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                wikitext = await fetch_wikitext(client, title)
            except httpx.HTTPError:
                continue
            if not wikitext:
                continue

            item = food_from_wikitext(title, wikitext)
            if item.buffs or item.recipe:
                items[item.name.lower()] = item

            for dep in recipe_dependencies([item]):
                dep_key = dep.lower()
                if dep_key not in seen and dep_key not in items and extra_pages < max_extra_pages:
                    queue.append(dep)
                    extra_pages += 1

            await asyncio.sleep(0.2)

    return sorted(items.values(), key=lambda item: item.name.lower())


def refresh_food_data() -> dict[str, str | int]:
    items = asyncio.run(scrape_foods())
    refreshed_at = datetime.now(timezone.utc).isoformat()
    save_foods(items, refreshed_at)
    return {"refreshed_at": refreshed_at, "count": len(items)}
