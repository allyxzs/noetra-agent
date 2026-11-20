"""Camada de síntese de respostas com suporte a Ollama, OpenAI-compatible e modo offline."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import NoetraConfig
from .models import SearchResult


def build_prompt(query: str, results: list[SearchResult]) -> str:
    """Monta o prompt de contexto grounded com citações de arquivo e linha."""
    context_blocks = []
    for i, res in enumerate(results, start=1):
        c = res.chunk
        context_blocks.append(
            f"[{i}] Arquivo: {c.file_path} (linhas {c.start_line}-{c.end_line})\n"
            f"```\n{c.content}\n```"
        )
    joined_context = "\n\n".join(context_blocks)
    return (
        "Você é o Noetra, um agente especialista em pesquisa de contexto de projetos.\n"
        "Responda à pergunta usando APENAS as evidências recuperadas abaixo. "
        "Sempre cite os caminhos de arquivo e intervalos de linha relevantes.\n\n"
        f"Pergunta: {query}\n\n"
        f"Evidências recuperadas:\n{joined_context}\n\n"
        "Resposta objetiva e fundamentada:"
    )


class ContextSynthesizer:
    """Gera respostas consolidadas a partir dos trechos recuperados."""

    def __init__(self, config: NoetraConfig) -> None:
        self.config = config

    def synthesize(self, query: str, results: list[SearchResult]) -> tuple[str, str]:
        """Retorna (resposta, provedor_utilizado)."""
        if not results:
            return (
                "Nenhum trecho relevante foi encontrado no contexto indexado para essa consulta.",
                "extractive",
            )

        provider = self.config.llm_provider.lower()
        prompt = build_prompt(query, results)

        if provider == "ollama":
            try:
                return self._call_ollama(prompt), f"ollama:{self.config.llm_model}"
            except Exception:
                pass
        elif provider == "openai" and self.config.openai_api_key:
            try:
                return self._call_openai(prompt), f"openai:{self.config.llm_model}"
            except Exception:
                pass

        return self._extractive_summary(query, results), "extractive"

    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.config.ollama_base_url.rstrip('/')}/api/generate"
        payload = json.dumps(
            {
                "model": self.config.llm_model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.config.llm_timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip()

    def _call_openai(self, prompt: str) -> str:
        url = f"{self.config.openai_base_url.rstrip('/')}/chat/completions"
        payload = json.dumps(
            {
                "model": self.config.llm_model,
                "messages": [
                    {"role": "system", "content": "Você é o agente Noetra, especialista em contexto de projetos."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.openai_api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.config.llm_timeout_seconds) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()

    def _extractive_summary(self, query: str, results: list[SearchResult]) -> str:
        lines = [f"Encontrados {len(results)} trecho(s) relevantes para: '{query}'"]
        for i, res in enumerate(results, start=1):
            c = res.chunk
            preview = " ".join(c.content.splitlines()[:3]).strip()
            if len(preview) > 160:
                preview = preview[:157] + "..."
            terms = ", ".join(res.matched_terms)
            lines.append(
                f"{i}. {c.file_path}:{c.start_line}-{c.end_line} "
                f"(score={res.score:.2f} | termos: {terms})\n   ↳ {preview}"
            )
        return "\n".join(lines)
