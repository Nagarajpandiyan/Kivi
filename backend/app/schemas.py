from pydantic import BaseModel, Field


class LearnRequest(BaseModel):
    user_id: str = "user_1"
    asr: str
    formatted: str
    source_id: str | None = None


class ProcessRequest(BaseModel):
    user_id: str = "user_1"
    asr: str
    formatted: str


class DeactivateResponse(BaseModel):
    id: str
    status: str


class ImportItem(BaseModel):
    user_id: str = "user_1"
    asr: str
    formatted: str
    source_id: str | None = None
