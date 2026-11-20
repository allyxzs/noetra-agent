"""Exemplo mínimo de uso programático do agente Noetra."""

from noetra import NoetraAgent, NoetraConfig

if __name__ == "__main__":
    config = NoetraConfig(
        llm_provider="none",  # Altere para "ollama" ou "openai" para síntese com LLM
    )
    agent = NoetraAgent(project_path=".", config=config)

    metadata = agent.inspect_project()
    print("Stack detectada:", metadata.detected_stack)
    print("Arquivos indexados:", metadata.total_files)

    report = agent.ask("Como funciona o motor de busca BM25 do Noetra?", top_k=3)
    print("\n--- Resposta do Noetra ---")
    print(report.answer)
