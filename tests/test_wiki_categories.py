import asyncio

from app.services import wiki


def test_fetch_category_titles_recurses_into_subcategories(monkeypatch):
    async def fake_fetch_json(_client, params):
        category = params["cmtitle"]
        pages = {
            "Category:Ammo": [
                {"ns": 14, "title": "Category:Bullets"},
            ],
            "Category:Bullets": [
                {"ns": 14, "title": "Category:9mm Rounds"},
            ],
            "Category:9mm Rounds": [
                {"ns": 0, "title": "9mm Round"},
            ],
        }
        return {"query": {"categorymembers": pages.get(category, [])}}

    monkeypatch.setattr(wiki, "fetch_json", fake_fetch_json)

    result = asyncio.run(wiki.fetch_category_titles(object(), "Category:Ammo"))

    assert result == {"9mm Round": {"9mm Rounds"}}
