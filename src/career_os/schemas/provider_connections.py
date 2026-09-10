"""Schemas for account-owned OpenAI-compatible connections."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProviderConnectionCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    provider_type: str = Field(default="openai_compatible", min_length=1, max_length=32)
    base_url: str = Field(min_length=1, max_length=2048)
    api_key: str | None = Field(default=None, max_length=4096)
    model: str = Field(min_length=1, max_length=255)
    enabled: bool = True


class ProviderConnectionUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    provider_type: str | None = Field(default=None, min_length=1, max_length=32)
    base_url: str | None = Field(default=None, max_length=2048)
    api_key: str | None = Field(default=None, max_length=4096)
    model: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None


class ProviderConnectionResponse(BaseModel):
    id: int
    display_name: str
    provider_type: str
    base_url: str
    model: str
    enabled: bool
    api_key_configured: bool
    created_at: datetime
    updated_at: datetime


class ProviderConnectionListResponse(BaseModel):
    connections: list[ProviderConnectionResponse]


class ProviderModelsResponse(BaseModel):
    models: list[str]


class ProviderTestResponse(BaseModel):
    success: bool
    message: str
    models: list[str] = Field(default_factory=list)


class ProviderCompletionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=100_000)
    model: str | None = Field(default=None, min_length=1, max_length=255)


class ProviderCompletionResponse(BaseModel):
    content: str
    model: str
