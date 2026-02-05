"""Knowledge ingestion helpers backed by Agno's knowledge base."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID


try:  # pragma: no cover - optional dep
    from agno.knowledge import Knowledge as _KnowledgeBase
except ImportError:  # pragma: no cover
    try:
        from agno.knowledge.knowledge import Knowledge as _KnowledgeBase
    except ImportError:  # pragma: no cover
        _KnowledgeBase = None  # type: ignore[assignment]


try:  # pragma: no cover - optional dep
    from agno.knowledge.content import Content
except ImportError:  # pragma: no cover
    Content = None  # type: ignore[assignment]


try:  # pragma: no cover - optional dep
    from agno.utils.string import generate_id as _generate_content_id
except ImportError:  # pragma: no cover
    _generate_content_id = None


try:  # pragma: no cover - optional dep
    from agno.knowledge.reader.pdf_reader import PDFReader
except ImportError as exc:  # pragma: no cover
    PDFReader = None  # type: ignore[assignment]
    _PDF_IMPORT_ERROR = exc
else:  # pragma: no cover
    _PDF_IMPORT_ERROR = None


try:  # pragma: no cover - optional dep
    from agno.knowledge.reader.url_reader import UrlReader
except ImportError as exc:  # pragma: no cover
    try:
        from agno.knowledge.reader.website_reader import WebsiteReader as UrlReader
    except ImportError:
        UrlReader = None  # type: ignore[assignment]
        _URL_IMPORT_ERROR = exc
    else:
        _URL_IMPORT_ERROR = None
else:  # pragma: no cover
    _URL_IMPORT_ERROR = None


try:  # pragma: no cover - optional dep
    from agno.vectordb.pgvector import PgVector
except ImportError as exc:  # pragma: no cover
    PgVector = None  # type: ignore[assignment]
    _PG_IMPORT_ERROR = exc
else:  # pragma: no cover
    _PG_IMPORT_ERROR = None


DATABASE_ENV_KEYS = ("DATABASE_URL", "DYNAMIC_AGENTS_DATABASE_URL")
DEFAULT_TABLE_NAME = "agent_knowledge"


@dataclass(slots=True)
class AgentKnowledge:
    """Lightweight record describing agent-linked knowledge content."""

    agent_id: UUID
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_id: str | None = None


class KnowledgeManagerError(RuntimeError):
    """Raised when the knowledge ingestion pipeline is unavailable."""


class KnowledgeManager:
    """Wrapper that manages Agno knowledge ingestion for stored agents."""

    def __init__(
        self,
        database_url: str | None = None,
        *,
        table_name: str = DEFAULT_TABLE_NAME,
        schema: str | None = None,
    ) -> None:
        if _KnowledgeBase is None:  # pragma: no cover - runtime guard
            raise KnowledgeManagerError(
                "Agno knowledge package is not installed. Install `agno` to enable ingestion.",
            )

        self._database_url = self._resolve_database_url(database_url)
        self._table_name = table_name
        self._schema = schema
        self._vector_db = self._init_vector_db()
        self._knowledge_base = _KnowledgeBase(vector_db=self._vector_db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def load_document(
        self,
        file_path: str,
        agent_id: UUID,
        *,
        metadata: Mapping[str, Any] | None = None,
        name: str | None = None,
    ) -> AgentKnowledge:
        """Load a local document into the shared vector store."""

        path = Path(file_path)
        if not path.is_file():
            raise KnowledgeManagerError(f"Document not found: {file_path}")

        merged_metadata = self._build_metadata(
            agent_id,
            source_type="file",
            metadata=metadata,
            extra={"filename": path.name},
        )

        reader = None
        if path.suffix.lower() == ".pdf":
            reader = self._get_pdf_reader()

        content_id = self._predict_content_id(path=str(path), metadata=merged_metadata)
        self._knowledge_base.insert(
            name=name or path.name,
            path=str(path),
            metadata=merged_metadata,
            reader=reader,
        )

        return AgentKnowledge(
            agent_id=agent_id,
            source=str(path),
            metadata=merged_metadata,
            content_id=content_id,
        )

    def load_url(
        self,
        url: str,
        agent_id: UUID,
        *,
        metadata: Mapping[str, Any] | None = None,
        name: str | None = None,
    ) -> AgentKnowledge:
        """Fetch and embed remote content from a URL."""

        if not url:
            raise KnowledgeManagerError("URL is required for ingestion")

        merged_metadata = self._build_metadata(
            agent_id,
            source_type="url",
            metadata=metadata,
            extra={"url": url},
        )

        reader = self._get_url_reader()
        content_id = self._predict_content_id(url=url, metadata=merged_metadata)
        self._knowledge_base.insert(
            name=name,
            url=url,
            metadata=merged_metadata,
            reader=reader,
        )

        return AgentKnowledge(
            agent_id=agent_id,
            source=url,
            metadata=merged_metadata,
            content_id=content_id,
        )

    def ingest_file(self, file_path: str, agent_id: UUID, **kwargs: Any) -> AgentKnowledge:
        """Alias maintained for API clarity."""

        return self.load_document(file_path, agent_id, **kwargs)

    def ingest_url(self, url: str, agent_id: UUID, **kwargs: Any) -> AgentKnowledge:
        """Alias maintained for API clarity."""

        return self.load_url(url, agent_id, **kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_database_url(self, explicit_url: str | None) -> str:
        if explicit_url:
            return explicit_url
        for key in DATABASE_ENV_KEYS:
            value = os.environ.get(key)
            if value:
                return value
        raise KnowledgeManagerError(
            "DATABASE_URL environment variable is not configured for the knowledge manager.",
        )

    def _prepare_pgvector_url(self, url: str) -> str:
        if url.startswith("postgresql+asyncpg://"):
            return "postgresql+psycopg://" + url[len("postgresql+asyncpg://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        return url

    def _init_vector_db(self):
        if PgVector is None:  # pragma: no cover - runtime guard
            raise KnowledgeManagerError(
                "pgvector integration is unavailable. Install `pgvector` to enable ingestion.",
            ) from _PG_IMPORT_ERROR

        pg_url = self._prepare_pgvector_url(self._database_url)
        return PgVector(table_name=self._table_name, db_url=pg_url, schema=self._schema)

    def _get_pdf_reader(self):
        if PDFReader is None:  # pragma: no cover - runtime guard
            raise KnowledgeManagerError(
                "PDF ingestion requires the optional `pypdf` dependency.",
            ) from _PDF_IMPORT_ERROR
        return PDFReader()

    def _get_url_reader(self):
        if UrlReader is None:  # pragma: no cover - runtime guard
            raise KnowledgeManagerError(
                "A URL reader is not available in the current Agno install."
            )
        return UrlReader()

    def _build_metadata(
        self,
        agent_id: UUID,
        *,
        source_type: str,
        metadata: Mapping[str, Any] | None,
        extra: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"agent_id": str(agent_id), "source_type": source_type}
        if extra:
            for key, value in extra.items():
                payload[key] = self._normalize_metadata_value(value)
        if metadata:
            for key, value in metadata.items():
                payload[key] = self._normalize_metadata_value(value)
        return payload

    def _normalize_metadata_value(self, value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        return value

    def _predict_content_id(
        self,
        *,
        path: str | None = None,
        url: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str | None:
        if Content is None or _generate_content_id is None:
            return None
        builder = getattr(self._knowledge_base, "_build_content_hash", None)
        if builder is None:
            return None

        payload = Content(path=path, url=url, metadata=dict(metadata or {}))
        payload.content_hash = builder(payload)
        return _generate_content_id(payload.content_hash)


__all__ = [
    "AgentKnowledge",
    "KnowledgeManager",
    "KnowledgeManagerError",
]
