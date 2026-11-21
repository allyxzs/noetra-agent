# Noetra

[![CI](https://github.com/allyxzs/noetra-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/allyxzs/noetra-agent/actions/workflows/ci.yml)

**Noetra** é um agente leve e extensível para pesquisar contextos de projetos de software e recuperar informações relevantes com precisão (arquivo, linhas, símbolos e síntese grounded).

Projetado para rodar **100% offline por padrão** (usando apenas a biblioteca padrão do Python com ranqueamento BM25 + boost de símbolos/caminhos) e integrar-se opcionalmente a **Ollama** ou **APIs compatíveis com OpenAI** para síntese de respostas.

---

## Recursos

- **Scanner inteligente com suporte a `.gitignore`:** ignora diretórios de build/cache (`node_modules`, `.git`, `.venv`, `dist`, etc.) e padrões do `.gitignore`, detecta a stack automaticamente e extrai símbolos (Python, JS/TS, Rust, Go e Markdown).
- **Recuperação BM25 insensível a acentos:** tokenização ciente de `camelCase`, `snake_case` e normalização de diacríticos (`autenticacao` == `autenticação`), com boost para correspondências em caminhos de arquivo e símbolos.
- **Cache persistente local:** salva o índice em `.noetra/index.json` para consultas instantâneas.
- **Carregamento automático de `.env`:** lê configurações locais sem dependências externas.
- **Síntese flexível:** funciona em modo extrativo inteligente offline (`none`), com LLMs locais via **Ollama** ou via **OpenAI-compatible API**.
- **CLI e SDK Python:** pronto para uso no terminal, scripts ou integração como ferramenta em arquiteturas multi-agente.

---

## Instalação

```bash
git clone https://github.com/allyxzs/noetra-agent.git
cd noetra-agent
pip install -e .
```

Para desenvolvimento (testes e linter):

```bash
pip install -e ".[dev]"
```

---

## Uso rápido (CLI)

### 1. Inspecionar e indexar um projeto
```bash
noetra inspect ./meu-projeto
noetra tree ./meu-projeto
```

### 2. Pesquisar trechos relevantes
```bash
noetra search "autenticacao JWT" --path ./meu-projeto --top-k 5
```

### 3. Fazer uma pergunta contextualizada
```bash
# Modo offline (extrativo)
noetra ask "Onde ficam as regras de cobrança?" --path ./meu-projeto

# Com Ollama local
noetra ask "Explique o fluxo de autenticação" --path ./meu-projeto --provider ollama --model llama3.2

# Saída estruturada em JSON (ideal para pipelines e outros agentes)
noetra ask "Qual é a arquitetura do projeto?" --path ./meu-projeto --json
```

---

## Uso como SDK (Python)

```python
from noetra import NoetraAgent, NoetraConfig

config = NoetraConfig(llm_provider="none")
agent = NoetraAgent(project_path="./meu-projeto", config=config)

report = agent.ask("Como o índice de busca é salvo em disco?", top_k=3)
print(report.answer)

for item in report.results:
    print(item.chunk.file_path, item.chunk.start_line, item.score)
```

---

## Configuração (.env)

Copie o arquivo `.env.example` para `.env` e ajuste conforme necessário:

```env
NOETRA_LLM_PROVIDER=none
NOETRA_LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## Testes e Lint

```bash
ruff check src tests
pytest -v
```

---

## Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
