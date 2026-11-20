"""Testes unitários e de integração do agente Noetra."""

from pathlib import Path

from noetra import NoetraAgent, NoetraConfig


def _create_sample_project(tmp_path: Path) -> Path:
    (tmp_path / "README.md").write_text(
        "# Atlas API\n\nServiço de autenticação JWT e processamento de pagamentos.\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "atlas-api"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
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


def test_index_and_metadata(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    meta = agent.index_project(persist=True)

    assert meta.total_files == 4
    assert meta.total_chunks >= 4
    assert "Python" in meta.detected_stack
    assert "README.md" in meta.key_files
    assert (project / ".noetra" / "index.json").exists()


def test_search_retrieves_relevant_code(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    results = agent.search("como funciona a validação de token JWT", top_k=2)

    assert len(results) >= 1
    assert results[0].chunk.file_path == "src/auth.py"
    assert "verify_jwt_token" in results[0].chunk.symbols


def test_ask_returns_grounded_report(tmp_path: Path) -> None:
    project = _create_sample_project(tmp_path)
    agent = NoetraAgent(project, config=NoetraConfig(llm_provider="none"))
    report = agent.ask("onde fica o processamento de subscription e invoice?", top_k=2)

    assert report.provider_used == "extractive"
    assert len(report.results) >= 1
    assert report.results[0].chunk.file_path == "src/billing.py"
    assert "src/billing.py" in report.answer
