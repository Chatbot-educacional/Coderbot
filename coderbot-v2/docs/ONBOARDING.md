### Onboarding – CoderBot v2

Bem-vindo ao CoderBot v2! Este documento orienta a configuração do ambiente, execução com Docker e localmente, variáveis de ambiente, fluxos de trabalho comuns e soluções para problemas frequentes.


## Visão geral
- **Frontend**: React + Vite + TypeScript + shadcn/ui (diretório `coderbot-v2/frontend`).
- **Backend**: FastAPI (Python 3.12, gerenciado por PDM) em `coderbot-v2/backend`.
- **Banco/Realtime**: PocketBase 0.27.2 (diretório de dados/migrações versionado).
- **Reverse Proxy**: Nginx roteando `/{frontend}`, `/api/{backend}` e `/pb/{pocketbase}`.
- **Execução opcional**: Judge0 (execução de código) via perfil `judge` no Compose.

Arquitetura (resumo):
- Nginx (porta host 3001) → `frontend:3000` (SPA estática servida) → chama `backend:8000` via `/api` e `pocketbase:8090` via `/pb`.


## Requisitos
- Docker Desktop (inclui Docker Compose v2): [Download](https://docs.docker.com/desktop/)
- Node.js LTS (18+ recomendado 20): [Download](https://nodejs.org/en)
- Python 3.12+: [Download](https://www.python.org/downloads/)

Instalação rápida de ferramentas:
```bash
# pnpm
npm i -g pnpm

# PDM (Python)
pip install -U pdm
```


## Quickstart com Docker (otimizado)
Este modo usa o Nginx como entrada única e serve o frontend pré-compilado. Antes do `up`, gere o `dist/` do frontend.

1) Crie o arquivo `.env` em `coderbot-v2/` com variáveis mínimas:
```bash
POCKETBASE_ADMIN_EMAIL=admin@example.com
POCKETBASE_ADMIN_PASSWORD=strong-password
```

2) Compile o frontend (gera `frontend/dist`):
```bash
cd coderbot-v2/frontend
pnpm install --frozen-lockfile
pnpm run build
```

3) Suba os serviços:
```bash
cd ..
docker compose -f docker-compose.optimized.yml up -d --build
```

4) Acesse:
- App (via Nginx): `http://localhost:3001/`  ← recomendada
- Alternativa: `http://localhost:8080/`
- API (health): `http://localhost:8000/health`
- PocketBase: `http://localhost:8090/`

Ver logs:
```bash
docker compose -f docker-compose.optimized.yml logs -f nginx
```
Parar/limpar:
```bash
docker compose -f docker-compose.optimized.yml down
```

> Observação: a porta 3000 do frontend NÃO é publicada no host por padrão. Use `http://localhost:3001`. Se quiser expor 3000 diretamente, veja “Troubleshooting”.


## Execução local (sem Docker)
Para desenvolvimento local, consulte `coderbot-v2/README.dev.md`.


## Variáveis de ambiente (principais)
- Autenticação Admin PB:
  - `POCKETBASE_ADMIN_EMAIL`, `POCKETBASE_ADMIN_PASSWORD`
- Acesso PB no backend:
  - `POCKETBASE_URL` (padrão interno: `http://pocketbase:8090`)
  - `POCKETBASE_USER_EMAIL`, `POCKETBASE_USER_PASSWORD` (opcional)
- LLMs/Provedores (opcionais):
  - `CLAUDE_API_KEY` (alias SDK: `ANTHROPIC_API_KEY`)
  - `OPEN_AI_API_KEY` (alias: `OPENAI_API_KEY`)
  - `DEEP_SEEK_API_KEY`, `DEEP_SEEK_API_URL`
  - `OPENAI_API_URL`
  - `RAPIDAPI_KEY`
- Frontend (Vite):
  - `VITE_API_URL` (default no Compose otimizado: `/api` via Nginx)
  - `VITE_POCKETBASE_URL` (default no Compose otimizado: `/pb` via Nginx)
  - `VITE_PUBLIC_POSTHOG_KEY`, `VITE_PUBLIC_POSTHOG_HOST`

Exemplo de `.env` (Compose otimizado):
```bash
POCKETBASE_ADMIN_EMAIL=admin@example.com
POCKETBASE_ADMIN_PASSWORD=strong-password
```


## Fluxos comuns
- Atualizar frontend e publicar:
```bash
cd coderbot-v2/frontend
pnpm run build
cd ..
docker compose -f docker-compose.optimized.yml restart frontend nginx
```
- Ver health do backend:
```bash
curl http://localhost:8000/health
```
- Acessar Admin do PocketBase:
```bash
open http://localhost:8090/_/
```


## Testes
- Backend (pytest):
```bash
cd coderbot-v2/backend
pdm run pytest -q
```


## Troubleshooting
- “Frontend ok, mas acessar porta 3000 no host não abre nada”
  - No arquivo `docker-compose.optimized.yml`, o frontend é servido internamente em `3000` e exposto pelo Nginx em `3001` (e `8080`). Acesse `http://localhost:3001`. Se quiser expor 3000 diretamente, adicione:
```yaml
# em services.frontend
ports:
  - "3000:3000"
```
  - Em seguida: `docker compose -f docker-compose.optimized.yml up -d --build`.

- Erro de build do frontend no Docker com caminhos (ex.: “Could not load ... /ui/toaster”)
  - Em sistemas Linux, caminhos são case-sensitive. Verifique o nome de arquivo e importação com a mesma caixa (ex.: `toaster.tsx` ≠ `Toaster.tsx`).
  - Alternativa (usada neste Compose otimizado): build local (`pnpm run build`) e servir `dist/` com Node dentro do container.

- PocketBase admin não é criado
  - Garanta `POCKETBASE_ADMIN_EMAIL` e `POCKETBASE_ADMIN_PASSWORD` no `.env` antes do `up`.
  - Confira logs do container `pocketbase`.

- Atualizar imagens/limpar cache
```bash
docker compose -f docker-compose.optimized.yml pull
docker compose -f docker-compose.optimized.yml build --no-cache
```


## Estrutura relevante do repositório
- `coderbot-v2/frontend/` – SPA, assets, Vite config
- `coderbot-v2/backend/` – FastAPI (PDM, `app/main.py`)
- `coderbot-v2/pocketbase_0.27.2_linux_amd64/` – dados/migrações PB
- `coderbot-v2/docker/` – Dockerfiles e Nginx config
- `coderbot-v2/docker-compose.optimized.yml` – stack principal
- `coderbot-v2/docker-compose.dev.yml` – stack de desenvolvimento (opcional)


## Suporte
- Crie issues com logs e passos para reproduzir.
- Inclua versão de Docker/Compose, SO e mudanças locais.

Boa jornada! ✨
