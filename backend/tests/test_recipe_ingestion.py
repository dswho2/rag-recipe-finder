import pytest
from unittest.mock import Mock, patch
from app.services.recipe_ingestion_service import RecipeIngestionService, RecipeSource
from app.services.dynamodb_service import DynamoDBService
from app.services.langchain_service import LangChainService
from app.core.schemas import Recipe, Ingredient, RecipeStep

# Test data
TEST_RECIPE_RAW = {
    "id": "test123",
    "title": "Test Recipe",
    "description": "A test recipe",
    "ingredients": [
        {"text": "1 cup flour"},
        {"text": "2 large eggs"},
        {"text": "1/2 tsp salt"}
    ],
    "instructions": [
        {"text": "Mix flour and salt"},
        {"text": "Add eggs and stir"}
    ],
    "cooking_time": 30,
    "prep_time": 15,
    "servings": 4,
    "cuisine": "Test Cuisine",
    "tags": ["test", "example"],
    "url": "https://example.com/recipe"
}

@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB service."""
    with patch('app.services.recipe_ingestion_service.DynamoDBService') as mock:
        instance = mock.return_value
        instance.store_recipe = Mock()
        instance.delete_recipe = Mock()
        yield instance

@pytest.fixture
def mock_langchain():
    """Mock LangChain service."""
    with patch('app.services.recipe_ingestion_service.LangChainService') as mock:
        instance = mock.return_value
        # Create an async mock for store_recipe_embedding
        async def async_store_recipe_embedding(*args, **kwargs):
            return None
        instance.store_recipe_embedding = Mock(side_effect=async_store_recipe_embedding)
        instance.vector_store = Mock()
        instance.vector_store.adelete = Mock()
        yield instance

@pytest.fixture
def ingestion_service(mock_dynamodb, mock_langchain):
    """Create RecipeIngestionService with mocked dependencies."""
    return RecipeIngestionService()

@pytest.mark.asyncio
async def test_successful_recipe_ingestion(ingestion_service, mock_dynamodb, mock_langchain):
    """Test successful recipe ingestion flow."""
    # Configure mocks for success
    mock_dynamodb.store_recipe.return_value = "test-id"
    # No need to set return_value for store_recipe_embedding as it's handled in the fixture
    
    # Process recipe
    recipe_id = await ingestion_service.process_recipe(TEST_RECIPE_RAW, RecipeSource.USER.value)
    
    # Verify success
    assert recipe_id is not None
    assert recipe_id.startswith("user-")
    assert mock_dynamodb.store_recipe.called
    assert mock_langchain.store_recipe_embedding.called

@pytest.mark.asyncio
async def test_dynamodb_failure(ingestion_service, mock_dynamodb, mock_langchain):
    """Test handling of DynamoDB storage failure."""
    # Configure DynamoDB to fail
    mock_dynamodb.store_recipe.side_effect = Exception("DynamoDB error")
    
    # Process recipe
    recipe_id = await ingestion_service.process_recipe(TEST_RECIPE_RAW, RecipeSource.USER.value)
    
    # Verify failure handling
    assert recipe_id is None
    assert mock_dynamodb.store_recipe.called
    assert not mock_langchain.store_recipe_embedding.called  # Should not reach Pinecone
    assert not mock_dynamodb.delete_recipe.called  # No cleanup needed

@pytest.mark.asyncio
async def test_pinecone_failure_with_cleanup(ingestion_service, mock_dynamodb, mock_langchain):
    """Test handling of Pinecone storage failure with DynamoDB cleanup."""
    # Configure DynamoDB success but Pinecone failure
    mock_dynamodb.store_recipe.return_value = "test-id"
    # Create an async mock that raises an exception
    async def async_store_recipe_embedding_error(*args, **kwargs):
        raise Exception("Pinecone error")
    mock_langchain.store_recipe_embedding.side_effect = async_store_recipe_embedding_error
    
    # Process recipe
    recipe_id = await ingestion_service.process_recipe(TEST_RECIPE_RAW, RecipeSource.USER.value)
    
    # Verify failure handling and cleanup
    assert recipe_id is None
    assert mock_dynamodb.store_recipe.called
    assert mock_langchain.store_recipe_embedding.called
    assert mock_dynamodb.delete_recipe.called  # Should attempt cleanup

@pytest.mark.asyncio
async def test_cleanup_failure(ingestion_service, mock_dynamodb, mock_langchain):
    """Test handling of cleanup failure after Pinecone failure."""
    # Configure cascading failures
    mock_dynamodb.store_recipe.return_value = "test-id"
    # Create an async mock that raises an exception
    async def async_store_recipe_embedding_error(*args, **kwargs):
        raise Exception("Pinecone error")
    mock_langchain.store_recipe_embedding.side_effect = async_store_recipe_embedding_error
    mock_dynamodb.delete_recipe.side_effect = Exception("Cleanup error")
    
    # Process recipe
    recipe_id = await ingestion_service.process_recipe(TEST_RECIPE_RAW, RecipeSource.USER.value)
    
    # Verify error handling
    assert recipe_id is None
    assert mock_dynamodb.store_recipe.called
    assert mock_langchain.store_recipe_embedding.called
    assert mock_dynamodb.delete_recipe.called

@pytest.mark.asyncio
async def test_recipe_id_generation(ingestion_service):
    """Test recipe ID generation for different sources."""
    # Test various sources
    sources = {
        RecipeSource.RECIPE1M.value: "recipe1m-",
        RecipeSource.USER.value: "user-",
        RecipeSource.API.value: "api-",
        RecipeSource.ADMIN.value: "admin-",
        "allrecipes": "web-allrecipes-",
        "unknown": "other-unknown-"
    }
    
    for source, expected_prefix in sources.items():
        recipe_id = ingestion_service.generate_recipe_id(source, "test123")
        assert recipe_id.startswith(expected_prefix)
        assert recipe_id.islower()  # Verify lowercase
        assert "-" in recipe_id  # Verify proper formatting

@pytest.mark.asyncio
async def test_data_normalization(ingestion_service):
    """Test ingredient and instruction normalization."""
    # Test ingredient normalization
    ingredient = {"text": "1 Cup Test Ingredient"}
    normalized = ingestion_service.normalize_ingredient(ingredient)
    assert normalized.quantity == 1.0
    assert normalized.unit == "cup"
    assert normalized.name == "test ingredient"
    
    # Test instruction normalization
    instruction = {"text": "Test Step"}
    normalized = ingestion_service.normalize_instruction(instruction, 1)
    assert normalized.step_number == 1
    assert normalized.text == "Test Step"

@pytest.mark.asyncio
async def test_batch_processing(ingestion_service, mock_dynamodb, mock_langchain):
    """Test batch processing of recipes."""
    # Configure mocks for mixed success/failure
    mock_dynamodb.store_recipe.side_effect = [None, Exception("Error"), None]
    
    # Process batch of recipes
    recipes = [TEST_RECIPE_RAW.copy() for _ in range(3)]
    successful_ids = await ingestion_service.batch_process_recipes(recipes, RecipeSource.USER.value)
    
    # Verify batch processing
    assert len(successful_ids) < len(recipes)  # Some should fail
    assert mock_dynamodb.store_recipe.call_count == 3 