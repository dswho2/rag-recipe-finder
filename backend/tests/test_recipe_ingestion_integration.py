import pytest
import os
from typing import List, AsyncGenerator
from pinecone import Pinecone
from app.services.recipe_ingestion_service import RecipeIngestionService, RecipeSource
from app.services.dynamodb_service import DynamoDBService
from app.services.langchain_service import LangChainService
from app.core.schemas import Recipe, Ingredient, RecipeStep
import boto3
from moto import mock_aws
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test data with realistic recipes
TEST_RECIPES = [
    {
        "title": "Classic Chocolate Chip Cookies",
        "description": "Soft and chewy chocolate chip cookies",
        "ingredients": [
            {"text": "2 1/4 cups all-purpose flour"},
            {"text": "1 cup unsalted butter, softened"},
            {"text": "3/4 cup granulated sugar"},
            {"text": "3/4 cup packed brown sugar"},
            {"text": "2 large eggs"},
            {"text": "1 teaspoon vanilla extract"},
            {"text": "1 teaspoon baking soda"},
            {"text": "1/2 teaspoon salt"},
            {"text": "2 cups semisweet chocolate chips"}
        ],
        "instructions": [
            {"text": "Preheat oven to 375°F (190°C)"},
            {"text": "Cream together butter and sugars until smooth"},
            {"text": "Beat in eggs and vanilla"},
            {"text": "Mix in flour, baking soda, and salt"},
            {"text": "Stir in chocolate chips"},
            {"text": "Drop rounded tablespoons onto ungreased baking sheets"},
            {"text": "Bake for 10 to 12 minutes until golden brown"}
        ],
        "cooking_time": 12,
        "prep_time": 15,
        "servings": 24,
        "cuisine": "American",
        "tags": ["dessert", "cookies", "baking"],
        "source_url": "https://example.com/chocolate-chip-cookies"
    },
    {
        "title": "Simple Tomato Pasta",
        "description": "Quick and easy pasta with fresh tomato sauce",
        "ingredients": [
            {"text": "1 pound spaghetti"},
            {"text": "4 large ripe tomatoes"},
            {"text": "4 cloves garlic, minced"},
            {"text": "1/4 cup extra virgin olive oil"},
            {"text": "1/2 cup fresh basil leaves"},
            {"text": "1 teaspoon salt"},
            {"text": "1/2 teaspoon black pepper"},
            {"text": "1/2 cup grated Parmesan cheese"}
        ],
        "instructions": [
            {"text": "Cook pasta according to package directions"},
            {"text": "Dice tomatoes and chop basil"},
            {"text": "Heat oil in a large pan and sauté garlic"},
            {"text": "Add tomatoes and cook for 5-7 minutes"},
            {"text": "Season with salt and pepper"},
            {"text": "Toss with cooked pasta and fresh basil"},
            {"text": "Serve with Parmesan cheese"}
        ],
        "cooking_time": 15,
        "prep_time": 10,
        "servings": 4,
        "cuisine": "Italian",
        "tags": ["pasta", "vegetarian", "quick meals"],
        "source_url": "https://example.com/tomato-pasta"
    }
]

@pytest.fixture(scope="module")
def dynamodb_table():
    """Create a test DynamoDB table using moto."""
    with mock_aws():
        # Create mock DynamoDB client
        dynamodb = boto3.resource("dynamodb", region_name="us-west-1")
        
        # Create test table
        table = dynamodb.create_table(
            TableName="test-recipes",
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        yield table
        
        # Cleanup happens automatically with moto

@pytest.fixture(scope="module")
async def pinecone_index():
    """Initialize test Pinecone index."""
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        pytest.skip("Pinecone API key not found. Skipping tests that require Pinecone.")
    
    index_name = os.getenv("PINECONE_INDEX_NAME")
    if not index_name:
        pytest.skip("Pinecone index name not found. Skipping tests that require Pinecone.")
    
    print(f"\nDebug: Using index name: {index_name}")
    
    # Initialize Pinecone with test credentials
    pc = Pinecone(api_key=api_key)
    
    # List available indexes
    available_indexes = pc.list_indexes()
    print(f"Debug: Available indexes: {available_indexes}")
    
    # Use the existing index
    available_index_names = [idx["name"] for idx in available_indexes]
    if index_name not in available_index_names:
        pytest.skip(f"Pinecone index {index_name} does not exist. Available indexes: {available_index_names}")
    
    index = pc.Index(index_name)
    print(f"Debug: Successfully connected to index {index_name}")
    
    yield index
    
    # Don't delete the index since we didn't create it
    # await pc.delete_index(index_name)

@pytest.fixture
async def services(dynamodb_table, pinecone_index):
    """Initialize services with test configurations."""
    # Initialize services with test configs
    dynamodb_service = DynamoDBService()
    
    langchain_service = LangChainService(
        index_name="test-recipes"
    )
    
    recipe_service = RecipeIngestionService(
        dynamodb_service=dynamodb_service,
        langchain_service=langchain_service
    )
    
    yield recipe_service, dynamodb_service, langchain_service

@pytest.mark.asyncio
async def test_full_recipe_ingestion_flow(services):
    """Test the complete flow of recipe ingestion and retrieval."""
    recipe_service, dynamodb_service, langchain_service = services
    test_recipe = TEST_RECIPES[0]
    
    # Test recipe ingestion
    recipe_id = await recipe_service.process_recipe(test_recipe, RecipeSource.TEST.value)
    assert recipe_id is not None
    
    # Verify recipe in DynamoDB
    stored_recipe = await dynamodb_service.get_recipe(recipe_id)
    assert stored_recipe is not None
    assert stored_recipe.title == test_recipe["title"]
    assert len(stored_recipe.ingredients) == len(test_recipe["ingredients"])
    
    # Test recipe similarity search
    similar_recipes = await langchain_service.similar_recipes_query(
        query="chocolate chip cookie recipe",
        k=1
    )
    assert len(similar_recipes) > 0
    assert similar_recipes[0]["score"] > 0.5  # Should have high relevance
    
    # Verify recipe metadata in search results
    assert similar_recipes[0]["metadata"]["title"] == test_recipe["title"]

@pytest.mark.asyncio
async def test_batch_recipe_processing(services):
    """Test processing multiple recipes in batch."""
    recipe_service, dynamodb_service, _ = services
    
    # Process all test recipes
    recipe_ids = await recipe_service.batch_process_recipes(
        TEST_RECIPES,
        RecipeSource.TEST.value
    )
    
    assert len(recipe_ids) == len(TEST_RECIPES)
    
    # Verify all recipes are stored
    for recipe_id in recipe_ids:
        stored_recipe = await dynamodb_service.get_recipe(recipe_id)
        assert stored_recipe is not None

@pytest.mark.asyncio
async def test_recipe_updates(services):
    """Test updating existing recipes."""
    recipe_service, dynamodb_service, langchain_service = services
    test_recipe = TEST_RECIPES[0].copy()
    
    # First insertion
    recipe_id = await recipe_service.process_recipe(test_recipe, RecipeSource.TEST.value)
    
    # Modify recipe
    test_recipe["title"] = "Updated Chocolate Chip Cookies"
    test_recipe["ingredients"].append({"text": "1 cup nuts (optional)"})
    
    # Update recipe
    updated_id = await recipe_service.process_recipe(test_recipe, RecipeSource.TEST.value)
    assert updated_id == recipe_id  # Should use same ID
    
    # Verify updates in DynamoDB
    updated_recipe = await dynamodb_service.get_recipe(recipe_id)
    assert updated_recipe.title == "Updated Chocolate Chip Cookies"
    assert len(updated_recipe.ingredients) == len(test_recipe["ingredients"])
    
    # Verify updates in vector search
    similar_recipes = await langchain_service.similar_recipes_query(
        query="chocolate chip cookies with nuts",
        k=1
    )
    assert similar_recipes[0]["metadata"]["title"] == "Updated Chocolate Chip Cookies"

@pytest.mark.asyncio
async def test_recipe_deletion(services):
    """Test recipe deletion across services."""
    recipe_service, dynamodb_service, langchain_service = services
    test_recipe = TEST_RECIPES[1]  # Use pasta recipe
    
    # Insert recipe
    recipe_id = await recipe_service.process_recipe(test_recipe, RecipeSource.TEST.value)
    
    # Verify insertion
    stored_recipe = await dynamodb_service.get_recipe(recipe_id)
    assert stored_recipe is not None
    
    # Delete recipe
    success = await recipe_service.delete_recipe(recipe_id)
    assert success is True
    
    # Verify deletion from DynamoDB
    deleted_recipe = await dynamodb_service.get_recipe(recipe_id)
    assert deleted_recipe is None
    
    # Verify deletion from vector search
    similar_recipes = await langchain_service.similar_recipes_query(
        query="tomato pasta recipe",
        k=1
    )
    assert not any(r["metadata"].get("id") == recipe_id for r in similar_recipes)

@pytest.mark.asyncio
async def test_error_handling_and_consistency(services):
    """Test error handling and data consistency across services."""
    recipe_service, dynamodb_service, langchain_service = services
    test_recipe = TEST_RECIPES[0]
    
    # Test with invalid recipe data
    invalid_recipe = test_recipe.copy()
    invalid_recipe["ingredients"] = None  # This should cause validation error
    
    with pytest.raises(ValueError):
        await recipe_service.process_recipe(invalid_recipe, RecipeSource.TEST.value)
    
    # Verify no partial data was stored
    recipes = await dynamodb_service.list_recipes()
    assert not any(r.title == invalid_recipe["title"] for r in recipes)
    
    similar_recipes = await langchain_service.similar_recipes_query(
        query=invalid_recipe["title"],
        k=1
    )
    assert not any(r["metadata"].get("title") == invalid_recipe["title"] 
                  for r in similar_recipes) 