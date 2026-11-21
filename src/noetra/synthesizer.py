"""Camada de síntese de respostas com suporte a Ollama, OpenAI-compatible e modo offline."""

from __future__ import annotations

import json
import urllib.request

from .config import NoetraConfig
from .models import SearchResult
from .retriever import tokenize


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


def _best_snippet(content: str, matched_terms: list[str], max_len: int = 180) -> str:
    """Seleciona a linha com maior concentração de termos encontrados para o preview."""
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return ""

    term_set = set(matched_terms)
    best_idx = 0
    best_hits = -1

    for idx, line in enumerate(lines):
        hits = sum(1 for tok in tokenize(line) if tok in term_set)
        if hits > best_hits:
            best_hits = hits
            best_idx = idx

    snippet = " ".join(lines[best_idx : best_idx + 2]).strip()
    if len(snippet) > max_len:
        return snippet[: max_len - 3] + "..."
    return snippet


class ContextSynthesizer:
    """Gera respostas consolidadas a partir dos trechos recuperados."""

    def __init__(self, config: NoetraConfig) -> None:
        self.config = config

    def synthesize(self, query: str, results: list[SearchResult]) -> tuple[str, str]:
        """Retorna (resposta, provedor_utilizado)."""
        if not results:
            return (
                "Nenhum trecho relevante foi encontrado no contexto indexado "
                "para essa consulta.",
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
        system_msg = "Você é o agente Noetra, especialista em contexto de projetos."
        payload = json.dumps(
            {
                "model": self.config.llm_model,
                "messages": [
                    {"role": "system", "content": system_msg},
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
            preview = _best_snippet(c.content, res.matched_terms)
            terms = ", ".join(res.matched_terms)
            lines.append(
                f"{i}. {c.file_path}:{c.start_line}-{c.end_line} "
                f"(score={res.score:.2f} | termos: {terms})\n   ↳ {preview}"
            )
        return "\n".join(lines)
