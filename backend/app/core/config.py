from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    PROJECT_NAME: str = "Recipe Finder API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # OpenAI settings
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    CHAT_MODEL: str = "gpt-4.1-mini"
    CHAT_MODEL_TEMPERATURE: float = 0.7
    
    # Pinecone settings
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "recipe-finder"
    
    # Recipe1M dataset path
    RECIPE1M_PATH: Optional[str] = None
    
    # AWS Settings
    AWS_REGION: str = "us-west-1"
    # AWS credentials - optional if using IAM roles or aws configure
    AWS_ACCESS_KEY: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    # DynamoDB settings
    DYNAMODB_TABLE_NAME: str = "recipes"
    DYNAMODB_ENDPOINT_URL: Optional[str] = None  # Set for local testing
    IS_PRODUCTION: bool = False  # Set to True in Lambda
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 