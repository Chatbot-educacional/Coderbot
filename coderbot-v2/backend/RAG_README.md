# Sistema RAG (Retrieval-Augmented Generation) - CoderBot v2

Este documento explica a implementação completa do sistema RAG integrado no CoderBot v2, incluindo Qdrant, context engineering e agentes educacionais inteligentes.

## 🏗️ Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Qdrant DB     │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Vector DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Educational     │    │   RAG Service   │    │   Embeddings    │
│   Agents        │◄──►│   (Context      │◄──►│   (OpenAI/      │
│                 │    │    Engineering) │    │    Local)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       ▲                       ▲
         └───────────────────────┼───────────────────────┘
                                 ▼
                   ┌─────────────────┐
                   │   PocketBase    │
                   │   (User Data)   │
                   └─────────────────┘
```

## 🚀 Benefícios Educacionais do RAG

### 1. **Personalização Inteligente**
- Adaptação automática ao perfil do estudante (estilo de aprendizado, nível, ritmo)
- Recomendações contextuais baseadas no histórico de aprendizado
- Conteúdo relevante recuperado dinamicamente

### 2. **Memória e Continuidade**
- Contexto persistente entre sessões
- Recordação inteligente de conceitos anteriores
- Progressão lógica baseada no que o estudante já sabe

### 3. **Context Engineering Avançado**
- Compressão inteligente de contexto para otimizar tokens
- Isolamento de seções importantes
- Gerenciamento hierárquico de informações

### 4. **Integração com Metodologias Pedagógicas**
- Enriquecimento das metodologias AGNO com conhecimento relevante
- Adaptação de exemplos e exercícios ao nível do estudante
- Geração de conteúdo personalizado em tempo real

## 🛠️ Componentes do Sistema

### 1. **Qdrant Vector Database**
- **Arquivo**: `docker/Dockerfile.qdrant`
- **Configuração**: `docker/qdrant/config.yaml`
- **Integração**: `docker-compose.optimized.yml`
- **Recursos**:
  - Armazenamento vetorial otimizado para embeddings
  - Busca semântica rápida e precisa
  - Filtragem contextual por assunto, dificuldade, etc.
  - Persistência de dados em volumes Docker

### 2. **Múltiplos Provedores de IA** 🆕
- **Suporte completo** a 4 provedores de IA
- **Detecção automática** do provedor baseado no ID do modelo
- **Fallback inteligente** em caso de falha
- **Configuração flexível** via variáveis de ambiente

#### Provedores Suportados:
- **OpenAI**: GPT-4, GPT-4o, GPT-3.5-turbo
- **Claude**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Ollama** 🆕: Modelos locais (Llama 3.2, CodeLlama, Mistral, etc.)
- **Open Router** 🆕: +100 modelos de diferentes provedores

#### Exemplo de Uso:
```python
# Ollama (local)
agno_service = AgnoMethodologyService(
    model_id="llama3.2",
    provider="ollama"
)

# Open Router (cloud)
agno_service = AgnoMethodologyService(
    model_id="anthropic/claude-3-5-sonnet",
    provider="openrouter"
)
```

### 3. **RAG Service**
- **Arquivo**: `app/services/rag_service.py`
- **Funcionalidades**:
  - Indexação de conteúdo educacional
  - Busca semântica com filtros contextuais
  - Context engineering (compressão, isolamento)
  - Suporte a múltiplos modelos de embedding
  - Cache inteligente para performance

### 4. **Educational Agent Service**
- **Arquivo**: `app/services/educational_agent_service.py`
- **Funcionalidades**:
  - Agentes especializados por perfil de estudante
  - Personalização dinâmica baseada em contexto
  - Memória de sessão inteligente
  - Avaliação contínua de progresso
  - Recomendações pedagógicas automáticas

### 5. **API Endpoints**
- **Arquivo**: `app/routers/agno_router.py`
- **Endpoints RAG**:
  - `POST /agno/rag/index` - Indexar conteúdo
  - `POST /agno/rag/search` - Buscar conteúdo
  - `GET /agno/rag/stats` - Estatísticas da coleção
- **Endpoints de Agentes**:
  - `POST /agno/agent/ask` - Consulta educacional personalizada
  - `GET /agno/agent/analytics/{user_id}` - Analytics do estudante
  - `POST /agno/agent/profile` - Atualizar perfil

## 📋 Pré-requisitos

### Dependências do Sistema
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential

# Python dependencies (via pyproject.toml)
pdm install
```

### Variáveis de Ambiente
```bash
# Qdrant
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=your_api_key  # Opcional

# OpenAI (para embeddings)
OPEN_AI_API_KEY=your_openai_key

# Claude (fallback)
CLAUDE_API_KEY=your_claude_key
```

## 🚀 Como Usar

### 1. **Iniciar o Sistema**
```bash
# Construir e iniciar todos os serviços
docker-compose -f docker-compose.optimized.yml up --build

# Ou apenas o Qdrant para desenvolvimento
docker-compose -f docker-compose.optimized.yml up qdrant
```

### 2. **Indexar Conteúdo Educacional**
```python
from app.services.rag_service import RAGService, EducationalContent

rag_service = RAGService()

content = EducationalContent(
    id="exemplo-algoritmos",
    title="Introdução aos Algoritmos",
    content="Conteúdo sobre algoritmos...",
    content_type="lesson",
    subject="programação",
    topic="algoritmos",
    difficulty="beginner",
    tags=["algoritmos", "programação"]
)

await rag_service.index_content(content)
```

### 3. **Realizar Busca RAG**
```python
from app.services.rag_service import SearchQuery

query = SearchQuery(
    query="Como funciona um algoritmo?",
    user_context={"difficulty": "beginner", "subject": "programação"},
    limit=5
)

results = await rag_service.search_content(query)
```

### 4. **Usar Agente Educacional**
```python
from app.services.educational_agent_service import EducationalAgentService, StudentProfile

# Criar perfil do estudante
profile = StudentProfile(
    user_id="student_123",
    learning_style="visual",
    current_level="intermediate",
    subjects=["programação", "matemática"]
)

# Processar consulta
response = await agent_service.process_educational_query(
    query="Como implementar uma função recursiva?",
    user_id="student_123",
    user_profile=profile.dict()
)

print(response.response)
print(f"Metodologia: {response.methodology_used}")
print(f"Personalização: {response.personalization_score:.2f}")
```

### 5. **API REST**
```bash
# Indexar conteúdo
curl -X POST "http://localhost:8000/agno/rag/index" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Algoritmos Básicos",
    "content": "Conteúdo sobre algoritmos...",
    "content_type": "lesson",
    "subject": "programação",
    "difficulty": "beginner"
  }'

# Buscar conteúdo
curl -X POST "http://localhost:8000/agno/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Como funciona um algoritmo?",
    "limit": 5
  }'

# Consulta educacional personalizada
curl -X POST "http://localhost:8000/agno/agent/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explique recursão em programação",
    "user_id": "student_123",
    "user_profile": {
      "learning_style": "visual",
      "current_level": "intermediate"
    }
  }'
```

## 🔧 Configuração Avançada

### Context Engineering
```python
# Configurações no RAG Service
self.max_context_tokens = 4000
self.compression_ratio = 0.7
self.isolation_threshold = 0.3
```

### Estratégias de Embedding
```python
# Prioridade de embeddings
1. OpenAI text-embedding-3-large (mais preciso)
2. Claude embeddings (fallback)
3. SentenceTransformers local (offline)
```

### Personalização de Agentes
```python
# Pesos de personalização
personalization_weights = {
    "learning_style": 0.3,
    "past_performance": 0.25,
    "learning_pace": 0.2,
    "methodology_preference": 0.15,
    "engagement_history": 0.1
}
```

## 📊 Métricas e Monitoramento

### Estatísticas RAG
```python
stats = await rag_service.get_collection_stats()
print(f"Vetores indexados: {stats['vectors_count']}")
print(f"Segmentos: {stats['segments_count']}")
```

### Analytics do Estudante
```python
analytics = await agent_service.get_student_analytics("student_123")
print(f"Engajamento médio: {analytics['average_engagement']:.2f}")
print(f"Sessões totais: {analytics['total_sessions']}")
```

## 🧪 Testes e Exemplos

### Executar Exemplo Completo
```bash
cd backend
python examples/rag_example.py
```

### Testes Unitários
```bash
# Instalar dependências de desenvolvimento
pdm install -d

# Executar testes
pdm run test
```

## 🚀 Próximos Passos

### Melhorias Planejadas
1. **Fine-tuning de embeddings** para domínio educacional brasileiro
2. **Cache distribuído** com Redis para alta performance
3. **Avaliação automática** de qualidade de respostas
4. **Integração com LMS** (Moodle, Google Classroom)
5. **Análise de sentimento** para feedback em tempo real

### Escalabilidade
- **Sharding horizontal** do Qdrant para milhões de vetores
- **API Gateway** para balanceamento de carga
- **Monitoring avançado** com Prometheus/Grafana
- **Backup automático** de vetores educacionais

## 📚 Referências

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [SentenceTransformers](https://www.sbert.net/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Context Engineering](https://jxnl.co/writing/2025/08/28/context-engineering-index/)

## 🤝 Contribuição

Para contribuir com melhorias no sistema RAG:

1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente os testes
4. Submeta um Pull Request

**Issues e discussões** são bem-vindos no repositório principal!
