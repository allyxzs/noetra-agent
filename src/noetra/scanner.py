"""Scanner de projetos, detecção de stack e fragmentação em chunks."""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

from .config import NoetraConfig
from .models import DocumentChunk, ProjectMetadata

SYMBOL_PATTERNS = [
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*="),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*#{1,3}\s+(.+)"),
]

STACK_INDICATORS: dict[str, str] = {
    "package.json": "Node.js / JavaScript",
    "tsconfig.json": "TypeScript",
    "next.config.js": "Next.js",
    "next.config.mjs": "Next.js",
    "next.config.ts": "Next.js",
    "pyproject.toml": "Python",
    "requirements.txt": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java / Kotlin (Gradle)",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
}

KEY_FILE_NAMES = {
    "README.md",
    "ARCHITECTURE.md",
    "CONTRIBUTING.md",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    ".env.example",
}


def extract_symbols(lines: list[str]) -> list[str]:
    """Extrai nomes de funções, classes, tipos e headings de um trecho."""
    symbols: list[str] = []
    seen: set[str] = set()
    for line in lines:
        for pattern in SYMBOL_PATTERNS:
            match = pattern.match(line)
            if match:
                symbol = match.group(1).strip()
                if symbol and symbol not in seen:
                    seen.add(symbol)
                    symbols.append(symbol)
                break
    return symbols


def is_allowed_file(path: Path, config: NoetraConfig) -> bool:
    """Verifica se o arquivo deve ser indexado."""
    if path.name in KEY_FILE_NAMES or path.name == "Makefile":
        return True
    if path.suffix.lower() in config.allowed_extensions:
        return True
    return False


def scan_project(root_path: str | Path, config: NoetraConfig) -> tuple[list[DocumentChunk], ProjectMetadata]:
    """Percorre o diretório do projeto e gera chunks indexáveis + metadados."""
    root = Path(root_path).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Diretório de projeto não encontrado: {root}")

    chunks: list[DocumentChunk] = []
    extensions_counter: Counter[str] = Counter()
    detected_stack: set[str] = set()
    key_files: list[str] = []
    indexed_files = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in config.ignored_dirs)
        current_dir = Path(dirpath)

        for filename in sorted(filenames):
            file_path = current_dir / filename
            rel_path = file_path.relative_to(root).as_posix()

            if filename in STACK_INDICATORS:
                detected_stack.add(STACK_INDICATORS[filename])
            if filename in KEY_FILE_NAMES:
                key_files.append(rel_path)

            if not is_allowed_file(file_path, config):
                continue

            try:
                if file_path.stat().st_size > config.max_file_size_bytes:
                    continue
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            if not text.strip():
                continue

            indexed_files += 1
            ext = file_path.suffix.lower() or filename
            extensions_counter[ext] += 1

            lines = text.splitlines()
            step = max(1, config.chunk_size_lines - config.chunk_overlap_lines)

            for start_idx in range(0, len(lines), step):
                end_idx = min(len(lines), start_idx + config.chunk_size_lines)
                slice_lines = lines[start_idx:end_idx]
                content = "\n".join(slice_lines).strip()
                if not content:
                    continue

                chunk_id = f"{rel_path}:{start_idx + 1}-{end_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        file_path=rel_path,
                        start_line=start_idx + 1,
                        end_line=end_idx,
                        content=content,
                        symbols=extract_symbols(slice_lines),
                    )
                )
                if end_idx >= len(lines):
                    break

    metadata = ProjectMetadata(
        root_path=str(root),
        total_files=indexed_files,
        total_chunks=len(chunks),
        detected_stack=sorted(detected_stack),
        extensions_count=dict(extensions_counter.most_common()),
        key_files=sorted(key_files),
    )
    return chunks, metadata
