# backend/app/services/recipe_service.py

from typing import List, Optional, Dict, Any
import json
import re
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
from app.core.config import settings
from app.core.schemas import Recipe, Ingredient, RecipeStep
import uuid
from app.services.dynamodb_service import DynamoDBService
from app.services.langchain_service import LangChainService

class RecipeService:
    def __init__(self):
        """Initialize the recipe service with DynamoDB and LangChain services."""
        self.dynamodb = DynamoDBService()
        self.langchain = LangChainService()
        
        # Initialize Pinecone with latest client
        self.pc = Pinecone(
            api_key=settings.PINECONE_API_KEY,
            source_tag="recipe-finder"  # Track API calls source
        )
        
        # Get or create index with latest configuration
        if settings.PINECONE_INDEX_NAME not in [idx.name for idx in self.pc.list_indexes()]:
            self.pc.create_index(
                name=settings.PINECONE_INDEX_NAME,
                dimension=settings.EMBEDDING_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=settings.AWS_REGION
                ),
                metadata_config={
                    "indexed": ["cuisine", "tags"]  # Enable filtering on these fields
                }
            )
        self.index = self.pc.Index(settings.PINECONE_INDEX_NAME)

    def _extract_ingredient_name(self, ingredient_text: str) -> str:
        """Extract just the ingredient name without quantities or units."""
        # Remove quantities (numbers and units)
        name = re.sub(r'^\d+(\.\d+)?\s*(g|kg|ml|l|tbsp|tsp|cup|cups|large|small|medium)?\s*', '', ingredient_text.lower())
        # Remove common prepositions and articles
        name = re.sub(r'^(of|the|a|an)\s+', '', name)
        return name.strip()

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text using OpenAI's API."""
        response = self.openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=text,
            dimensions=settings.EMBEDDING_DIMENSIONS
        )
        return response.data[0].embedding

    def _prepare_recipe_text(self, recipe: Recipe) -> str:
        ingredients = ", ".join(ing.text for ing in recipe.ingredients)
        instructions = " ".join(step.text for step in recipe.instructions)
        return f"{recipe.title}\nIngredients: {ingredients}\nInstructions: {instructions}".strip()

    def _prepare_metadata(self, recipe: Recipe) -> Dict[str, Any]:
        return {
            "title": recipe.title,
            "tags": recipe.tags or []
        }

    def _prepare_search_text(self, ingredients: List[str]) -> str:
        """Prepare search text optimized for ingredient matching."""
        # Clean ingredient names
        clean_ingredients = [self._extract_ingredient_name(ing) for ing in ingredients]
        ingredients_text = " ".join(clean_ingredients)
        return f"recipe with ingredients: {ingredients_text} cooking meal food dish"

    async def store_recipe(self, recipe: Recipe) -> str:
        """Store a recipe in both DynamoDB and vector store."""
        # Store full recipe in DynamoDB
        await self.dynamodb.store_recipe(recipe)
        
        # Store searchable data in vector store
        recipe_text = self._prepare_recipe_text(recipe)
        metadata = self._prepare_metadata(recipe)
        await self.langchain.store_recipe_embedding(recipe.id, recipe_text, metadata)
        
        return recipe.id

    async def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Get a recipe by ID from DynamoDB."""
        return await self.dynamodb.get_recipe(recipe_id)

    async def search_recipes(
        self,
        query: str,
        search_ingredients: List[str],
        limit: int = 10,
        cuisine: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_score: float = 0.4
    ) -> List[Dict[str, Any]]:
        """Search for recipes using semantic similarity and ingredient matching."""
        # Prepare search query
        search_text = self._prepare_search_text(search_ingredients) if search_ingredients else query
        
        # Get similar recipes from vector store
        similar_recipes = await self.langchain.similar_recipes_query(search_text, k=limit * 2)
        
        # Process and filter results
        recipes = []
        for item in similar_recipes:
            if item["score"] < min_score:
                continue
            
            metadata = item["metadata"]
            
            # Apply tag filters
            if tags and not all(tag in metadata.get("tags", []) for tag in tags):
                continue
            
            # Calculate ingredient matches
            ingredients = metadata.get("ingredients", [])
            ingredient_matches = self._calculate_ingredient_matches(ingredients, search_ingredients)
            
            recipes.append({
                "id": item["metadata"].get("id"),
                "title": metadata.get("title", "Unknown"),
                "description": "",
                "ingredients": ingredients,
                "cuisine": "",
                "tags": metadata.get("tags", []),
                "score": round(float(item["score"]), 3),
                "ingredient_matches": ingredient_matches
            })
        
        # Sort by match percentage and score
        recipes.sort(key=lambda x: (x["ingredient_matches"]["match_percentage"], x["score"]), reverse=True)
        return recipes[:limit]

    def _calculate_ingredient_matches(self, recipe_ingredients: List[str], search_ingredients: List[str]) -> Dict[str, Any]:
        """Calculate how many search ingredients are found in the recipe."""
        clean_recipe_ingredients = [self._extract_ingredient_name(ing) for ing in recipe_ingredients]
        clean_search_ingredients = [self._extract_ingredient_name(ing) for ing in search_ingredients]
        
        matches = [ing for ing in clean_search_ingredients if any(ing in recipe_ing for recipe_ing in clean_recipe_ingredients)]
        total = len(clean_search_ingredients)
        matched = len(matches)
        
        return {
            "matched_ingredients": matches,
            "total_ingredients_searched": total,
            "match_percentage": round((matched / total) * 100 if total > 0 else 0, 1)
        }

    async def suggest_recipe(self, ingredients: List[str]) -> str:
        """Get a recipe suggestion based on available ingredients."""
        # Find similar recipes
        similar = await self.langchain.similar_recipes_query(
            self._prepare_search_text(ingredients),
            k=3
        )
        
        # Generate suggestion
        return await self.langchain.generate_recipe_suggestion(ingredients, similar)

    async def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from both DynamoDB and vector store."""
        # Delete from DynamoDB
        dynamo_success = await self.dynamodb.delete_recipe(recipe_id)
        if not dynamo_success:
            return False
        
        # Delete from vector store
        try:
            await self.langchain.vector_store.adelete([recipe_id])
            return True
        except Exception:
            return False

    async def process_recipe1m(self, recipe_data: Dict[str, Any]) -> Recipe:
        """Process a Recipe1M format recipe into our schema."""
        # Extract and normalize ingredients
        ingredients = [
            Ingredient(
                text=ing.get('text', ''),
                name=ing.get('name', ing.get('text', '')),
                quantity=ing.get('quantity'),
                unit=ing.get('unit')
            )
            for ing in recipe_data.get('ingredients', [])
        ]
        
        # Extract and normalize instructions
        instructions = [
            RecipeStep(
                step_number=idx + 1,
                text=step.get('text', '')
            )
            for idx, step in enumerate(recipe_data.get('instructions', []))
        ]
        
        # Create Recipe object
        recipe = Recipe(
            id=recipe_data.get('id'),
            title=recipe_data.get('title', 'Untitled Recipe'),
            description=recipe_data.get('description'),
            ingredients=ingredients,
            instructions=instructions,
            cooking_time=recipe_data.get('cooking_time'),
            prep_time=recipe_data.get('prep_time'),
            servings=recipe_data.get('servings'),
            cuisine=recipe_data.get('cuisine'),
            tags=recipe_data.get('tags', []),
            source='Recipe1M'
        )
        
        return recipe

    async def delete_all_recipes(self):
        """Delete all recipes from the index."""
        # Delete all vectors in batches
        while True:
            # Get all vector IDs (up to 1000)
            response = self.index.query(
                vector=[0] * settings.EMBEDDING_DIMENSIONS,  # Dummy vector
                top_k=1000,
                include_metadata=False
            )
            
            if not response.matches:
                break
                
            # Delete the batch of vectors
            ids = [match.id for match in response.matches]
            self.index.delete(ids=ids)

    async def add_test_recipes(self) -> List[Recipe]:
        """Add test recipes to the index."""
        test_recipes = [
            Recipe(
                id=str(uuid.uuid4()),
                title="Simple Omelette",
                description="Quick and easy breakfast omelette",
                ingredients=[
                    {"text": "3 large eggs", "name": "eggs", "quantity": 3.0, "unit": "large"},
                    {"text": "30ml milk", "name": "milk", "quantity": 30.0, "unit": "ml"},
                    {"text": "Salt and pepper", "name": "seasoning", "quantity": None, "unit": None},
                    {"text": "1 tbsp butter", "name": "butter", "quantity": 1.0, "unit": "tbsp"}
                ],
                instructions=[
                    {"step_number": 1, "text": "Beat eggs with milk and seasoning"},
                    {"step_number": 2, "text": "Melt butter in pan"},
                    {"step_number": 3, "text": "Pour in egg mixture and cook until set"}
                ],
                cuisine="International",
                tags=["breakfast", "quick", "eggs"]
            ),
            Recipe(
                id=str(uuid.uuid4()),
                title="Simple Pasta Carbonara",
                description="Classic Italian pasta dish with eggs and pancetta",
                ingredients=[
                    {"text": "200g spaghetti", "name": "spaghetti", "quantity": 200.0, "unit": "g"},
                    {"text": "100g pancetta", "name": "pancetta", "quantity": 100.0, "unit": "g"},
                    {"text": "2 large eggs", "name": "eggs", "quantity": 2.0, "unit": "large"},
                    {"text": "50g pecorino cheese", "name": "pecorino", "quantity": 50.0, "unit": "g"},
                    {"text": "Black pepper", "name": "seasoning", "quantity": None, "unit": None}
                ],
                instructions=[
                    {"step_number": 1, "text": "Cook pasta in salted water"},
                    {"step_number": 2, "text": "Fry pancetta until crispy"},
                    {"step_number": 3, "text": "Mix eggs and cheese"},
                    {"step_number": 4, "text": "Combine all ingredients"}
                ],
                cuisine="Italian",
                tags=["pasta", "quick", "dinner"]
            ),
            Recipe(
                id=str(uuid.uuid4()),
                title="Pancakes",
                description="Fluffy breakfast pancakes",
                ingredients=[
                    {"text": "2 cups all-purpose flour", "name": "flour", "quantity": 2.0, "unit": "cups"},
                    {"text": "2 large eggs", "name": "eggs", "quantity": 2.0, "unit": "large"},
                    {"text": "1 cup milk", "name": "milk", "quantity": 1.0, "unit": "cup"},
                    {"text": "2 tbsp butter, melted", "name": "butter", "quantity": 2.0, "unit": "tbsp"},
                    {"text": "2 tbsp sugar", "name": "sugar", "quantity": 2.0, "unit": "tbsp"},
                    {"text": "1 tsp baking powder", "name": "baking powder", "quantity": 1.0, "unit": "tsp"}
                ],
                instructions=[
                    {"step_number": 1, "text": "Mix dry ingredients"},
                    {"step_number": 2, "text": "Whisk wet ingredients"},
                    {"step_number": 3, "text": "Combine and cook on griddle"}
                ],
                cuisine="American",
                tags=["breakfast", "sweet"]
            )
        ]
        
        for recipe in test_recipes:
            await self.store_recipe(recipe)
        
        return test_recipes 