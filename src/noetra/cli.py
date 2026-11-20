"""Interface de linha de comando (CLI) do agente Noetra."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent import NoetraAgent
from .config import NoetraConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noetra",
        description="Noetra — Agente de pesquisa de contexto de projetos e recuperação de informações.",
    )
    parser.add_argument("--version", action="version", version=f"noetra {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_index = subparsers.add_parser("index", help="Indexa um diretório de projeto.")
    p_index.add_argument("path", nargs="?", default=".", help="Caminho do projeto (padrão: .)")
    p_index.add_argument("--json", action="store_true", help="Exibe saída em JSON.")

    p_inspect = subparsers.add_parser("inspect", help="Mostra a estrutura, stack e arquivos-chave do projeto.")
    p_inspect.add_argument("path", nargs="?", default=".", help="Caminho do projeto (padrão: .)")
    p_inspect.add_argument("--json", action="store_true", help="Exibe saída em JSON.")

    p_search = subparsers.add_parser("search", help="Pesquisa trechos relevantes no projeto.")
    p_search.add_argument("query", help="Consulta de busca.")
    p_search.add_argument("--path", default=".", help="Caminho do projeto (padrão: .)")
    p_search.add_argument("--top-k", type=int, default=5, help="Número máximo de resultados.")
    p_search.add_argument("--filter", dest="path_filter", default=None, help="Filtra por substring no caminho.")
    p_search.add_argument("--reindex", action="store_true", help="Força reindexação antes da busca.")
    p_search.add_argument("--json", action="store_true", help="Exibe saída em JSON.")

    p_ask = subparsers.add_parser("ask", help="Faz uma pergunta sobre o projeto e sintetiza a resposta.")
    p_ask.add_argument("question", help="Pergunta sobre o projeto.")
    p_ask.add_argument("--path", default=".", help="Caminho do projeto (padrão: .)")
    p_ask.add_argument("--top-k", type=int, default=5, help="Número de evidências recuperadas.")
    p_ask.add_argument("--filter", dest="path_filter", default=None, help="Filtra por substring no caminho.")
    p_ask.add_argument("--provider", choices=["none", "ollama", "openai"], default=None, help="Provedor de LLM.")
    p_ask.add_argument("--model", default=None, help="Nome do modelo LLM.")
    p_ask.add_argument("--reindex", action="store_true", help="Força reindexação antes de responder.")
    p_ask.add_argument("--json", action="store_true", help="Exibe saída em JSON.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    config = NoetraConfig()
    if getattr(args, "provider", None):
        config.llm_provider = args.provider
    if getattr(args, "model", None):
        config.llm_model = args.model

    if args.command in ("index", "inspect"):
        agent = NoetraAgent(Path(args.path), config=config)
        meta = agent.index_project(persist=True)
        if args.json:
            print(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"[Noetra] Projeto indexado: {meta.root_path}")
            print(f"  Arquivos: {meta.total_files} | Chunks: {meta.total_chunks}")
            print(f"  Stack: {', '.join(meta.detected_stack) or 'Não identificada'}")
            print(f"  Arquivos-chave: {', '.join(meta.key_files) or 'Nenhum'}")
        return 0

    if args.command == "search":
        agent = NoetraAgent(Path(args.path), config=config)
        results = agent.search(
            query=args.query,
            top_k=args.top_k,
            path_filter=args.path_filter,
            reindex=args.reindex,
        )
        if args.json:
            print(json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2))
        else:
            if not results:
                print("[Noetra] Nenhum resultado encontrado.")
                return 0
            for idx, res in enumerate(results, start=1):
                c = res.chunk
                print(f"\n[{idx}] {c.file_path}:{c.start_line}-{c.end_line} (score={res.score:.2f})")
                if res.matched_terms:
                    print(f"    Termos: {', '.join(res.matched_terms)}")
                print("-" * 60)
                print(c.content)
        return 0

    if args.command == "ask":
        agent = NoetraAgent(Path(args.path), config=config)
        report = agent.ask(
            question=args.question,
            top_k=args.top_k,
            path_filter=args.path_filter,
            reindex=args.reindex,
        )
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"[Noetra | {report.provider_used}]\n")
            print(report.answer)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
