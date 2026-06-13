from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class Ingredient(BaseModel):
    name: str
    quantity: float


class Recipe(BaseModel):
    inputs: list[Ingredient] = Field(default_factory=list)
    outputs: list[Ingredient] = Field(default_factory=list)
    benches: list[str] = Field(default_factory=list)


class Item(BaseModel):
    name: str
    slug: str
    categories: list[str] = Field(default_factory=list)
    tier: str | None = None
    description: str | None = None
    duration: str | None = None
    spoil_time: str | None = None
    weight: str | None = None
    stack: str | None = None
    bench: str | None = None
    benches: list[str] = Field(default_factory=list)
    effects: list[str] = Field(default_factory=list)
    buffs: list[str] = Field(default_factory=list)
    recipe: Recipe | None = None
    wiki_url: str | None = None
    source: str = "icarus.wiki.gg"


class LoadoutItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item: str = Field(validation_alias=AliasChoices("item", "food"))
    quantity: int = Field(default=1, ge=1)


class Loadout(BaseModel):
    id: str
    name: str
    items: list[LoadoutItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class LoadoutCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class LoadoutItemInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item: str = Field(validation_alias=AliasChoices("item", "food"))
    quantity: int = Field(default=1, ge=1)


FoodItem = Item
BucketItem = LoadoutItem
Bucket = Loadout
BucketCreate = LoadoutCreate
BucketItemInput = LoadoutItemInput
