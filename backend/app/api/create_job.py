# app/api/create_job.py

import uuid
import time
import boto3
from fastapi import APIRouter
from pydantic import BaseModel

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("recipe-jobs")
router = APIRouter()

class JobRequest(BaseModel):
    ingredients: list[str]

@router.post("/generate-recipe-job")
async def create_recipe_job(request: JobRequest):
    job_id = str(uuid.uuid4())
    ttl = int(time.time()) + 3600  # 1 hour from now

    item = {
        "job_id": job_id,
        "status": "pending",
        "input": request.dict(),
        "created_at": int(time.time()),
        "expires_at": ttl
    }

    table.put_item(Item=item)
    return {"job_id": job_id}
