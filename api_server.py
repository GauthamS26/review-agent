#!/usr/bin/env python3
"""FastAPI service for the code review agent."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from code_review_agent_enhanced import DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, process_code_review


class LocalReviewRequest(BaseModel):
    source_path: str = Field(..., description="Local folder path to review")
    model: str = Field(default=DEFAULT_MODEL, description="Ollama model name")
    ollama_host: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
        description="Ollama host URL",
    )
    output_file: Optional[str] = Field(
        default=None,
        description="Optional path to save full review output",
    )


class GitReviewRequest(BaseModel):
    git_url: str = Field(..., description="Git repository URL to clone and review")
    model: str = Field(default=DEFAULT_MODEL, description="Ollama model name")
    ollama_host: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
        description="Ollama host URL",
    )
    output_file: Optional[str] = Field(
        default=None,
        description="Optional path to save full review output",
    )


class ReviewResponse(BaseModel):
    source: str
    model: str
    ollama_host: str
    is_git: bool
    review: str


app = FastAPI(
    title="Code Review Agent API",
    version="1.0.0",
    description="FastAPI wrapper for the Ollama-powered code review agent.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/models/default")
def default_model() -> dict:
    return {
        "default_model": DEFAULT_MODEL,
        "default_ollama_host": os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
    }


@app.post("/review/local", response_model=ReviewResponse)
async def review_local(req: LocalReviewRequest) -> ReviewResponse:
    source = str(Path(req.source_path).resolve())
    if not Path(source).exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {source}")

    try:
        review = await run_in_threadpool(
            process_code_review,
            source,
            False,
            req.model,
            req.ollama_host,
            req.output_file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return ReviewResponse(
        source=source,
        model=req.model,
        ollama_host=req.ollama_host,
        is_git=False,
        review=review,
    )


@app.post("/review/git", response_model=ReviewResponse)
async def review_git(req: GitReviewRequest) -> ReviewResponse:
    if not (req.git_url.startswith("http://") or req.git_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="git_url must start with http:// or https://")

    try:
        review = await run_in_threadpool(
            process_code_review,
            req.git_url,
            True,
            req.model,
            req.ollama_host,
            req.output_file,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc

    return ReviewResponse(
        source=req.git_url,
        model=req.model,
        ollama_host=req.ollama_host,
        is_git=True,
        review=review,
    )
