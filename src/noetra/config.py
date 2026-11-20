"""Configurações do agente Noetra."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IGNORED_DIRS: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".noetra",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "coverage",
    "target",
    ".idea",
    ".vscode",
}

DEFAULT_ALLOWED_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
    ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml",
    ".ini", ".cfg", ".env.example", ".html", ".css", ".scss",
    ".sql", ".sh", ".bash", ".zsh", ".ps1",
    ".go", ".rs", ".java", ".kt", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".glsl", ".wgsl",
}


@dataclass
class NoetraConfig:
    """Configuração de indexação, busca e síntese do Noetra."""

    chunk_size_lines: int = 40
    chunk_overlap_lines: int = 8
    max_file_size_bytes: int = 512 * 1024  # 512 KB
    cache_dir_name: str = ".noetra"
    ignored_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_IGNORED_DIRS))
    allowed_extensions: set[str] = field(default_factory=lambda: set(DEFAULT_ALLOWED_EXTENSIONS))

    # LLM Synthesis settings
    llm_provider: str = field(default_factory=lambda: os.getenv("NOETRA_LLM_PROVIDER", "none").lower())
    llm_model: str = field(default_factory=lambda: os.getenv("NOETRA_LLM_MODEL", "llama3.2"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    llm_timeout_seconds: int = 45

    def index_file_path(self, root: Path) -> Path:
        return root / self.cache_dir_name / "index.json"
