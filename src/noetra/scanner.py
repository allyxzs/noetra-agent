"""Scanner de projetos, suporte a .gitignore, detecção de stack e chunks."""

from __future__ import annotations

import fnmatch
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
    re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_][A-Za-z0-9_]*)"),
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


def load_gitignore_patterns(root: Path) -> list[str]:
    """Carrega padrões básicos do .gitignore da raiz do projeto."""
    gitignore = root / ".gitignore"
    if not gitignore.exists() or not gitignore.is_file():
        return []

    patterns: list[str] = []
    for raw in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def is_ignored_by_patterns(rel_path: str, patterns: list[str]) -> bool:
    """Verifica se um caminho relativo casa com algum padrão do .gitignore."""
    parts = rel_path.split("/")
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(parts[-1], pattern):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in parts[:-1]):
            return True
    return False


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


def scan_project(
    root_path: str | Path,
    config: NoetraConfig,
) -> tuple[list[DocumentChunk], ProjectMetadata]:
    """Percorre o diretório do projeto e gera chunks indexáveis + metadados."""
    root = Path(root_path).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Diretório de projeto não encontrado: {root}")

    gitignore_patterns = load_gitignore_patterns(root) if config.respect_gitignore else []
    chunks: list[DocumentChunk] = []
    extensions_counter: Counter[str] = Counter()
    detected_stack: set[str] = set()
    key_files: list[str] = []
    indexed_files_list: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath)
        filtered_dirs: list[str] = []
        for d in sorted(dirnames):
            if d in config.ignored_dirs:
                continue
            rel_dir = (current_dir / d).relative_to(root).as_posix()
            if gitignore_patterns and is_ignored_by_patterns(rel_dir, gitignore_patterns):
                continue
            filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        for filename in sorted(filenames):
            file_path = current_dir / filename
            rel_path = file_path.relative_to(root).as_posix()

            if gitignore_patterns and is_ignored_by_patterns(rel_path, gitignore_patterns):
                continue

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

            indexed_files_list.append(rel_path)
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
        total_files=len(indexed_files_list),
        total_chunks=len(chunks),
        detected_stack=sorted(detected_stack),
        extensions_count=dict(extensions_counter.most_common()),
        key_files=sorted(key_files),
        indexed_files=indexed_files_list,
    )
    return chunks, metadata
