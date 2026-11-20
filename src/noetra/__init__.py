"""Noetra — Agente de pesquisa de contexto de projetos e recuperação de informações."""

from .agent import NoetraAgent
from .config import NoetraConfig
from .models import ContextReport, DocumentChunk, ProjectMetadata, SearchResult

__version__ = "0.1.0"

__all__ = [
    "NoetraAgent",
    "NoetraConfig",
    "ContextReport",
    "DocumentChunk",
    "ProjectMetadata",
    "SearchResult",
    "__version__",
]
