"""Configurações e carregamento automático de .env do agente Noetra."""

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


def load_dotenv_file(env_path: Path) -> dict[str, str]:
    """Lê pares KEY=VALUE de um arquivo .env sem sobrescrever variáveis já definidas."""
    loaded: dict[str, str] = {}
    if not env_path.exists() or not env_path.is_file():
        return loaded

    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            loaded[key] = value
            os.environ.setdefault(key, value)
    return loaded


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass
class NoetraConfig:
    """Configuração de indexação, busca e síntese do Noetra."""

    chunk_size_lines: int = 40
    chunk_overlap_lines: int = 8
    max_file_size_bytes: int = 512 * 1024  # 512 KB
    cache_dir_name: str = ".noetra"
    respect_gitignore: bool = True
    ignored_dirs: set[str] = field(default_factory=lambda: set(DEFAULT_IGNORED_DIRS))
    allowed_extensions: set[str] = field(
        default_factory=lambda: set(DEFAULT_ALLOWED_EXTENSIONS)
    )

    # LLM Synthesis settings
    llm_provider: str = field(
        default_factory=lambda: _env("NOETRA_LLM_PROVIDER", "none").lower()
    )
    llm_model: str = field(
        default_factory=lambda: _env("NOETRA_LLM_MODEL", "llama3.2")
    )
    ollama_base_url: str = field(
        default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    openai_api_key: str = field(
        default_factory=lambda: _env("OPENAI_API_KEY", "")
    )
    openai_base_url: str = field(
        default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    llm_timeout_seconds: int = 45

    @classmethod
    def from_project(cls, project_path: str | Path = ".") -> NoetraConfig:
        """Cria uma configuração carregando .env do projeto ou do diretório atual."""
        root = Path(project_path).resolve()
        load_dotenv_file(root / ".env")
        load_dotenv_file(Path.cwd() / ".env")
        return cls()

    def index_file_path(self, root: Path) -> Path:
        return root / self.cache_dir_name / "index.json"
