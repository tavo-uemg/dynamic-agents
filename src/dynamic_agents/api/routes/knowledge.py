"""Knowledge ingestion HTTP endpoints."""

from __future__ import annotations

# pyright: reportUninitializedInstanceVariable=false

import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ...core.knowledge import AgentKnowledge, KnowledgeManagerError
from ..deps import KnowledgeManagerDep


router = APIRouter()


class KnowledgeIngestionResponse(BaseModel):
    """Payload returned after a successful ingestion request."""

    agent_id: UUID
    source: str
    content_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UrlIngestionRequest(BaseModel):
    """Request payload for ingesting knowledge from URLs."""

    url: str
    agent_id: UUID


def _serialize_agent_knowledge(record: AgentKnowledge) -> KnowledgeIngestionResponse:
    return KnowledgeIngestionResponse(
        agent_id=record.agent_id,
        source=record.source,
        content_id=record.content_id,
        metadata=record.metadata,
    )


async def _persist_upload(upload: UploadFile) -> Path:
    filename = upload.filename or "upload"
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        _ = temp_file.write(await upload.read())
        temp_path = Path(temp_file.name)
    await upload.close()
    return temp_path


@router.post(
    "/ingest/file",
    response_model=KnowledgeIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_file(
    agent_id: Annotated[UUID, Form(...)],
    file: Annotated[UploadFile, File(...)],
    manager: KnowledgeManagerDep,
) -> KnowledgeIngestionResponse:
    """Upload a document and ingest it into the agent knowledge base."""

    if not file.filename:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="Uploaded file must include a filename"
        )

    temp_path: Path | None = None
    try:
        temp_path = await _persist_upload(file)
        record = await run_in_threadpool(manager.load_document, str(temp_path), agent_id)
    except KnowledgeManagerError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to ingest document"
        ) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return _serialize_agent_knowledge(record)


@router.post(
    "/ingest/url",
    response_model=KnowledgeIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_url(
    payload: UrlIngestionRequest,
    manager: KnowledgeManagerDep,
) -> KnowledgeIngestionResponse:
    """Ingest the contents of a remote URL."""

    try:
        record = await run_in_threadpool(manager.load_url, payload.url, payload.agent_id)
    except KnowledgeManagerError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to ingest URL"
        ) from exc

    return _serialize_agent_knowledge(record)


__all__ = ["router"]
