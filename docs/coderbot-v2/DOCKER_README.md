# 🐳 CoderBot V2 - Docker Setup

Este guia mostra como executar o CoderBot V2 usando Docker.
O arquivo `docker-compose.optimized.yml` inicia PocketBase,
backend (FastAPI), frontend (React) e Nginx.

## 📋 Pré-requisitos

- Docker e Docker Compose v2
- Git
- Node.js e pnpm (opcional, para compilar o frontend localmente)

## 🚀 Início Rápido

```bash
# Clone o repositório
git clone <seu-repositorio>
cd coderbot-v2

# Configure variáveis de ambiente
cp .env.example .env
# edite .env com suas credenciais

# Opcional: compilar frontend
cd frontend
pnpm install --frozen-lockfile
pnpm run build
cd ..

# Subir serviços
docker compose -f docker-compose.optimized.yml up -d --build
```

## 🌐 URLs dos Serviços

- **App (via Nginx)**: <http://localhost:3001>
  - Alternativa: <http://localhost:8080>
- **Backend (FastAPI)**: <http://localhost:8000>
- **PocketBase**: <http://localhost:8090>

## 🔧 Comandos Úteis

```bash
# Logs de todos os serviços
docker compose -f docker-compose.optimized.yml logs -f

# Parar e remover serviços
docker compose -f docker-compose.optimized.yml down

# Reiniciar serviços específicos
docker compose -f docker-compose.optimized.yml restart backend nginx

# Acessar shell do backend
docker compose -f docker-compose.optimized.yml exec backend bash

# Ver status
docker compose -f docker-compose.optimized.yml ps
```

## 🏗️ Arquitetura dos Containers

```
┌────────────┐    ┌────────────┐    ┌────────────┐
│ Frontend   │    │ Backend    │    │ PocketBase │
│ (React)    │────│ (FastAPI)  │────│ (Banco)    │
└────────────┘    └────────────┘    └────────────┘
                │
             Nginx (3001/8080)
```

## 📝 Notas

- O arquivo `docker-compose.dev.yml` oferece um ambiente de desenvolvimento com hot reload.
- Para atualizar as imagens ou recompilar:
  ```bash
  docker compose -f docker-compose.optimized.yml pull
  docker compose -f docker-compose.optimized.yml build --no-cache
  ```

