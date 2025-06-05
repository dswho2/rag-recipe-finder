from fastapi import FastAPI
from mangum import Mangum

from app.core.config import settings
from app.api.recipes import router as recipes_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.include_router(recipes_router, prefix="/api/recipes")

# Handler for AWS Lambda
handler = Mangum(app)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 