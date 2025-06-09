# backend/app/services/dynamodb_service.py

import boto3
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.schemas import Recipe
import json

class DynamoDBService:
    def __init__(self):
        """Initialize DynamoDB client with configuration."""
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            endpoint_url=settings.DYNAMODB_ENDPOINT_URL
        )
        self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
    
    def ensure_table_exists(self):
        """Ensure the recipes table exists with correct schema."""
        try:
            self.table = self.dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
            self.table.load()
        except self.dynamodb.meta.client.exceptions.ResourceNotFoundException:
            # Create table with hash index
            self.table = self.dynamodb.create_table(
                TableName=settings.DYNAMODB_TABLE_NAME,
                KeySchema=[
                    {'AttributeName': 'recipe_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'recipe_id', 'AttributeType': 'S'},
                    {'AttributeName': 'recipe_hash', 'AttributeType': 'S'}
                ],
                GlobalSecondaryIndexes=[
                    {
                        'IndexName': 'recipe_hash_index',
                        'KeySchema': [
                            {'AttributeName': 'recipe_hash', 'KeyType': 'HASH'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'},
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 5,
                            'WriteCapacityUnits': 5
                        }
                    }
                ],
                ProvisionedThroughput={
                    'ReadCapacityUnits': 5,
                    'WriteCapacityUnits': 5
                }
            )
            self.table.wait_until_exists()
    
    def _recipe_to_item(self, recipe: Recipe) -> Dict[str, Any]:
        """Convert Recipe model to DynamoDB item."""
        # Convert complex types to strings to ensure DynamoDB compatibility
        ingredients_str = json.dumps([{
            'text': str(ing.text),
            'name': str(ing.name),
            'quantity': str(ing.quantity) if ing.quantity is not None else None,
            'unit': str(ing.unit) if ing.unit is not None else None
        } for ing in recipe.ingredients])
        
        instructions_str = json.dumps([{
            'step_number': str(step.step_number),
            'text': str(step.text)
        } for step in recipe.instructions])
        
        # Build item with proper type handling
        item = {
            'recipe_id': str(recipe.id),  # Partition key
            'recipe_hash': str(recipe.recipe_hash),  # For duplicate detection
            'title': str(recipe.title),
            'description': str(recipe.description) if recipe.description else None,
            'ingredients': ingredients_str,
            'instructions': instructions_str,
            'cooking_time': str(recipe.cooking_time) if recipe.cooking_time is not None else None,
            'prep_time': str(recipe.prep_time) if recipe.prep_time is not None else None,
            'servings': str(recipe.servings) if recipe.servings is not None else None,
            'cuisine': str(recipe.cuisine) if recipe.cuisine else None,
            'tags': list(map(str, recipe.tags)) if recipe.tags else [],
            'source': str(recipe.source) if recipe.source else None,
            'source_url': str(recipe.source_url) if recipe.source_url else None
        }
        
        # Remove None values as DynamoDB doesn't support them
        return {k: v for k, v in item.items() if v is not None}
    
    def _item_to_recipe(self, item: Dict[str, Any]) -> Recipe:
        """Convert DynamoDB item back to Recipe model with proper type handling."""
        # Parse JSON strings back to dictionaries
        ingredients = json.loads(item['ingredients']) if 'ingredients' in item else []
        instructions = json.loads(item['instructions']) if 'instructions' in item else []
        
        # Convert string numbers back to integers where needed
        recipe_data = {
            'id': item['recipe_id'],  # Map from recipe_id back to id
            'title': item['title'],
            'description': item.get('description'),
            'ingredients': ingredients,
            'instructions': instructions,
            'cooking_time': int(item['cooking_time']) if 'cooking_time' in item else None,
            'prep_time': int(item['prep_time']) if 'prep_time' in item else None,
            'servings': int(item['servings']) if 'servings' in item else None,
            'cuisine': item.get('cuisine'),
            'tags': item.get('tags', []),
            'source': item.get('source'),
            'source_url': item.get('source_url'),
            'recipe_hash': item['recipe_hash']  # Add the hash when converting back
        }
        return Recipe(**recipe_data)
    
    def store_recipe(self, recipe: Recipe) -> str:
        """Store a recipe in DynamoDB."""
        item = self._recipe_to_item(recipe)
        self.table.put_item(Item=item)
        return item['recipe_id']
    
    def get_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Retrieve a recipe from DynamoDB by ID."""
        response = self.table.get_item(Key={'recipe_id': str(recipe_id)})
        item = response.get('Item')
        if item:
            return self._item_to_recipe(item)
        return None
    
    def delete_recipe(self, recipe_id: str) -> bool:
        """Delete a recipe from DynamoDB."""
        try:
            # Check if recipe exists first
            exists_response = self.table.get_item(Key={'recipe_id': str(recipe_id)})
            if 'Item' not in exists_response:
                return False  # Recipe doesn't exist
            
            # Delete the recipe
            self.table.delete_item(Key={'recipe_id': str(recipe_id)})
            
            # Verify deletion
            verify_response = self.table.get_item(Key={'recipe_id': str(recipe_id)})
            return 'Item' not in verify_response
            
        except Exception as e:
            print(f"Error deleting recipe: {str(e)}")
            return False
    
    def update_recipe(self, recipe: Recipe) -> bool:
        """Update an existing recipe in DynamoDB."""
        try:
            item = self._recipe_to_item(recipe)
            self.table.put_item(Item=item)
            return True
        except Exception:
            return False
    
    def list_recipes(self, limit: int = 100) -> List[Recipe]:
        """List recipes from DynamoDB with pagination."""
        response = self.table.scan(Limit=limit)
        items = response.get('Items', [])
        return [self._item_to_recipe(item) for item in items]
    
    async def get_recipe_by_hash(self, recipe_hash: str) -> Optional[Recipe]:
        """Get a recipe by its content hash."""
        response = self.table.query(
            IndexName='recipe_hash_index',
            KeyConditionExpression='recipe_hash = :hash',
            ExpressionAttributeValues={':hash': recipe_hash}
        )
        
        items = response.get('Items', [])
        if not items:
            return None
            
        return self._item_to_recipe(items[0]) 

    def store_recipes_batch(self, recipes: List[Recipe]) -> List[str]:
        from boto3.dynamodb.conditions import Key
        import time

        client = self.table.meta.client
        table_name = self.table.name

        def chunked(iterable, size):
            for i in range(0, len(iterable), size):
                yield iterable[i:i + size]

        stored_ids = []
        for batch in chunked(recipes, 25):
            request_items = [
                {'PutRequest': {'Item': self._recipe_to_item(recipe)}}
                for recipe in batch
            ]
            batch_request = {table_name: request_items}
            
            backoff = 2
            while True:
                response = client.batch_write_item(RequestItems=batch_request)
                unprocessed = response.get('UnprocessedItems', {})
                if not unprocessed:
                    break
                batch_request = unprocessed
                time.sleep(backoff)
                backoff = min(backoff * 2, 32)  # cap at 32 seconds

            stored_ids.extend([recipe.id for recipe in batch])
            time.sleep(1)

        return stored_ids
