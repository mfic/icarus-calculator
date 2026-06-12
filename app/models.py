from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str
    quantity: float


class Recipe(BaseModel):
    inputs: list[Ingredient] = Field(default_factory=list)
    outputs: list[Ingredient] = Field(default_factory=list)
    benches: list[str] = Field(default_factory=list)


class FoodItem(BaseModel):
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
    buffs: list[str] = Field(default_factory=list)
    recipe: Recipe | None = None
    wiki_url: str | None = None
    source: str = "icarus.wiki.gg"


class BucketItem(BaseModel):
    food: str
    quantity: int = Field(default=1, ge=1)


class Bucket(BaseModel):
    id: str
    name: str
    items: list[BucketItem] = Field(default_factory=list)
    created_at: str
    updated_at: str


class BucketCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class BucketItemInput(BaseModel):
    food: str
    quantity: int = Field(default=1, ge=1)
