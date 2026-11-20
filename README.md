# Noetra

**Noetra** é um agente leve e extensível para pesquisar contextos de projetos de software e recuperar informações relevantes com precisão (arquivo, linhas, símbolos e síntese grounded).

Projetado para rodar **100% offline por padrão** (usando apenas a biblioteca padrão do Python com ranqueamento BM25 + boost de símbolos/caminhos) e integrar-se opcionalmente a **Ollama** ou **APIs compatíveis com OpenAI** para síntese de respostas.

---

## Recursos

- **Scanner inteligente de projetos:** ignora diretórios de build/cache (`node_modules`, `.git`, `.venv`, `dist`, etc.), detecta a stack automaticamente e extrai símbolos (funções, classes, interfaces e títulos Markdown).
- **Recuperação BM25 com boost estrutural:** tokenização ciente de `camelCase` e `snake_case`, com peso adicional para correspondências em caminhos de arquivo e nomes de símbolos.
- **Cache persistente local:** salva o índice em `.noetra/index.json` para consultas instantâneas.
- **Síntese flexível:** funciona em modo extrativo offline (`none`), com LLMs locais via **Ollama** ou via **OpenAI-compatible API**.
- **CLI e SDK Python:** pronto para uso no terminal, scripts ou integração como ferramenta em arquiteturas multi-agente.

---

## Instalação

```bash
git clone https://github.com/<seu-usuario>/noetra.git
cd noetra
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
```

### 2. Pesquisar trechos relevantes
```bash
noetra search "autenticação JWT" --path ./meu-projeto --top-k 5
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

## Estrutura do Repositório

```text
noetra/
├── .github/workflows/ci.yml   # Pipeline de testes e lint no GitHub Actions
├── examples/basic_usage.py    # Exemplo de uso via Python SDK
├── src/noetra/
│   ├── agent.py               # Orquestrador NoetraAgent
│   ├── cli.py                 # Interface CLI (noetra)
│   ├── config.py              # Configurações e variáveis de ambiente
│   ├── models.py              # Dataclasses de chunks, resultados e relatórios
│   ├── retriever.py           # Motor BM25 + persistência em JSON
│   ├── scanner.py             # Scanner de diretórios e extrator de símbolos
│   └── synthesizer.py         # Síntese extrativa, Ollama e OpenAI-compatible
├── tests/test_noetra.py       # Testes automatizados
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
└── README.md
```

---

## Testes

```bash
pytest -v
```

---

## Publicando no GitHub

```bash
cd noetra
git init
git add .
git commit -m "feat: initial release of Noetra context research agent"
git branch -M main
git remote add origin https://github.com/<seu-usuario>/noetra.git
git push -u origin main
```

---

## Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
