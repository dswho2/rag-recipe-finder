import boto3
import sys
import os
import time

# Add the backend directory to the Python path so we can import our app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def reset_dynamodb_table():
    """Delete and recreate the DynamoDB table."""
    print("Initializing DynamoDB client...")
    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        endpoint_url=settings.DYNAMODB_ENDPOINT_URL
    )
    
    table = dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
    
    try:
        print(f"Deleting table {settings.DYNAMODB_TABLE_NAME}...")
        table.delete()
        print("Waiting for table deletion...")
        table.wait_until_not_exists()
    except Exception as e:
        print(f"Table deletion failed (this is okay if the table didn't exist): {str(e)}")
    
    print("Table deleted successfully or didn't exist.")
    print("The table will be recreated with the new schema when you run the process_csv script.")

if __name__ == "__main__":
    reset_dynamodb_table() le has been deleted successfully. Now let's run the CSV processing script again, which will create the table with the new schema that includes the recipe hash index: