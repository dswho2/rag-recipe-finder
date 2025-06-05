import pytest
from app.services.dynamodb_service import DynamoDBService
from app.core.schemas import Recipe, Ingredient, RecipeStep

# Use a fixed test ID for consistency
TEST_RECIPE_ID = "test-recipe-001"

@pytest.fixture(scope="module")
async def dynamo_service():
    """Fixture to provide a DynamoDB service instance."""
    service = DynamoDBService()
    await service.ensure_table_exists()
    return service

@pytest.fixture
def test_recipe():
    """Fixture to provide a test recipe."""
    return Recipe(
        id=TEST_RECIPE_ID,  # Use fixed test ID
        title="Test Recipe",
        description="A test recipe to verify DynamoDB connection",
        ingredients=[
            Ingredient(text="1 cup test ingredient", name="test ingredient", quantity=1.0, unit="cup")
        ],
        instructions=[
            RecipeStep(step_number=1, text="Test step 1")
        ],
        cuisine="Test Cuisine",
        tags=["test", "verification"]
    )

@pytest.mark.asyncio
async def test_store_recipe(dynamo_service, test_recipe):
    """Test storing a recipe in DynamoDB. Can be run independently to add a test recipe."""
    print("\nTest Recipe Details:")
    print(f"ID: {test_recipe.id}")
    print(f"Title: {test_recipe.title}")
    
    stored_id = await dynamo_service.store_recipe(test_recipe)
    assert stored_id == TEST_RECIPE_ID
    
    print(f"\nRecipe stored successfully!")
    print(f"Recipe ID: {stored_id}")
    print("You can now check the AWS console to see the item.")

@pytest.mark.asyncio
async def test_get_recipe(dynamo_service):
    """Test retrieving a recipe from DynamoDB. Can be run independently to verify a stored recipe."""
    print(f"\nAttempting to retrieve recipe with ID: {TEST_RECIPE_ID}")
    recipe = await dynamo_service.get_recipe(TEST_RECIPE_ID)
    
    assert recipe is not None, f"Recipe with ID {TEST_RECIPE_ID} should be found in DynamoDB"
    print("\nRecipe found!")
    print(f"Title: {recipe.title}")
    print(f"Description: {recipe.description}")
    print(f"Number of ingredients: {len(recipe.ingredients)}")
    print(f"First ingredient: {recipe.ingredients[0].text}")

@pytest.mark.asyncio
async def test_delete_recipe(dynamo_service):
    """Test deleting a recipe from DynamoDB. Can be run independently to delete a stored recipe."""
    print(f"\nAttempting to delete recipe with ID: {TEST_RECIPE_ID}")
    
    # First verify it exists
    recipe = await dynamo_service.get_recipe(TEST_RECIPE_ID)
    assert recipe is not None, f"Recipe with ID {TEST_RECIPE_ID} should exist before deletion"
    print("✓ Verified recipe exists")
    
    # Delete it
    delete_success = await dynamo_service.delete_recipe(TEST_RECIPE_ID)
    assert delete_success is True, "Delete operation should succeed"
    print("✓ Delete operation successful")
    
    # Verify deletion
    deleted_recipe = await dynamo_service.get_recipe(TEST_RECIPE_ID)
    assert deleted_recipe is None, "Recipe should not exist after deletion"
    print("✓ Verified recipe no longer exists")

@pytest.mark.asyncio
async def test_get_nonexistent_recipe(dynamo_service):
    """Test retrieving a non-existent recipe."""
    nonexistent_id = str(uuid.uuid4())
    recipe = await dynamo_service.get_recipe(nonexistent_id)
    assert recipe is None

@pytest.mark.asyncio
async def test_delete_nonexistent_recipe(dynamo_service):
    """Test deleting a non-existent recipe."""
    nonexistent_id = str(uuid.uuid4())
    success = await dynamo_service.delete_recipe(nonexistent_id)
    assert success is False

if __name__ == "__main__":
    pytest.main() 