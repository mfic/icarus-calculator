from app.services.wiki import item_from_wikitext


def test_ammo_template_attributes_become_effects():
    item = item_from_wikitext(
        "9mm Miasmic Round",
        """{{Ammo
  | attributes=+15% chance to cause Miasma on Hit with Attacks<br><br>Inflicts the 'Miasma' modifier for 10 seconds
  | projdamageMin=50
  | elementdamageMax=100 Poison Damage
  | techlvl=[[:Category:Tier 3|Tier 3]]
}}
[[Category:Miasmic Ammo]]
""",
    )

    assert item.tier == "Tier 3"
    assert "+15% chance to cause Miasma on Hit with Attacks" in item.effects
    assert "Projectile Damage Min: 50" in item.effects
    assert "Element Damage Max: 100 Poison Damage" in item.effects


def test_compact_crafting_table_parses_dirt_recipe():
    item = item_from_wikitext(
        "Dirt Corner",
        """{{Buildings
  | attributes=+2 Insulation from Temperature
}}
==Crafting==
{| class="wikitable"
|+style="text-align: center;" |{{Icon link|Character Crafting}}
!Amount
!Resource
|-
|20||{{Item icon|Dirt}}
|}
[[Category:Dirt Buildings]]
""",
    )

    assert item.recipe is not None
    assert item.recipe.inputs[0].name == "Dirt"
    assert item.recipe.inputs[0].quantity == 20
    assert item.recipe.outputs[0].name == "Dirt Corner"


def test_pagename_recipe_outputs_are_resolved():
    item = item_from_wikitext(
        "Polymerizer",
        """{{Crafting|
  {{Recipe
    |Inputs=Titanium Plate:20
    |Outputs={{PAGENAME}}:1
  }}
}}""",
    )

    assert item.recipe is not None
    assert item.recipe.outputs[0].name == "Polymerizer"


def test_tech_tier_field_sets_tier():
    item = item_from_wikitext(
        "Crude Oil Generator",
        """{{Deployables
  | tech_tier=[[:Category:Tier 5|Tier 5]]
}}
""",
    )

    assert item.tier == "Tier 5"
