"""Testes unitários e de integração do agente Noetra."""

from pathlib import Path

from noetra import NoetraAgent, NoetraConfig
from noetra.cli import main as cli_main
from noetra.config import load_dotenv_file


def _create_sample_project(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        "# Atlas API\n\nServiço de autenticação JWT e processamento de pagamentos.\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "atlas-api"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text("ignored_dir/\n*.log\n", encoding="utf-8")

    ignored_dir = tmp_path / "ignored_dir"
    ignored_dir.mkdir()
    (ignored_dir / "secret.py").write_text("SECRET_TOKEN = 'do-not-index'\n", encoding="utf-8")
    (tmp_path / "debug.log").write_text("log line\n", encoding="utf-8")

    src = tmp_path / "src"
    src.mkdir()
    (src / "auth.py").write_text(
        "def verify_jwt_token(token: str) -> dict:\n"
        '    """Valida assinatura e expiração de tokens JWT."""\n'
        "    if not token:\n"
        "        raise ValueError('Token inválido')\n"
        "    return {'sub': 'user_123', 'role': 'admin'}\n",
        encoding="utf-8",
    )
    (src / "billing.py").write_text(
        "class InvoiceProcessor:\n"
        "    def charge_subscription(self, customer_id: str, amount_cents: int) -> bool:\n"
        "        return amount_cents > 0\n",
        encoding="utf-8",
    )
    return tmp_path


def test_index_respects_gitignore_and_metadata(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    meta = agent.index_project(persist=True)

    assert meta.total_files == 4
    assert meta.total_chunks >= 4
    assert "Python" in meta.detected_stack
    assert "README.md" in meta.key_files
    assert "ignored_dir/secret.py" not in meta.indexed_files
    assert (project / ".noetra" / "index.json").exists()


def test_search_accent_insensitive_and_symbols(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    results = agent.search("expiracao token JWT", top_k=2)

    assert len(results) >= 1
    assert results[0].chunk.file_path == "src/auth.py"
    assert "verify_jwt_token" in results[0].chunk.symbols


def test_search_with_path_filter(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    results = agent.search("JWT", top_k=5, path_filter="README")

    assert len(results) == 1
    assert results[0].chunk.file_path == "README.md"


def test_ask_returns_grounded_report(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    report = agent.ask("onde fica o processamento de subscription e invoice?", top_k=2)

    assert report.provider_used == "extractive"
    assert len(report.results) >= 1
    assert report.results[0].chunk.file_path == "src/billing.py"
    assert "src/billing.py" in report.answer


def test_dotenv_loader_and_cli(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    env_file = project / ".env"
    env_file.write_text("NOETRA_TEST_VAR=ok\n# comment\n", encoding="utf-8")

    loaded = load_dotenv_file(env_file)
    assert loaded["NOETRA_TEST_VAR"] == "ok"

    assert cli_main(["inspect", str(project)]) == 0
    assert cli_main(["tree", str(project)]) == 0
    assert cli_main(["ask", "JWT", "--path", str(project), "--json"]) == 0
