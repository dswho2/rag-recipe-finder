from typing import List, Optional
from pydantic import BaseModel, Field

class Ingredient(BaseModel):
    """Schema for recipe ingredients."""
    text: str = Field(..., description="Raw ingredient text")
    quantity: Optional[float] = Field(None, description="Quantity of the ingredient")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    name: str = Field(..., description="Name of the ingredient")

class RecipeStep(BaseModel):
    """Schema for recipe instructions."""
    step_number: int = Field(..., description="Step number in the recipe")
    text: str = Field(..., description="Instruction text")

class Recipe(BaseModel):
    """Schema for recipe data."""
    id: Optional[str] = Field(None, description="Unique identifier for the recipe")
    title: str = Field(..., description="Recipe title")
    description: Optional[str] = Field(None, description="Recipe description")
    ingredients: List[Ingredient] = Field(..., description="List of ingredients")
    instructions: List[RecipeStep] = Field(..., description="List of instructions")
    cooking_time: Optional[int] = Field(None, description="Cooking time in minutes")
    prep_time: Optional[int] = Field(None, description="Preparation time in minutes")
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    servings: Optional[int] = Field(None, description="Number of servings")
    cuisine: Optional[str] = Field(None, description="Type of cuisine")
    tags: List[str] = Field(default_factory=list, description="Recipe tags/categories")
    source: Optional[str] = Field(None, description="Source of the recipe (e.g., 'Recipe1M', 'web')")
    source_url: Optional[str] = Field(None, description="Original URL if from web scraping")
    embedding_id: Optional[str] = Field(None, description="ID of the embedding in vector store")
    recipe_hash: str = Field(..., description="Hash of title + ingredients + instructions for duplicate detection")

class RecipeSearchQuery(BaseModel):
    """Schema for recipe search queries."""
    query: str = Field(..., description="Search query text")
    limit: int = Field(default=10, description="Number of results to return")
    cuisine: Optional[str] = Field(None, description="Filter by cuisine type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags") 