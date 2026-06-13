import asyncio
import re
from datetime import datetime, timezone
from html import unescape
from typing import Iterable

import httpx

from app.config import DATA_DIR, USER_AGENT, WIKI_API_URL
from app.models import Ingredient, Item, Recipe
from app.services.storage import save_items


ITEM_CATEGORIES = [
    "Category:Items",
    "Category:Resources",
    "Category:Crafted Resources",
    "Category:Food",
    "Category:Consumables",
    "Category:Tools",
    "Category:Deployables",
    "Category:Weapons",
    "Category:Ammo",
    "Category:Arrows",
    "Category:Bolts",
    "Category:Bows",
    "Category:Crossbows",
    "Category:Firearms",
    "Category:Dirt Buildings",
]

ITEM_INFO_TEMPLATES = [
    "ItemData",
    "Ammo",
    "Buildings",
    "Consumables",
    "Deployables",
    "Weapons",
    "Tools",
    "Armor",
]

EFFECT_FIELDS = [
    "attributes",
    "projdamageMin",
    "projdamageMax",
    "elementdamageMin",
    "elementdamageMax",
    "projectileBreakChance",
    "durability",
    "flammable",
]


ITEM_ICON_RE = re.compile(r"\{\{Item icon\|([^}|]+).*?\}\}")
LINK_RE = re.compile(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]")
TAG_RE = re.compile(r"<[^>]+>")
CATEGORY_RE = re.compile(r"\[\[Category:([^|\]]+)")
TIER_RE = re.compile(r"\bTier\s+\d+\b", re.IGNORECASE)


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


def clean_category(category: str) -> str:
    return category.removeprefix("Category:").strip()


def parse_categories(wikitext: str, extra: Iterable[str] = ()) -> list[str]:
    categories = {clean_category(category) for category in extra if category}
    categories.update(match.strip() for match in CATEGORY_RE.findall(wikitext))
    return sorted(category for category in categories if category)


def parse_tier(categories: Iterable[str], *values: str | None) -> str | None:
    for category in categories:
        match = TIER_RE.search(category)
        if match:
            return match.group(0).title()
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        match = TIER_RE.search(cleaned)
        if match:
            return match.group(0).title()
    return None


def load_item_overrides() -> dict[str, dict]:
    path = DATA_DIR / "item_overrides.json"
    if not path.exists():
        return {}
    import json

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return {name.lower(): override for name, override in payload.get("items", {}).items()}


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
        if "||" in value:
            for part in value.split("||"):
                cleaned = clean_text(part)
                if cleaned:
                    cells.append(cleaned)
            continue
        if "|" in value and not value.startswith("{{"):
            value = value.rsplit("|", 1)[-1].strip()
        cleaned = clean_text(value)
        if cleaned:
            cells.append(cleaned)
    return cells


def caption_output_quantity(caption: str) -> float:
    match = re.search(r"(?<![\d.])(\d+(?:\.\d+)?)\s*x\b", caption, re.IGNORECASE)
    return parse_quantity(match.group(1)) if match else 1


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
    output_quantity = caption_output_quantity(caption)
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
        outputs.append(Ingredient(name=title, quantity=output_quantity))
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


def parse_effects(fields: dict[str, str]) -> list[str]:
    effects = parse_buffs(fields.get("attributes"))
    labels = {
        "projdamageMin": "Projectile Damage Min",
        "projdamageMax": "Projectile Damage Max",
        "elementdamageMin": "Element Damage Min",
        "elementdamageMax": "Element Damage Max",
        "projectileBreakChance": "Projectile Break Chance",
        "durability": "Durability",
        "flammable": "Flammable",
    }
    for field in EFFECT_FIELDS:
        if field == "attributes":
            continue
        value = clean_text(fields.get(field))
        if value:
            effects.append(f"{labels[field]}: {value}")
    return effects


def parse_item_info(wikitext: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for template in ITEM_INFO_TEMPLATES:
        body = extract_template(wikitext, template)
        if body:
            fields.update(parse_fields(body))
    return fields


def slugify(title: str) -> str:
    return title.replace(" ", "_")


def item_from_wikitext(title: str, wikitext: str, categories: Iterable[str] = ()) -> Item:
    consumables = parse_consumables(wikitext)
    item_info = parse_item_info(wikitext)
    info_fields = {**item_info, **consumables}
    resolved_wikitext = wikitext.replace("{{PAGENAME}}", title)
    recipe = parse_recipe(resolved_wikitext) or parse_wikitable_recipe(title, resolved_wikitext)
    bench = clean_text(info_fields.get("bench") or info_fields.get("benchtool"))
    benches = recipe.benches if recipe and recipe.benches else ([bench] if bench else [])
    overrides = load_item_overrides().get(title.lower(), {})
    description = clean_text(info_fields.get("description") or info_fields.get("Itemable_description"))
    categories = parse_categories(wikitext, categories)
    categories = sorted(set(categories).union(overrides.get("categories", [])))
    effects = parse_effects(info_fields)
    tier = overrides.get("tier") or parse_tier(
        categories,
        info_fields.get("tech"),
        info_fields.get("techlvl"),
        info_fields.get("tech_tier"),
        info_fields.get("tier"),
        info_fields.get("techLevelNeeded"),
        info_fields.get("techLevelUnlock"),
    )
    return Item(
        name=title,
        slug=slugify(title),
        categories=categories,
        tier=tier,
        description=description,
        duration=clean_text(info_fields.get("duration")),
        spoil_time=clean_text(info_fields.get("spoiltime") or info_fields.get("spoil_time")),
        weight=clean_text(info_fields.get("weight") or info_fields.get("Itemable_weight")),
        stack=clean_text(info_fields.get("stack") or info_fields.get("Itemable_maxStack")),
        bench=bench,
        benches=benches,
        effects=effects,
        buffs=effects,
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


async def fetch_category_titles(
    client: httpx.AsyncClient,
    category: str,
    max_depth: int = 4,
) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = {}
    category_queue: list[tuple[str, int]] = [(category, 0)]
    seen_categories: set[str] = set()

    while category_queue:
        current_category, depth = category_queue.pop(0)
        if current_category in seen_categories:
            continue
        seen_categories.add(current_category)
        current_label = clean_category(current_category)
        params: dict[str, str | int] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": current_category,
            "cmlimit": 500,
            "format": "json",
        }
        while True:
            payload = await fetch_json(client, params)
            for page in payload.get("query", {}).get("categorymembers", []):
                if page.get("ns") == 0:
                    titles.setdefault(page["title"], set()).add(current_label)
                elif page.get("ns") == 14 and depth < max_depth:
                    category_queue.append((page["title"], depth + 1))
            cont = payload.get("continue")
            if not cont:
                break
            params.update(cont)
        await asyncio.sleep(0.1)

    return titles


async def fetch_template_titles(client: httpx.AsyncClient, template: str, label: str) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = {}
    params: dict[str, str | int] = {
        "action": "query",
        "list": "embeddedin",
        "eititle": f"Template:{template}",
        "einamespace": 0,
        "eilimit": 500,
        "format": "json",
    }
    while True:
        payload = await fetch_json(client, params)
        for page in payload.get("query", {}).get("embeddedin", []):
            titles.setdefault(page["title"], set()).add(label)
        cont = payload.get("continue")
        if not cont:
            return titles
        params.update(cont)


async def fetch_seed_titles(client: httpx.AsyncClient) -> dict[str, set[str]]:
    titles: dict[str, set[str]] = {}
    for category in ITEM_CATEGORIES:
        for title, categories in (await fetch_category_titles(client, category)).items():
            titles.setdefault(title, set()).update(categories)
        await asyncio.sleep(0.2)
    for template in ITEM_INFO_TEMPLATES:
        label = "Items" if template == "ItemData" else template
        for title, categories in (await fetch_template_titles(client, template, label)).items():
            titles.setdefault(title, set()).update(categories)
        await asyncio.sleep(0.2)
    return titles


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


async def fetch_wikitext_batch(client: httpx.AsyncClient, titles: list[str]) -> dict[str, str]:
    if not titles:
        return {}
    payload = await fetch_json(
        client,
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(titles),
            "format": "json",
            "formatversion": 2,
        },
    )
    pages = payload.get("query", {}).get("pages", [])
    result: dict[str, str] = {}
    for page in pages:
        if page.get("missing"):
            continue
        revisions = page.get("revisions") or []
        slots = revisions[0].get("slots", {}) if revisions else {}
        content = slots.get("main", {}).get("content")
        if content:
            result[page["title"]] = content
    return result


def recipe_dependencies(items: Iterable[Item]) -> set[str]:
    deps: set[str] = set()
    for item in items:
        if not item.recipe:
            continue
        for ingredient in item.recipe.inputs:
            deps.add(ingredient.name)
    return deps


async def scrape_items(max_extra_pages: int = 800) -> list[Item]:
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        seed_titles = await fetch_seed_titles(client)
        queue = list(seed_titles)
        seen: set[str] = set()
        items: dict[str, Item] = {}
        extra_pages = 0

        while queue:
            batch: list[str] = []
            while queue and len(batch) < 50:
                title = queue.pop(0)
                key = title.lower()
                if key in seen:
                    continue
                seen.add(key)
                batch.append(title)
            if not batch:
                continue

            try:
                pages = await fetch_wikitext_batch(client, batch)
            except httpx.HTTPError:
                pages = {}

            for title, wikitext in pages.items():
                item = item_from_wikitext(title, wikitext, seed_titles.get(title, set()))
                if item.categories or item.buffs or item.recipe:
                    items[item.name.lower()] = item

                for dep in recipe_dependencies([item]):
                    dep_key = dep.lower()
                    if dep_key not in seen and dep_key not in items and extra_pages < max_extra_pages:
                        queue.append(dep)
                        extra_pages += 1

            await asyncio.sleep(0.2)

    return sorted(items.values(), key=lambda item: item.name.lower())


def refresh_item_data() -> dict[str, str | int]:
    items = asyncio.run(scrape_items())
    refreshed_at = datetime.now(timezone.utc).isoformat()
    save_items(items, refreshed_at)
    return {"refreshed_at": refreshed_at, "count": len(items)}


food_from_wikitext = item_from_wikitext
scrape_foods = scrape_items
refresh_food_data = refresh_item_data
