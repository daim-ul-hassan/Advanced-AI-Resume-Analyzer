from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ThemeName = Literal["dark-ai", "gradient"]
ProviderName = Literal["gemini", "groq", "heuristic"]


class ProfilePayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    theme: ThemeName


class SessionPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=4, max_length=128)
    theme: ThemeName


class ResumeUploadResponse(BaseModel):
    filename: str
    saved_path: str
    characters: int
    message: str


class VectorBuildResponse(BaseModel):
    chunk_count: int
    message: str


class AnalysisRequest(BaseModel):
    job_description: str = Field(min_length=1)
    provider: ProviderName = "heuristic"
    gemini_key: str | None = None
    groq_key: str | None = None


class AnalysisResponse(BaseModel):
    score: int
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    matching_keywords: list[str]
    summary: str
    provider_used: str
    retrieved_chunks: list[str]


class ActivityEntry(BaseModel):
    timestamp: str
    title: str
    detail: str
