from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Configurações do DeepSeek
    deep_seek_api_key: str = Field(..., env="DEEP_SEEK_API_KEY")
    deep_seek_api_url: str = Field("https://api.deepseek.com/v1", env="DEEP_SEEK_API_URL")

    # Configurações do Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")

    # Configuração do PocketBase
    pocketbase_url: str = Field(..., env="POCKETBASE_URL")
    pocketbase_user_email: str = Field(..., env="POCKETBASE_USER_EMAIL")
    pocketbase_user_password: str = Field(..., env="POCKETBASE_USER_PASSWORD")
    
    # Configurações de administrador do PocketBase (para gerenciamento de prompts)
    pocketbase_admin_email: str = Field(..., env="POCKETBASE_ADMIN_EMAIL")
    pocketbase_admin_password: str = Field(..., env="POCKETBASE_ADMIN_PASSWORD")
    
    # Configurações de Providers de IA
    open_ai_api_key: str = Field(..., env="OPEN_AI_API_KEY")
    openai_api_url: str = Field("https://api.openai.com/v1", env="OPENAI_API_URL")
    
    # Configuração do Claude (Anthropic)
    claude_api_key: str = Field("", env="CLAUDE_API_KEY")
    claude_api_url: str = Field("https://api.anthropic.com", env="CLAUDE_API_URL")

    # Configuração do Open Router
    openrouter_api_key: str = Field("", env="OPENROUTER_API_KEY")
    openrouter_api_url: str = Field("https://openrouter.ai/api/v1", env="OPENROUTER_API_URL")

    # Configuração do Ollama (local)
    ollama_host: str = Field("http://localhost:11434", env="OLLAMA_HOST")
    ollama_timeout: int = Field(120, env="OLLAMA_TIMEOUT")

    # Qdrant Vector Database
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: str = Field("", env="QDRANT_API_KEY")

    # Outros
    rapidapi_key: str = Field(..., env="RAPIDAPI_KEY")

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        from_attributes = True
        extra = "ignore"  # Ignora campos extras para evitar erros de validação

settings = Settings()
