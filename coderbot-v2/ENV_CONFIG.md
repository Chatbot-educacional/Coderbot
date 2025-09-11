# Configuração de Ambiente - CoderBot v2

## Variáveis de Ambiente Necessárias

### Configurações de Banco de Dados
```bash
POCKETBASE_URL=http://localhost:8090
POCKETBASE_USER_EMAIL=user@example.com
POCKETBASE_USER_PASSWORD=password123
POCKETBASE_ADMIN_EMAIL=admin@example.com
POCKETBASE_ADMIN_PASSWORD=admin123
```

### Configurações de IA - OpenAI
```bash
OPEN_AI_API_KEY=sk-your-openai-api-key-here
OPENAI_API_URL=https://api.openai.com/v1
```

### Configurações de IA - Claude (Anthropic)
```bash
CLAUDE_API_KEY=sk-ant-your-claude-api-key-here
CLAUDE_API_URL=https://api.anthropic.com
```

### Configurações de IA - Ollama (Local)
```bash
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120
```

### Configurações de IA - Open Router
```bash
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-api-key-here
OPENROUTER_API_URL=https://openrouter.ai/api/v1
```

### Outras Configurações
```bash
DEEP_SEEK_API_KEY=your-deepseek-api-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
RAPIDAPI_KEY=your-rapidapi-key-here
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key-if-needed
UVICORN_WORKERS=1
```

## Como Configurar

1. **Crie um arquivo `.env`** na raiz do projeto backend:
   ```bash
   cd backend
   cp .env.example .env  # Se existir
   # ou crie manualmente
   ```

2. **Configure suas chaves de API**:
   - **OpenAI**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - **Claude**: [https://console.anthropic.com/](https://console.anthropic.com/)
   - **Open Router**: [https://openrouter.ai/keys](https://openrouter.ai/keys)

3. **Para Ollama**:
   - Instale: [https://ollama.ai/](https://ollama.ai/)
   - Execute: `ollama serve`
   - Baixe modelos: `ollama pull llama3.2`

## Modelos Disponíveis por Provedor

### Ollama (Local)
- `llama3.2`, `llama3.2:1b`, `llama3.2:3b`
- `llama3.1`, `llama3.1:8b`, `llama3.1:70b`
- `codellama`, `codellama:7b`, `codellama:13b`
- `mistral`, `mistral:7b`
- `qwen2`, `qwen2:7b`, `qwen2:72b`

### Open Router (Cloud)
- `anthropic/claude-3-5-sonnet`
- `openai/gpt-4o`, `openai/gpt-4-turbo`
- `google/gemini-pro`
- `meta-llama/llama-3-70b-instruct`
- `mistralai/mistral-7b-instruct`

## Como Usar na API

### Especificar Provedor na Requisição
```bash
# Ollama
POST /agno/ask?provider=ollama&model_id=llama3.2

# Open Router
POST /agno/ask?provider=openrouter&model_id=anthropic/claude-3-5-sonnet

# Claude (padrão)
POST /agno/ask?provider=claude&model_id=claude-3-5-sonnet-20241022

# OpenAI
POST /agno/ask?provider=openai&model_id=gpt-4o
```

### Exemplo de Requisição Completa
```bash
curl -X POST "http://localhost:8000/agno/ask?provider=ollama&model_id=llama3.2" \
  -H "Content-Type: application/json" \
  -d '{
    "methodology": "worked_examples",
    "user_query": "Como funciona uma função recursiva?",
    "context": "Estudando programação funcional"
  }'
```

## Verificação de Funcionamento

### 1. Verificar Ollama
```bash
# Verificar se Ollama está rodando
curl http://localhost:11434/api/tags

# Testar modelo específico
curl http://localhost:11434/api/generate -d '{"model": "llama3.2", "prompt": "Olá"}'
```

### 2. Verificar Open Router
```bash
# Testar chave da API
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-3-5-sonnet",
    "messages": [{"role": "user", "content": "Olá"}]
  }'
```

### 3. Verificar Backend
```bash
# Health check
curl http://localhost:8000/health

# Listar metodologias
curl http://localhost:8000/agno/methodologies

# Testar provedores disponíveis
curl http://localhost:8000/agno/ask?provider=ollama&model_id=llama3.2 \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"methodology": "worked_examples", "user_query": "Teste"}'
```
