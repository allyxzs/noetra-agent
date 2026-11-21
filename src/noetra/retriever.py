"""Motor de recuperação BM25 com normalização de acentos e boost estrutural."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .models import DocumentChunk, ProjectMetadata, SearchResult

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_À-ÖØ-öø-ÿ]+")

STOPWORDS: set[str] = {
    "a", "o", "as", "os", "de", "do", "da", "dos", "das", "em", "no", "na",
    "nos", "nas", "para", "por", "com", "sem", "um", "uma", "e", "ou", "que",
    "como", "onde", "qual", "quais", "fica", "ficam", "sobre", "the", "an",
    "of", "to", "in", "on", "for", "with", "and", "or", "is", "are", "how",
    "where", "what", "this", "that",
}


def strip_accents(text: str) -> str:
    """Remove diacríticos para permitir busca insensível a acentuação."""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def tokenize(text: str) -> list[str]:
    """Tokeniza texto dividindo camelCase, snake_case e normalizando acentos."""
    raw_tokens = TOKEN_PATTERN.findall(text)
    tokens: list[str] = []
    for raw in raw_tokens:
        camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
        for part in re.split(r"[\s_]+", camel_split):
            low = strip_accents(part).lower().strip()
            if len(low) >= 2 and low not in STOPWORDS:
                tokens.append(low)
    return tokens


class ContextRetriever:
    """Indexador e recuperador de contexto baseado em BM25."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.chunks: list[DocumentChunk] = []
        self.metadata: ProjectMetadata | None = None
        self._doc_freqs: Counter[str] = Counter()
        self._chunk_term_freqs: list[Counter[str]] = []
        self._chunk_lengths: list[int] = []
        self._avg_len: float = 1.0

    def build_index(
        self,
        chunks: list[DocumentChunk],
        metadata: ProjectMetadata | None = None,
    ) -> None:
        """Constrói o índice BM25 em memória a partir dos chunks."""
        self.chunks = chunks
        self.metadata = metadata
        self._doc_freqs = Counter()
        self._chunk_term_freqs = []
        self._chunk_lengths = []

        for chunk in chunks:
            weighted_text = f"{chunk.file_path} {' '.join(chunk.symbols)} {chunk.content}"
            terms = tokenize(weighted_text)
            tf = Counter(terms)
            self._chunk_term_freqs.append(tf)
            self._chunk_lengths.append(len(terms))
            for term in tf:
                self._doc_freqs[term] += 1

        total_len = sum(self._chunk_lengths)
        self._avg_len = (total_len / len(chunks)) if chunks else 1.0

    def search(
        self,
        query: str,
        top_k: int = 5,
        path_filter: str | None = None,
    ) -> list[SearchResult]:
        """Recupera os chunks mais relevantes para uma consulta."""
        if not self.chunks:
            return []

        query_terms = tokenize(query)
        if not query_terms:
            return []

        n_docs = len(self.chunks)
        scored: list[SearchResult] = []

        for idx, chunk in enumerate(self.chunks):
            if path_filter and path_filter.lower() not in chunk.file_path.lower():
                continue

            tf = self._chunk_term_freqs[idx]
            doc_len = self._chunk_lengths[idx] or 1
            score = 0.0
            matched: set[str] = set()

            path_tokens = set(tokenize(chunk.file_path))
            symbol_tokens = set(tokenize(" ".join(chunk.symbols)))

            for term in query_terms:
                freq = tf.get(term, 0)
                if freq > 0:
                    matched.add(term)
                    df = self._doc_freqs.get(term, 0)
                    idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                    denom = freq + self.k1 * (
                        1 - self.b + self.b * (doc_len / self._avg_len)
                    )
                    score += idf * ((freq * (self.k1 + 1)) / denom)

                if term in path_tokens:
                    score += 1.2
                    matched.add(term)
                if term in symbol_tokens:
                    score += 1.5
                    matched.add(term)

            if score > 0:
                scored.append(
                    SearchResult(
                        chunk=chunk,
                        score=score,
                        matched_terms=sorted(matched),
                    )
                )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def save(self, index_path: Path) -> None:
        """Persiste o índice e metadados em arquivo JSON."""
        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": self.metadata.to_dict() if self.metadata else None,
            "chunks": [c.to_dict() for c in self.chunks],
        }
        index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, index_path: Path) -> bool:
        """Carrega o índice salvo em disco, se existir."""
        if not index_path.exists():
            return False
        data = json.loads(index_path.read_text(encoding="utf-8"))
        chunks = [DocumentChunk.from_dict(item) for item in data.get("chunks", [])]
        raw_meta = data.get("metadata")
        metadata = ProjectMetadata(**raw_meta) if raw_meta else None
        self.build_index(chunks, metadata)
        return True
