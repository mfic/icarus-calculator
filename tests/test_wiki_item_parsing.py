from app.models import Ingredient
from app.services.wiki import item_from_wikitext, item_icons


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


def test_epoxy_multiple_recipes_are_all_parsed():
    item = item_from_wikitext(
        "Epoxy",
        """{{Crafting/start}}
{{Recipe
 |Inputs=Sulfur:2,Tree Sap:4
 |Outputs=Epoxy:1
 |Benches=Mortar and Pestle,Windmill,Material Processor
}}
{{Recipe
 |Inputs=Crushed Bone:4
 |Outputs=Epoxy:1
 |Benches=Mortar and Pestle,Windmill,Material Processor
}}
{{Recipe
 |Inputs=Infected Bark:1
 |Outputs=Epoxy:5
 |Benches=Biofuel Bio-Cleaner,Organic Residue Cleanser
}}
{{Recipe
 |Inputs=Hammerhead Slime:1
 |Outputs=Epoxy:50
 |Benches=Mortar and Pestle,Windmill,Material Processor
}}
{{Crafting/end}}
""",
    )

    assert len(item.recipes) == 4
    assert item.recipe == item.recipes[0]

    ids = [recipe.id for recipe in item.recipes]
    assert ids == ["sulfur+tree sap", "crushed bone", "infected bark", "hammerhead slime"]
    assert len(set(ids)) == 4

    labels = [recipe.label for recipe in item.recipes]
    assert labels == ["2 Sulfur + 4 Tree Sap", "4 Crushed Bone", "1 Infected Bark", "1 Hammerhead Slime"]

    assert item.recipes[2].benches == ["Biofuel Bio-Cleaner", "Organic Residue Cleanser"]


def test_refining_table_resolves_ingot_to_ore():
    item = item_from_wikitext(
        "Aluminium Ingot",
        """{{ItemData
|categories = Ingots
}}
==Description==
{{PAGENAME}} is the refined resource crafted from {{Item icon|Aluminium Ore}}.
==Refining==
{{PAGENAME}} is refined by adding ore to a Furnace, the minimum required Furnace for refining is as follows:
{| class="wikitable" style="text-align: center;"
|+style="text-align: center; height:50px;" |{{Item icon|Concrete Furnace}}
!style="width:80px;" |Input
!style="width:180px;" |Resource
!style="width:80px;" |Output
!style="width:180px;" |Ingot
|-
|1
|{{Item icon|Aluminium Ore}}
|1
|{{Item icon|Aluminium Ingot}}
|}
==Usage==
{{PAGENAME}} is used in the following items:<br>
{{Item icon|Aluminium Arrow}}
[[Category:Resources]]
""",
    )

    assert item.recipe is not None
    assert item.recipe.inputs == [Ingredient(name="Aluminium Ore", quantity=1)]
    assert item.recipe.outputs[0].name == "Aluminium Ingot"
    assert item.recipe.benches == ["Concrete Furnace"]


def test_refining_table_with_no_table_does_not_produce_recipe():
    item = item_from_wikitext(
        "Iron Ore",
        """{{ItemData}}
==Description==
Iron Ore is a Mineral.
== Refining==
2 x{{Item icon|Iron Ore}} can be refined to create 1 x{{Item icon|Iron Ingot}} at the following furnaces:
*{{Item icon|Stone Furnace}}
[[Category:Resources]]
""",
    )

    assert item.recipe is None


def test_refining_table_splits_multiple_resources_per_cell():
    item = item_from_wikitext(
        "Cold Steel Ingot",
        """{{ItemData}}
==Description==
{{PAGENAME}}s are a refined resource.
==Refining==
{| class="wikitable" style="text-align: center;"
|+ style="text-align: center;" |{{Item icon|Concrete Furnace}}
! |Input
! |Resource
! |Output
! |Ingot
|-
|1 (of each)
|{{Item icon|Steel Ingot}} + {{Item icon|Super Cooled Ice}}
|1
|{{Item icon|{{PAGENAME}}}}
|}
[[Category:Resources]]
""",
    )

    assert item.recipe is not None
    assert item.recipe.inputs == [
        Ingredient(name="Steel Ingot", quantity=1),
        Ingredient(name="Super Cooled Ice", quantity=1),
    ]
    assert item.recipe.outputs[0].name == "Cold Steel Ingot"


def test_refining_table_with_rowspan_output_cell():
    item = item_from_wikitext(
        "Clay Brick",
        """{{ItemData}}
==Description==
{{PAGENAME}}s are a refined resource.
==Refining==
{| class="wikitable" style="text-align: center;"
|+ style="text-align: center;" |{{Item icon|Stone Furnace}}
! |Input
! |Resource
! |Output
! |Ingot
|-
|1
|{{Item icon|Clay}}
| rowspan="2" |5
| rowspan="2" |{{Item icon|Clay Brick}}
|-
|0.1 L
|[[Water]]
|}
[[Category:Resources]]
""",
    )

    assert item.recipe is not None
    assert item.recipe.inputs == [
        Ingredient(name="Clay", quantity=1),
        Ingredient(name="Water", quantity=0.1),
    ]
    assert item.recipe.outputs[0].name == "Clay Brick"
    assert item.recipe.outputs[0].quantity == 5


def test_crafting_heading_with_spaces_is_parsed():
    item = item_from_wikitext(
        "Beeswax Wood Halfpieces",
        """{{Buildings}}
== Crafting ==
{| class="wikitable"
|+{{Icon link|Carpentry Bench}}
!Amount
!Resource
|-
|12||{{Item icon|Fiber}}
|-
|20||{{Item icon|Wood}}
|-
|10||{{Item icon|Beeswax}}
|}
""",
    )

    assert item.recipe is not None
    assert {(ingredient.name, ingredient.quantity) for ingredient in item.recipe.inputs} == {
        ("Fiber", 12),
        ("Wood", 20),
        ("Beeswax", 10),
    }


def test_icon_template_variants_are_cleaned_to_plain_names():
    item = item_from_wikitext(
        "Rustic Pot",
        """{{Deployables}}
==Crafting==
{| class="wikitable"
|+{{Icon link|Decoration Bench}}
!Amount
!Resource
|-
|20|| {{Item icon |Fiber}}
|-
|10||{{Item_icon|Stick}}
|-
|5||{{Icon link|Sulfur}}
|-
|2||{{Item icon|Iron Ingot}
|}
""",
    )

    assert item.recipe is not None
    assert {(ingredient.name, ingredient.quantity) for ingredient in item.recipe.inputs} == {
        ("Fiber", 20),
        ("Stick", 10),
        ("Sulfur", 5),
        ("Iron Ingot", 2),
    }


def test_icon_link_with_notext_param_is_cleaned():
    assert item_icons("{{Icon link|Ren|notext}}") == ["Ren"]


def test_consumable_food_gameplay_tag_adds_food_category():
    item = item_from_wikitext(
        "Bacon Butty",
        """{{ItemData
|ItemableGameplayTags=Item.Consumable.Food
}}
{{Crafting| {{Recipe |Inputs=Bread:1, Crispy Bacon:5, Butter:3 |Benches=Kitchen Bench |Outputs=Bacon Butty:3 }} }}
""",
    )

    assert "Food" in item.categories
    assert "Consumables" in item.categories
    assert item.primary_category == "Consumables"


def test_research_cost_table_without_resource_column_yields_no_recipe():
    item = item_from_wikitext(
        "Archer's Backpack",
        """{{ItemData}}
==Crafting==
{| class="wikitable" style="text-align: center;"
|+ style="text-align: center; height:50px;" |[[Workshop]]
! |'''Research Cost'''
! |'''Crafting Cost'''
|-
|250 {{Icon link|Ren|notext}}<br>100 {{Icon link|Exotics (Currency)|notext}}
|50 {{Icon link|Ren|notext}}<br>50 {{Icon link|Exotics (Currency)|notext}}
|}
[[Category:Workshop Backpacks]]
""",
    )

    assert item.recipe is None
