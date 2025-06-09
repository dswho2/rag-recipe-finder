# backend/app/services/recipe_ingestion_service.py

from typing import Dict, Any, List, Optional
import uuid
import re
from datetime import datetime
from enum import Enum
from app.core.schemas import Recipe, Ingredient, RecipeStep
from app.services.dynamodb_service import DynamoDBService
from app.services.langchain_service import LangChainService
import hashlib

class RecipeSource(Enum):
    """Enumeration of valid recipe sources."""
    RECIPE1M = "recipe1m"
    WEB = "web"
    USER = "user"
    API = "api"
    ADMIN = "admin"
    TEST = "test"  # For testing purposes

class RecipeIngestionService:
    """Service for ingesting recipes from various sources and storing them in our databases."""
    
    # Known web sources for recipes
    KNOWN_WEB_SOURCES = {
        'allrecipes',
        'foodnetwork',
        'epicurious',
        'tasty',
        'bbcgoodfood',
        'simplyrecipes',
        'food52',
        'bonappetit'
    }
    
    def __init__(self):
        self.dynamodb = DynamoDBService()
        self.langchain = LangChainService()
        
    def generate_recipe_id(self, source: str, original_id: Optional[str] = None) -> str:
        """
        Generate a unique, URL-safe recipe ID.
        
        Args:
            source: Source of the recipe (e.g., 'recipe1m', 'allrecipes', 'user')
            original_id: Original ID from the source if available
            
        Returns:
            A formatted recipe ID like 'recipe1m-12345' or 'web-allrecipes-67890'
            All IDs are lowercase and use only alphanumeric characters and hyphens.
        """
        # Convert source to lowercase and clean it
        source = source.lower().strip()
        
        # Determine the base prefix for the ID
        if source == RecipeSource.RECIPE1M.value:
            base = source
        elif source in self.KNOWN_WEB_SOURCES:
            base = f"web-{source}"
        elif source == RecipeSource.USER.value:
            base = "user"
        elif source == RecipeSource.API.value:
            base = "api"
        elif source == RecipeSource.ADMIN.value:
            base = "admin"
        else:
            base = f"other-{re.sub(r'[^a-z0-9-]', '', source)}"
            
        if original_id:
            # Clean and standardize the original ID
            clean_id = re.sub(r'[^a-z0-9-]', '', original_id.lower())
            return f"{base}-{clean_id}"
        else:
            # Generate a timestamp-based unique ID
            timestamp = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
            random_suffix = str(uuid.uuid4())[:8].lower()
            return f"{base}-{timestamp}-{random_suffix}"

    def normalize_ingredient(self, ingredient: Dict[str, Any]) -> Ingredient:
        """Normalize ingredient data to our schema."""
        # Extract quantity and unit using regex
        quantity_pattern = r'^(\d+(?:\.\d+)?)\s*'
        unit_pattern = r'(?:cup|cups|tbsp|tsp|g|kg|ml|l|pound|pounds|oz|ounce|ounces|piece|pieces)'
        
        text = ingredient.get('text', '').strip()
        quantity = None
        unit = None
        name = text
        
        # Try to extract quantity
        qty_match = re.match(quantity_pattern, text)
        if qty_match:
            quantity = float(qty_match.group(1))
            name = text[qty_match.end():].strip()
        
        # Try to extract unit
        unit_match = re.search(unit_pattern, name, re.IGNORECASE)
        if unit_match:
            unit = unit_match.group().lower()
            name = (name[:unit_match.start()] + name[unit_match.end():]).strip()
        
        # Clean up the name
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'^of\s+', '', name)  # Remove leading "of"
        name = name.lower()  # Convert to lowercase
        
        return Ingredient(
            text=text,
            name=name,
            quantity=quantity,
            unit=unit
        )

    def normalize_instruction(self, instruction: Dict[str, Any], step_number: int) -> RecipeStep:
        """Normalize instruction step to our schema."""
        return RecipeStep(
            step_number=step_number,
            text=instruction.get('text', '').strip()
        )

    def _generate_recipe_hash(self, title: str, ingredients: List[str], instructions: List[str]) -> str:
        """Generate a unique hash for a recipe based on its content."""
        # Normalize and sort ingredients/instructions to ensure same hash regardless of order
        normalized_title = title.lower().strip()
        normalized_ingredients = sorted([ing.lower().strip() for ing in ingredients])
        normalized_instructions = [inst.lower().strip() for inst in instructions]
        
        # Combine elements
        recipe_str = f"{normalized_title}|{'|'.join(normalized_ingredients)}|{'|'.join(normalized_instructions)}"
        return hashlib.sha256(recipe_str.encode()).hexdigest()

    async def process_recipe(self, raw_recipe: Dict[str, Any], source: str) -> Optional[str]:
        """
        Process a single recipe through the entire pipeline:
        1. Normalize the data
        2. Generate recipe ID
        3. Store in DynamoDB
        4. Generate and store embedding in Pinecone
        
        Returns:
            recipe_id if successful, None if failed
        
        Note:
            This method attempts to maintain consistency between DynamoDB and Pinecone.
            If storing in one database fails, it will attempt to clean up the other.
        """
        recipe_id = None
        stored_in_dynamodb = False
        stored_in_pinecone = False
        
        try:
            # Generate recipe hash first
            recipe_hash = self._generate_recipe_hash(
                title=raw_recipe.get('title', '').strip(),
                ingredients=[ing.get('text', '').strip() for ing in raw_recipe.get('ingredients', [])],
                instructions=[step.get('text', '').strip() for step in raw_recipe.get('instructions', [])]
            )
            
            # Check if recipe with this hash already exists
            existing_recipe = await self.dynamodb.get_recipe_by_hash(recipe_hash)
            if existing_recipe:
                # print(f"Found duplicate recipe: '{raw_recipe.get('title')}' (hash: {recipe_hash})")
                return f"duplicate:{existing_recipe.id}"  # Special format to indicate duplicate
            
            # Generate recipe ID for new recipe
            recipe_id = self.generate_recipe_id(
                source=source,
                original_id=raw_recipe.get('id') or raw_recipe.get('recipe_id')
            )
            
            # Normalize ingredients
            ingredients = [
                self.normalize_ingredient(ing)
                for ing in raw_recipe.get('ingredients', [])
            ]
            
            # Normalize instructions
            instructions = [
                self.normalize_instruction(step, idx + 1)
                for idx, step in enumerate(raw_recipe.get('instructions', []))
            ]
            
            # Create Recipe object with hash
            recipe = Recipe(
                id=recipe_id,
                title=raw_recipe.get('title', '').strip(),
                description=raw_recipe.get('description', '').strip(),
                ingredients=ingredients,
                instructions=instructions,
                cooking_time=raw_recipe.get('cooking_time'),
                prep_time=raw_recipe.get('prep_time'),
                servings=raw_recipe.get('servings'),
                cuisine=raw_recipe.get('cuisine', '').strip(),
                tags=raw_recipe.get('tags', []),
                source=source,
                source_url=raw_recipe.get('url'),
                recipe_hash=recipe_hash
            )
            
            # Store in DynamoDB first (synchronous call)
            try:
                self.dynamodb.store_recipe(recipe)  # Ignore return value, use our generated ID
                stored_in_dynamodb = True
            except Exception as e:
                print(f"Failed to store recipe in DynamoDB: {str(e)}")
                raise
            
            # Then store in Pinecone (async call)
            try:
                await self.langchain.store_recipe_embedding(
                    recipe_id=recipe_id,
                    text=self._prepare_recipe_text(recipe),
                    metadata=self._prepare_metadata(recipe)
                )
                stored_in_pinecone = True
            except Exception as e:
                print(f"Failed to store recipe embedding in Pinecone: {str(e)}")
                # If Pinecone storage fails, clean up DynamoDB (synchronous call)
                if stored_in_dynamodb:
                    try:
                        self.dynamodb.delete_recipe(recipe_id)
                        stored_in_dynamodb = False
                    except Exception as cleanup_error:
                        print(f"Failed to clean up DynamoDB after Pinecone error: {str(cleanup_error)}")
                raise
            
            return recipe_id
            
        except Exception as e:
            print(f"Error processing recipe: {str(e)}")
            # Clean up if needed
            if recipe_id:
                if stored_in_dynamodb:
                    try:
                        self.dynamodb.delete_recipe(recipe_id)
                    except Exception as cleanup_error:
                        print(f"Failed to clean up DynamoDB: {str(cleanup_error)}")
                if stored_in_pinecone:
                    try:
                        await self.langchain.vector_store.adelete(ids=[recipe_id])
                    except Exception as cleanup_error:
                        print(f"Failed to clean up Pinecone: {str(cleanup_error)}")
            return None
    
    def _prepare_recipe_text(self, recipe: Recipe) -> str:
        """Prepare recipe text for embedding."""
        ingredients = ", ".join(ing.text for ing in recipe.ingredients)
        instructions = " ".join(step.text for step in recipe.instructions)
        return f"{recipe.title}\nIngredients: {ingredients}\nInstructions: {instructions}".strip()
    
    def _prepare_metadata(self, recipe: Recipe) -> Dict[str, Any]:
        """Prepare minimal recipe metadata for vector store."""
        return {
            "title": recipe.title,
            "tags": recipe.tags or []
        }

    async def batch_process_recipes(self, recipes: List[Dict[str, Any]], source: str) -> List[str]:
        new_recipes = []
        duplicate_ids = []
        prepared_recipes = []
        embedding_texts = []
        embedding_metadata = []
        embedding_ids = []

        for raw in recipes:
            recipe_hash = self._generate_recipe_hash(
                title=raw.get('title', '').strip(),
                ingredients=[ing.get('text', '').strip() for ing in raw.get('ingredients', [])],
                instructions=[step.get('text', '').strip() for step in raw.get('instructions', [])]
            )
            existing = await self.dynamodb.get_recipe_by_hash(recipe_hash)
            if existing:
                duplicate_ids.append(f"duplicate:{existing.id}")
                continue

            recipe_id = self.generate_recipe_id(source, raw.get("id") or raw.get("recipe_id"))
            ingredients = [self.normalize_ingredient(i) for i in raw.get("ingredients", [])]
            instructions = [self.normalize_instruction(s, idx + 1) for idx, s in enumerate(raw.get("instructions", []))]
            recipe = Recipe(
                id=recipe_id,
                title=raw.get("title", "").strip(),
                description=raw.get("description", "").strip(),
                ingredients=ingredients,
                instructions=instructions,
                cooking_time=raw.get("cooking_time"),
                prep_time=raw.get("prep_time"),
                servings=raw.get("servings"),
                cuisine=raw.get("cuisine", "").strip(),
                tags=raw.get("tags", []),
                source=source,
                source_url=raw.get("url"),
                recipe_hash=recipe_hash
            )
            prepared_recipes.append(recipe)
            embedding_texts.append(self._prepare_recipe_text(recipe))
            embedding_metadata.append(self._prepare_metadata(recipe))
            embedding_ids.append(recipe_id)

        dynamodb_store_success = False
        if prepared_recipes:
            try:
                self.dynamodb.store_recipes_batch(prepared_recipes)
                dynamodb_store_success = True
            except Exception as e:
                print(f"DynamoDB batch insert failed: {str(e)}")

        if embedding_texts and dynamodb_store_success:
            try:
                await self.langchain.vector_store.aadd_texts(
                    texts=embedding_texts,
                    metadatas=embedding_metadata,
                    ids=embedding_ids,
                    batch_size=100,
                    show_progress=False,
                    namespace="recipes"
                )
            except Exception as e:
                print(f"Embedding batch failed: {str(e)}")

        return embedding_ids + duplicate_ids
