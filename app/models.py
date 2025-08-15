from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    job_id: str
    status: str


class ResultResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[str] = None
