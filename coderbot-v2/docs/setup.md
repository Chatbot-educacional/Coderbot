# Setup do CoderBot v2 com Docker

Este guia rápido utiliza o arquivo `docker-compose.optimized.yml` para iniciar todos os serviços.

## Pré-requisitos

- Docker e Docker Compose v2
- Git
- Node.js e pnpm (opcional para build local)

## Passos para rodar o sistema

1. **Clone o repositório:**
   ```bash
   git clone <seu-repositorio>
   cd coderbot-v2
   ```

2. **Configure o arquivo `.env`:**
   ```bash
   cp .env.example .env
   # edite as variáveis obrigatórias
   ```

3. **(Opcional) Compile o frontend:**
   ```bash
   cd frontend
   pnpm install --frozen-lockfile
   pnpm run build
   cd ..
   ```

4. **Inicie os serviços:**
   ```bash
   docker compose -f docker-compose.optimized.yml up -d --build
   ```

5. **Acesse os serviços:**
   - App: <http://localhost:3001>
   - Backend: <http://localhost:8000>
   - PocketBase: <http://localhost:8090>

## Comandos úteis

- Ver logs: `docker compose -f docker-compose.optimized.yml logs -f`
- Parar serviços: `docker compose -f docker-compose.optimized.yml down`
- Reiniciar serviço específico: `docker compose -f docker-compose.optimized.yml restart <serviço>`

## Dicas

- Nunca commite seu `.env`.
- Para reset total: `docker compose -f docker-compose.optimized.yml down -v --remove-orphans`

