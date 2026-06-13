from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class Ingredient(BaseModel):
    name: str
    quantity: float


class Recipe(BaseModel):
    inputs: list[Ingredient] = Field(default_factory=list)
    outputs: list[Ingredient] = Field(default_factory=list)
    benches: list[str] = Field(default_factory=list)
    id: str = ""
    label: str = ""


class Item(BaseModel):
    name: str
    slug: str
    primary_category: str = "Other"
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
    recipes: list[Recipe] = Field(default_factory=list)
    wiki_url: str | None = None
    source: str = "icarus.wiki.gg"


class LoadoutItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item: str = Field(min_length=1, max_length=120, validation_alias=AliasChoices("item", "food"))
    quantity: int = Field(default=1, ge=1)


class Loadout(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    items: list[LoadoutItem] = Field(default_factory=list)
    collected: dict[str, float] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("collected", "farmed"),
    )
    in_storage: dict[str, float] = Field(default_factory=dict)
    recipe_choices: dict[str, str] = Field(default_factory=dict)
    ignored_materials: list[str] = Field(default_factory=list)
    owner_id: str = ""
    shared_with: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class LoadoutCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class LoadoutImport(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    items: list[LoadoutItem] = Field(default_factory=list, max_length=500)
    collected: dict[str, float] = Field(default_factory=dict)
    in_storage: dict[str, float] = Field(default_factory=dict, max_length=500)
    recipe_choices: dict[str, str] = Field(default_factory=dict)
    ignored_materials: list[str] = Field(default_factory=list, max_length=500)

    @field_validator("collected")
    @classmethod
    def _validate_collected(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) > 500:
            raise ValueError("collected may not contain more than 500 entries")
        for key in value:
            if not (1 <= len(key) <= 120):
                raise ValueError("collected keys must be between 1 and 120 characters")
        return value

    @field_validator("in_storage")
    @classmethod
    def _validate_in_storage(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) > 500:
            raise ValueError("in_storage may not contain more than 500 entries")
        for key in value:
            if not (1 <= len(key) <= 120):
                raise ValueError("in_storage keys must be between 1 and 120 characters")
        return value

    @field_validator("recipe_choices")
    @classmethod
    def _validate_recipe_choices(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 500:
            raise ValueError("recipe_choices may not contain more than 500 entries")
        for key, recipe_id in value.items():
            if not (1 <= len(key) <= 120):
                raise ValueError("recipe_choices keys must be between 1 and 120 characters")
            if len(recipe_id) > 200:
                raise ValueError("recipe_choices values must be at most 200 characters")
        return value

    @field_validator("ignored_materials")
    @classmethod
    def _validate_ignored_materials(cls, value: list[str]) -> list[str]:
        for name in value:
            if not (1 <= len(name) <= 120):
                raise ValueError("ignored_materials entries must be between 1 and 120 characters")
        return value


class LoadoutItemInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    item: str = Field(min_length=1, max_length=120, validation_alias=AliasChoices("item", "food"))
    quantity: int = Field(default=1, ge=1)


class CollectedItemInput(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    quantity: float = Field(default=0, ge=0)


class RecipeChoiceInput(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    recipe_id: str = Field(default="", max_length=200)


class IgnoredMaterialInput(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    ignored: bool


class ShareInput(BaseModel):
    account_id: str = Field(min_length=1, max_length=64)
    shared: bool


FoodItem = Item
BucketItem = LoadoutItem
Bucket = Loadout
BucketCreate = LoadoutCreate
BucketItemInput = LoadoutItemInput
FarmedItemInput = CollectedItemInput
