# backend/app/main.py

from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.recipes import router as recipes_router
from app.api.create_job import router as create_job_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes_router, prefix="/api/recipes")
app.include_router(create_job_router)

# Handler for AWS Lambda
handler = Mangum(app)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 