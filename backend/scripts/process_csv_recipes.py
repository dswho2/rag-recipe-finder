# backend/scripts/process_csv_recipes.py

import pandas as pd
import ast
import uuid
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
import sys
import os
import argparse

# Add the backend directory to the Python path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.schemas import Recipe, Ingredient, RecipeStep
from app.services.recipe_ingestion_service import RecipeIngestionService, RecipeSource
from app.services.dynamodb_service import DynamoDBService
from app.services.langchain_service import LangChainService

def parse_list_string(list_str: str) -> List[str]:
    """Parse string representation of list into actual list."""
    try:
        return ast.literal_eval(list_str)
    except:
        return []

def clean_ingredient(ingredient: str) -> Ingredient:
    """Clean and structure ingredient text into an Ingredient model."""
    # Extract components
    quantity_val = extract_quantity(ingredient)
    unit_val = extract_unit(ingredient)
    name_val = extract_ingredient_name(ingredient)
    
    # Create Ingredient model
    return Ingredient(
        text=ingredient.strip(),  # Keep original text
        name=name_val,           # Clean name for search
        quantity=quantity_val,    # Extracted quantity
        unit=unit_val            # Extracted unit
    )

def extract_quantity(ingredient: str) -> Optional[float]:
    """Extract the quantity from an ingredient string."""
    parts = ingredient.strip().split()
    if not parts:
        return None
        
    # Try to convert first part to float
    try:
        return float(parts[0].replace(',', ''))
    except ValueError:
        # Handle fractions like "1/2"
        if '/' in parts[0]:
            try:
                num, denom = parts[0].split('/')
                return float(num) / float(denom)
            except (ValueError, ZeroDivisionError):
                pass
    return None

def extract_unit(ingredient: str) -> Optional[str]:
    """Extract the unit from an ingredient string."""
    common_units = {
        'cup', 'cups', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'l',
        'pound', 'pounds', 'tablespoon', 'tablespoons', 'teaspoon', 'teaspoons',
        'ounce', 'ounces', 'gram', 'grams', 'kilogram', 'kilograms',
        'milliliter', 'milliliters', 'liter', 'liters',
        'pinch', 'dash', 'handful', 'piece', 'pieces'
    }
    
    parts = ingredient.strip().split()
    if len(parts) < 2:
        return None
        
    # Skip the first part (assumed to be quantity)
    for part in parts[1:]:
        clean_part = part.lower().rstrip('s.,')  # Remove plurals and punctuation
        if clean_part in common_units:
            return clean_part
            
    return None

def extract_ingredient_name(ingredient: str) -> str:
    """Extract the main ingredient name from the text."""
    parts = ingredient.strip().split()
    if not parts:
        return ""
        
    # Skip quantity
    start_idx = 0
    if parts[start_idx].replace('.','',1).replace('/','',1).replace(',','',1).replace('-','',1).isdigit():
        start_idx += 1
        
    # Skip units
    if start_idx < len(parts):
        clean_part = parts[start_idx].lower().rstrip('s.,')
        if clean_part in {'cup', 'tbsp', 'tsp', 'oz', 'lb', 'g', 'kg', 'ml', 'l'}:
            start_idx += 1
            
    # Join the remaining parts
    return ' '.join(parts[start_idx:]).strip()

def generate_recipe_hash(title: str, ingredients: List[str], instructions: List[str]) -> str:
    """Generate a unique hash for a recipe based on its content."""
    # Normalize and sort ingredients/instructions to ensure same hash regardless of order
    normalized_title = title.lower().strip()
    normalized_ingredients = sorted([ing.lower().strip() for ing in ingredients])
    normalized_instructions = [inst.lower().strip() for inst in instructions]
    
    # Combine elements
    recipe_str = f"{normalized_title}|{'|'.join(normalized_ingredients)}|{'|'.join(normalized_instructions)}"
    return hashlib.sha256(recipe_str.encode()).hexdigest()

async def process_recipes(csv_path: str, chunk_iterator=None, batch_size: int = 100):
    """Process recipes from CSV file and store them in our databases."""
    # Initialize services
    recipe_service = RecipeIngestionService()  # Service initializes its own dependencies

    # Ensure DynamoDB table exists
    recipe_service.dynamodb.ensure_table_exists()

    # If no iterator provided, create one
    if chunk_iterator is None:
        chunk_iterator = pd.read_csv(csv_path, chunksize=batch_size)

    total_processed = 0
    total_successful = 0
    all_successful_ids = []  # Track all successful IDs

    for chunk in chunk_iterator:
        recipes_batch = []
        
        for _, row in chunk.iterrows():
            try:
                # Parse ingredients and directions from their string representation
                ingredients = parse_list_string(row['ingredients'])
                directions = parse_list_string(row['directions'])
                ner_ingredients = parse_list_string(row['NER'])

                # Generate recipe hash
                recipe_hash = recipe_service._generate_recipe_hash(
                    title=row['title'],
                    ingredients=ingredients,
                    instructions=directions
                )

                # Create Recipe model instance
                recipe = Recipe(
                    id=str(uuid.uuid4()),
                    title=row['title'],
                    description="",  # No description in the CSV
                    ingredients=[clean_ingredient(ing) for ing in ingredients],
                    instructions=[RecipeStep(step_number=i+1, text=step) for i, step in enumerate(directions)],
                    cuisine="",  # No cuisine info in the CSV
                    tags=ner_ingredients,  # Use NER ingredients as tags
                    source=RecipeSource.API.value,
                    source_url=row['link'] if pd.notna(row['link']) else "",  # Empty string instead of None
                    prep_time=0 if pd.isna(row.get('prep_time')) else row.get('prep_time'),  # Default to 0
                    cooking_time=0 if pd.isna(row.get('cooking_time')) else row.get('cooking_time'),  # Default to 0
                    total_time=None,  # We don't have this in the CSV
                    servings=0 if pd.isna(row.get('servings')) else row.get('servings'),  # Default to 0
                    recipe_hash=recipe_hash  # Set the hash when creating the Recipe
                )
                recipes_batch.append(recipe)
                
            except Exception as e:
                print(f"Error processing recipe {row['title']}: {str(e)}")
                continue

        if recipes_batch:
            # Process batch
            successful_ids = await recipe_service.batch_process_recipes(
                [recipe.model_dump() for recipe in recipes_batch],  # Convert to dict for storage
                RecipeSource.API.value
            )
            all_successful_ids.extend(successful_ids)  # Add to our list of all IDs
            
            total_processed += len(recipes_batch)
            
            # Count duplicates and new recipes
            duplicates = sum(1 for id in successful_ids if isinstance(id, str) and id.startswith('duplicate:'))
            new_recipes = len(successful_ids) - duplicates
            total_successful += new_recipes  # Only count new recipes as successful
            
            print(f"Processed batch: {new_recipes} new, {duplicates} duplicates, {len(recipes_batch) - len(successful_ids)} failed")
            print(f"Total progress: {total_successful} new recipes stored")

    return all_successful_ids, total_processed

if __name__ == "__main__":
    # Use a path that works whether we're in the root or backend directory
    csv_path = "recipes.csv"
    if not os.path.exists(csv_path):
        csv_path = os.path.join("..", "backend", "recipes.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Could not find recipes.csv in current directory or backend directory")
        print(f"Current working directory: {os.getcwd()}")
        sys.exit(1)
    
    # Add argument parsing for test mode
    parser = argparse.ArgumentParser(description='Process recipes from CSV into databases')
    parser.add_argument('--test', action='store_true', help='Run in test mode with only a few recipes')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    args = parser.parse_args()

    if args.test:
        print("Running in test mode with first few recipes...")
        print(f"Reading from: {csv_path}")
        # Read just the first few recipes for testing
        df = pd.read_csv(csv_path, nrows=5)
        # Convert to iterator format for compatibility
        chunk_iterator = [df]
    else:
        print(f"Processing entire dataset with batch size {args.batch_size}...")
        chunk_iterator = pd.read_csv(csv_path, chunksize=args.batch_size)
    
    print(f"Starting recipe processing from {csv_path}")
    successful_ids, total_processed = asyncio.run(process_recipes(csv_path, chunk_iterator, args.batch_size))
    
    # Count total duplicates and new recipes
    duplicates = sum(1 for id in successful_ids if isinstance(id, str) and id.startswith('duplicate:'))
    new_recipes = len(successful_ids) - duplicates
    
    print("\nProcessing complete!")
    print(f"Total recipes processed: {total_processed}")
    print(f"Successfully stored: {new_recipes} new recipes")
    if duplicates > 0:
        print(f"Skipped {duplicates} duplicate recipes") 