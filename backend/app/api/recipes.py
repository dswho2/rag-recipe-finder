from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.schemas import Recipe, RecipeSearchQuery
from app.services.recipe_service import RecipeService
import uuid

router = APIRouter()

class IngredientsInput(BaseModel):
    ingredients: List[str]
    limit: int = 10  # Optional: how many recipes to return
    min_score: float = 0.4  # Minimum similarity score to include

class IngredientMatch(BaseModel):
    matched_ingredients: List[str]
    total_ingredients_searched: int
    match_percentage: float

class RecipeSearchResult(BaseModel):
    id: str
    title: str
    description: str
    ingredients: List[str]
    cuisine: str
    tags: List[str]
    score: float
    ingredient_matches: IngredientMatch

def get_recipe_service() -> RecipeService:
    """Dependency to get RecipeService instance."""
    return RecipeService()

@router.post("/search/by-ingredients", response_model=List[RecipeSearchResult])
async def search_by_ingredients(
    ingredients_input: IngredientsInput,
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """Search for recipes based on available ingredients."""
    try:
        query = recipe_service._prepare_search_text(ingredients_input.ingredients)
        recipes = await recipe_service.search_recipes(
            query=query,
            search_ingredients=ingredients_input.ingredients,
            limit=ingredients_input.limit,
            min_score=ingredients_input.min_score
        )
        return recipes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search/semantic", response_model=List[RecipeSearchResult])
async def semantic_search(
    query: RecipeSearchQuery,
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """Advanced semantic search for recipes with filtering options."""
    try:
        recipes = await recipe_service.search_recipes(
            query=query.query,
            search_ingredients=[],  # No specific ingredients to match
            limit=query.limit,
            cuisine=query.cuisine,
            tags=query.tags
        )
        return recipes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Recipe)
async def create_recipe(
    recipe: Recipe,
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """Create a new recipe and store its embedding."""
    try:
        if not recipe.id:
            recipe.id = str(uuid.uuid4())
        await recipe_service.store_recipe(recipe)
        return recipe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/reset", response_model=List[Recipe])
async def reset_test_recipes(
    recipe_service: RecipeService = Depends(get_recipe_service)
):
    """Delete all recipes and add test recipes again."""
    try:
        # Delete all existing recipes
        await recipe_service.delete_all_recipes()
        
        # Add test recipes
        return await recipe_service.add_test_recipes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 