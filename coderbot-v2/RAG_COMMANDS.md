# Comandos para Sistema RAG Educacional - CoderBot v2

## 🚀 Início Rápido

### 1. Iniciar Sistema Completo
```bash
# Construir e iniciar todos os serviços (Qdrant + Backend + Frontend)
docker-compose -f docker-compose.optimized.yml up --build
```

### 2. Iniciar Apenas RAG (Desenvolvimento)
```bash
# Iniciar apenas Qdrant + Backend para desenvolvimento
docker-compose -f docker-compose.optimized.yml up qdrant backend --build
```

### 3. Verificar Status dos Serviços
```bash
docker-compose -f docker-compose.optimized.yml ps
```

## 🧪 Testes e Demonstrações

### 4. Executar Exemplo Completo
```bash
cd backend
python examples/rag_example.py
```

### 5. Testar Endpoints da API
```bash
# Documentação FastAPI
curl http://localhost:8000/docs

# Health check Qdrant
curl http://localhost:6333/healthz

# Health check Backend
curl http://localhost:8000/health
```

### 6. Testar Funcionalidades RAG
```bash
# Indexar conteúdo educacional
curl -X POST "http://localhost:8000/agno/rag/index" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Introdução aos Algoritmos",
    "content": "Algoritmos são sequências finitas de passos...",
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
    "user_id": "demo_student",
    "user_profile": {
      "learning_style": "visual",
      "current_level": "intermediate"
    }
  }'

# Estatísticas RAG
curl http://localhost:8000/agno/rag/stats

# Analytics do estudante
curl http://localhost:8000/agno/agent/analytics/demo_student
```

## 📊 Monitoramento e Logs

### 7. Logs dos Serviços
```bash
# Logs do Qdrant
docker-compose -f docker-compose.optimized.yml logs -f qdrant

# Logs do Backend
docker-compose -f docker-compose.optimized.yml logs -f backend

# Logs de todos os serviços
docker-compose -f docker-compose.optimized.yml logs -f
```

### 8. Monitorar Recursos
```bash
# Uso de CPU/Memória
docker stats

# Espaço em disco dos volumes
docker system df -v
```

## 🛠️ Desenvolvimento e Manutenção

### 9. Reiniciar Serviços
```bash
# Reiniciar Qdrant
docker-compose -f docker-compose.optimized.yml restart qdrant

# Reiniciar Backend
docker-compose -f docker-compose.optimized.yml restart backend

# Reiniciar tudo
docker-compose -f docker-compose.optimized.yml restart
```

### 10. Limpar Sistema
```bash
# Parar serviços
docker-compose -f docker-compose.optimized.yml down

# Limpar volumes (CUIDADO: perde dados!)
docker-compose -f docker-compose.optimized.yml down -v

# Limpar imagens não utilizadas
docker image prune -f

# Limpar sistema completo
docker system prune -f
```

### 11. Atualizar Dependências
```bash
cd backend

# Instalar/atualizar dependências Python
pdm install

# Atualizar lockfile
pdm lock

# Verificar dependências desatualizadas
pdm update --dry-run
```

## 🔧 Troubleshooting

### Problemas Comuns

#### Qdrant não inicia
```bash
# Verificar logs detalhados
docker-compose -f docker-compose.optimized.yml logs qdrant

# Verificar portas ocupadas
netstat -tulpn | grep :6333

# Limpar e reconstruir
docker-compose -f docker-compose.optimized.yml down
docker-compose -f docker-compose.optimized.yml up --build --force-recreate qdrant
```

#### Backend não conecta ao Qdrant
```bash
# Verificar conectividade
docker exec -it coderbot-qdrant curl http://localhost:6333/healthz

# Verificar variáveis de ambiente
docker exec -it coderbot-backend env | grep QDRANT
```

#### Embeddings falham
```bash
# Verificar chaves da API
echo $OPEN_AI_API_KEY
echo $CLAUDE_API_KEY

# Testar conectividade da API
curl -H "Authorization: Bearer $OPEN_AI_API_KEY" \
     https://api.openai.com/v1/models
```

## 📈 Performance Tuning

### Otimizar Qdrant
```bash
# Ajustar limites de memória
docker-compose -f docker-compose.optimized.yml up -d
docker update --memory=2g --cpus=2 coderbot-qdrant
```

### Otimizar Backend
```bash
# Configurar workers do Uvicorn
export UVICORN_WORKERS=4
docker-compose -f docker-compose.optimized.yml up -d backend
```

## 🔧 Teste de Provedores de IA

### Testar Provedores Individuais
```bash
cd backend

# Testar Ollama
python test_providers.py ollama llama3.2

# Testar Open Router
python test_providers.py openrouter anthropic/claude-3-5-sonnet

# Testar Claude
python test_providers.py claude claude-3-5-sonnet-20241022

# Testar OpenAI
python test_providers.py openai gpt-4o

# Listar modelos disponíveis
python test_providers.py --list
```

### Configuração de Provedores

#### Ollama (Local)
```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar servidor
ollama serve

# Baixar modelos
ollama pull llama3.2
ollama pull codellama:7b
ollama pull mistral:7b

# Verificar modelos disponíveis
ollama list
```

#### Open Router (Cloud)
```bash
# Obter chave de API gratuita
# https://openrouter.ai/keys

# Testar API
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-3-5-sonnet",
    "messages": [{"role": "user", "content": "Olá"}]
  }'
```

## 🌐 Produção

### Configuração para Produção
```bash
# Usar compose de produção
docker-compose -f docker-compose.yml up -d

# Configurar HTTPS (nginx)
docker-compose -f docker-compose.yml up -d nginx

# Backup automático
docker run --rm -v qdrant_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/qdrant-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

## 📚 Documentação

- [RAG_README.md](backend/RAG_README.md) - Documentação completa do sistema RAG
- [API Docs](http://localhost:8000/docs) - Documentação interativa da API
- [Qdrant Docs](https://qdrant.tech/documentation/) - Documentação oficial do Qdrant

## 🎯 Próximos Passos

1. **Teste o sistema**: Execute o exemplo em `backend/examples/rag_example.py`
2. **Indexe conteúdo**: Adicione seu próprio conteúdo educacional
3. **Personalize agentes**: Ajuste os perfis de estudante e metodologias
4. **Monitore performance**: Use os comandos de logs e estatísticas
5. **Otimize**: Ajuste parâmetros baseado no uso real

---

**🎉 Sistema RAG educacional pronto para uso!**

Para dúvidas ou problemas, consulte os logs ou abra uma issue no repositório.
