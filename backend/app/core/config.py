from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Recipe Finder"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: str
    PINECONE_INDEX_NAME: str
    
    # AWS
    AWS_REGION: str = "us-east-1"
    DYNAMODB_TABLE_NAME: str = "recipes"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 