# CodeBot - Ambiente de Desenvolvimento

Este documento descreve como configurar e usar o ambiente de desenvolvimento do CodeBot com **hot reload** ativado.

## 🚀 Início Rápido (Recomendado)

### Pré-requisitos

- Docker e Docker Compose instalados
- Git
- curl (para testes de API)

### Configuração Automática

1. **Clone o repositório:**
```bash
git clone <repository-url>
cd coderbot-v2
```

2. **Execute o script de setup automático:**
```bash
./setup-dev.sh
```

**⚡ Este é o método recomendado!** O script irá:
- ✅ Verificar pré-requisitos (Docker, Docker Compose)
- ✅ Criar arquivos `.env` necessários
- ✅ Iniciar todos os serviços Docker
- ✅ Configurar PocketBase (admin e usuário regular)
- ✅ Corrigir problemas comuns de configuração
- ✅ Testar a configuração
- ✅ Exibir informações importantes

**Tempo estimado:** 2-3 minutos

### Configuração Manual (Alternativa)

Se preferir configurar manualmente:

1. **Crie os arquivos `.env`:**
```bash
# Arquivo .env principal
cp .env.example .env

# Arquivo .env do backend
cp backend/.env.example backend/.env

# Arquivo .env do frontend
cp frontend/.env.example frontend/.env
```

2. **Inicie o ambiente:**
```bash
./dev.sh up
```

3. **Configure o PocketBase:**
```bash
# Criar usuário admin
docker exec -it coderbot-pocketbase-dev /pb/pocketbase superuser upsert andremendes0113@gmail.com coderbotdagalera

# Criar usuário regular
curl -X POST http://localhost:8090/api/collections/users/records \
  -H "Content-Type: application/json" \
  -d '{
    "email": "andremendes0113@gmail.com",
    "password": "coderbotdagalera",
    "passwordConfirm": "coderbotdagalera",
    "name": "Andre Mendes"
  }'

# Reiniciar backend
docker restart coderbot-backend-dev
```

### Serviços Disponíveis

Após iniciar o ambiente, os seguintes serviços estarão disponíveis:

- **Frontend (React + Vite)**: http://localhost:3000
- **Backend (FastAPI)**: http://localhost:8000
- **PocketBase (Database)**: http://localhost:8090
- **Code Server (IDE)**: http://localhost:8787

## 🔧 Comandos Disponíveis

Use o script `./dev.sh` para gerenciar o ambiente:

### Comandos Básicos

```bash
# Iniciar todos os serviços
./dev.sh up

# Parar todos os serviços
./dev.sh down

# Reiniciar todos os serviços
./dev.sh restart

# Ver status dos serviços
./dev.sh status
```

### Logs e Monitoramento

```bash
# Ver logs de todos os serviços
./dev.sh logs

# Ver logs em tempo real
./dev.sh logs-f

# Ver logs apenas do backend
./dev.sh backend

# Ver logs apenas do frontend
./dev.sh frontend
```

### Manutenção

```bash
# Rebuildar todas as imagens
./dev.sh build

# Limpar containers, volumes e imagens
./dev.sh clean
```

## 🔥 Hot Reload

### Frontend (React + Vite)

- **Arquivos monitorados**: `./frontend/src/`
- **Tecnologia**: Vite Dev Server
- **Configuração**: Volume mapping em `docker-compose.dev.yml`
- **Variáveis de ambiente**:
  - `CHOKIDAR_USEPOLLING=true`
  - `WATCHPACK_POLLING=true`

### Backend (FastAPI)

- **Arquivos monitorados**: `./backend/`
- **Tecnologia**: Uvicorn com `--reload`
- **Configuração**: Volume mapping em `docker-compose.dev.yml`
- **Comando**: `uvicorn app.main:app --reload --reload-dir /app`

## 📁 Estrutura de Volumes

O ambiente de desenvolvimento usa volumes para:

1. **Preservar dependências**: `node_modules` e `.venv` são mantidos em volumes separados
2. **Hot reload**: Código fonte é mapeado diretamente do host
3. **Persistência de dados**: Dados do PocketBase são mantidos em volume

```yaml
volumes:
  - ./frontend:/app                           # Código do frontend
  - frontend_node_modules_dev:/app/node_modules  # Dependências Node.js
  - ./backend:/app                            # Código do backend
  - backend_deps_dev:/app/.venv              # Dependências Python
```

## 🛠️ Configuração do Ambiente

### Arquivo `.env`

O arquivo `.env` é criado automaticamente com valores padrão:

```env
# Configurações do PocketBase
POCKETBASE_ADMIN_EMAIL=admin@coderbot.dev
POCKETBASE_ADMIN_PASSWORD=admin123456

# Chaves de API
DEEP_SEEK_API_KEY=your_deep_seek_api_key
DEEP_SEEK_API_URL=https://api.deepseek.com
OPEN_AI_API_KEY=your_openai_api_key
OPENAI_API_URL=https://api.openai.com
CLAUDE_API_KEY=your_claude_api_key
RAPIDAPI_KEY=your_rapidapi_key

# Supabase (opcional)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Variáveis de Desenvolvimento

As seguintes variáveis são automaticamente definidas no ambiente de desenvolvimento:

**Frontend:**
- `NODE_ENV=development`
- `VITE_API_URL=http://localhost:8000`
- `VITE_POCKETBASE_URL=http://localhost:8090`

**Backend:**
- `PYTHONPATH=/app`
- `DEVELOPMENT=true`
- `POCKETBASE_URL=http://pocketbase:8090`

## 🐛 Troubleshooting

### Problemas Comuns

1. **Porta já em uso:**
```bash
# Verificar processos usando as portas
sudo lsof -i :3000
sudo lsof -i :8000
sudo lsof -i :8090
```

2. **Hot reload não funciona:**
```bash
# Verificar se os volumes estão montados corretamente
docker compose -f docker-compose.dev.yml exec frontend ls -la /app
docker compose -f docker-compose.dev.yml exec backend ls -la /app
```

3. **Dependências não instaladas:**
```bash
# Rebuildar as imagens
./dev.sh build
```

4. **Limpar ambiente completamente:**
```bash
./dev.sh clean
./dev.sh up
```

### Logs Detalhados

Para debugar problemas específicos:

```bash
# Ver logs detalhados de um serviço específico
docker compose -f docker-compose.dev.yml logs -f [service-name]

# Entrar no container para debug
docker compose -f docker-compose.dev.yml exec [service-name] /bin/bash
```

## 📋 Checklist de Desenvolvimento

- [ ] Ambiente iniciado com `./dev.sh up`
- [ ] Frontend acessível em http://localhost:3000
- [ ] Backend acessível em http://localhost:8000
- [ ] Hot reload funcionando no frontend
- [ ] Hot reload funcionando no backend
- [ ] Logs visíveis com `./dev.sh logs-f`

## 🔄 Workflow de Desenvolvimento

1. **Inicie o ambiente**: `./dev.sh up`
2. **Faça suas alterações** no código
3. **Veja as mudanças** automaticamente refletidas
4. **Monitore os logs** com `./dev.sh logs-f`
5. **Teste** as funcionalidades
6. **Pare o ambiente** com `./dev.sh down` quando terminar

## 🔧 Troubleshooting

### Problemas Comuns

1. **Erro de porta ocupada**
   - Verifique se as portas 3000, 8000, 8090 e 8787 estão livres
   - Use `netstat -tulpn | grep :3000` para verificar

2. **Erro de permissão do Docker**
   - Adicione seu usuário ao grupo docker: `sudo usermod -aG docker $USER`
   - Faça logout e login novamente

3. **Erro de memória insuficiente**
   - Aumente a memória disponível para o Docker
   - Feche outros aplicativos que consomem muita memória

4. **Hot reload não funciona**
   - Verifique se os volumes estão montados corretamente
   - Reinicie o container específico: `docker restart coderbot-frontend-dev`

5. **Erro de autenticação no PocketBase**
   - Execute o script de setup novamente: `./setup-dev.sh`
   - Ou configure manualmente os usuários conforme documentado acima

6. **Backend não consegue conectar ao PocketBase**
   - Verifique se o arquivo `backend/.env` tem `POCKETBASE_URL=http://pocketbase:8090`
   - Reinicie o backend: `docker restart coderbot-backend-dev`

### Logs e Depuração

```bash
# Ver logs de todos os serviços
./dev.sh logs-f

# Ver logs de um serviço específico
./dev.sh logs frontend
./dev.sh logs backend
./dev.sh logs pocketbase

# Acessar shell de um container
docker exec -it coderbot-frontend-dev sh
docker exec -it coderbot-backend-dev bash
docker exec -it coderbot-pocketbase-dev sh
```

### Comandos de Recuperação

Se algo der errado, use estes comandos para resetar:

```bash
# Parar todos os serviços
./dev.sh down

# Limpar containers, volumes e imagens
./dev.sh clean

# Recriar tudo do zero
./setup-dev.sh
```

### Credenciais Padrão

Para desenvolvimento, use estas credenciais:

```
Email: andremendes0113@gmail.com
Senha: coderbotdagalera
```

## 🚀 Próximos Passos

- Configure as chaves de API no arquivo `.env`
- Explore o Code Server em http://localhost:8787
- Consulte a documentação da API em http://localhost:8000/docs
- Acesse o admin do PocketBase em http://localhost:8090/_/ 