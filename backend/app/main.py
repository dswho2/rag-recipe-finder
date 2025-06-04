from fastapi import FastAPI
from mangum import Mangum

from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# Handler for AWS Lambda
handler = Mangum(app)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 