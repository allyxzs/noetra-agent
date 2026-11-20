"""Orquestrador principal do agente Noetra."""

from __future__ import annotations

from pathlib import Path

from .config import NoetraConfig
from .models import ContextReport, ProjectMetadata, SearchResult
from .retriever import ContextRetriever
from .scanner import scan_project
from .synthesizer import ContextSynthesizer


class NoetraAgent:
    """Agente responsável por indexar, pesquisar e sintetizar contextos de projetos."""

    def __init__(self, project_path: str | Path = ".", config: NoetraConfig | None = None) -> None:
        self.project_path = Path(project_path).resolve()
        self.config = config or NoetraConfig()
        self.retriever = ContextRetriever()
        self.synthesizer = ContextSynthesizer(self.config)

    def index_project(self, persist: bool = True) -> ProjectMetadata:
        """Escaneia o projeto, constrói o índice e opcionalmente salva em cache."""
        chunks, metadata = scan_project(self.project_path, self.config)
        self.retriever.build_index(chunks, metadata)
        if persist:
            self.retriever.save(self.config.index_file_path(self.project_path))
        return metadata

    def ensure_indexed(self) -> ProjectMetadata:
        """Carrega o índice em cache ou indexa o projeto automaticamente."""
        if self.retriever.chunks and self.retriever.metadata:
            return self.retriever.metadata

        index_path = self.config.index_file_path(self.project_path)
        if self.retriever.load(index_path) and self.retriever.metadata:
            return self.retriever.metadata

        return self.index_project(persist=True)

    def search(
        self,
        query: str,
        top_k: int = 5,
        path_filter: str | None = None,
        reindex: bool = False,
    ) -> list[SearchResult]:
        """Pesquisa trechos relevantes no contexto do projeto."""
        if reindex:
            self.index_project(persist=True)
        else:
            self.ensure_indexed()
        return self.retriever.search(query=query, top_k=top_k, path_filter=path_filter)

    def ask(
        self,
        question: str,
        top_k: int = 5,
        path_filter: str | None = None,
        reindex: bool = False,
    ) -> ContextReport:
        """Recupera evidências do projeto e sintetiza uma resposta contextualizada."""
        results = self.search(
            query=question,
            top_k=top_k,
            path_filter=path_filter,
            reindex=reindex,
        )
        answer, provider_used = self.synthesizer.synthesize(question, results)
        return ContextReport(
            query=question,
            answer=answer,
            results=results,
            provider_used=provider_used,
            project_metadata=self.retriever.metadata,
        )

    def inspect_project(self, reindex: bool = True) -> ProjectMetadata:
        """Retorna um panorama estrutural do projeto (arquivos, stack e extensões)."""
        if reindex:
            return self.index_project(persist=True)
        return self.ensure_indexed()
