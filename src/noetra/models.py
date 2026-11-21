"""Modelos de dados estruturados usados pelo Noetra."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DocumentChunk:
    """Representa um trecho indexado de um arquivo do projeto."""

    chunk_id: str
    file_path: str
    start_line: int
    end_line: int
    content: str
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        return cls(**data)


@dataclass
class SearchResult:
    """Resultado ranqueado de uma busca de contexto."""

    chunk: DocumentChunk
    score: float
    matched_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.chunk.file_path,
            "start_line": self.chunk.start_line,
            "end_line": self.chunk.end_line,
            "score": round(self.score, 4),
            "matched_terms": self.matched_terms,
            "symbols": self.chunk.symbols,
            "content": self.chunk.content,
        }


@dataclass
class ProjectMetadata:
    """Resumo estrutural de um projeto escaneado."""

    root_path: str
    total_files: int
    total_chunks: int
    detected_stack: list[str] = field(default_factory=list)
    extensions_count: dict[str, int] = field(default_factory=dict)
    key_files: list[str] = field(default_factory=list)
    indexed_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextReport:
    """Resposta consolidada do agente Noetra para uma consulta."""

    query: str
    answer: str
    results: list[SearchResult]
    provider_used: str
    project_metadata: ProjectMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        meta_dict = self.project_metadata.to_dict() if self.project_metadata else None
        return {
            "query": self.query,
            "answer": self.answer,
            "provider_used": self.provider_used,
            "results": [r.to_dict() for r in self.results],
            "project_metadata": meta_dict,
        }
