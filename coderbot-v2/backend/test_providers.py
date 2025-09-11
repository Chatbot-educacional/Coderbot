#!/usr/bin/env python3
"""
Script para testar os diferentes provedores de IA suportados pelo CoderBot v2

Uso:
python test_providers.py [provedor] [modelo]

Exemplos:
python test_providers.py ollama llama3.2
python test_providers.py openrouter anthropic/claude-3-5-sonnet
python test_providers.py claude claude-3-5-sonnet-20241022
python test_providers.py openai gpt-4o
"""

import asyncio
import sys
import os
from typing import Optional

# Adicionar o diretório do backend ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.agno_methodology_service import AgnoMethodologyService, MethodologyType

async def test_provider(provider: str, model_id: str):
    """Testa um provedor específico."""

    print(f"🧪 Testando provedor: {provider.upper()}")
    print(f"🤖 Modelo: {model_id}")
    print("-" * 50)

    try:
        # Verificar pré-requisitos
        if provider == "ollama":
            if not os.getenv("OLLAMA_HOST"):
                print("❌ OLLAMA_HOST não configurado")
                return
            print(f"📍 Ollama host: {os.getenv('OLLAMA_HOST')}")

        elif provider == "openrouter":
            if not os.getenv("OPENROUTER_API_KEY"):
                print("❌ OPENROUTER_API_KEY não configurado")
                return
            print("🔑 Open Router API configurado")

        elif provider == "claude":
            if not any([os.getenv("CLAUDE_API_KEY"), os.getenv("ANTHROPIC_API_KEY")]):
                print("❌ CLAUDE_API_KEY ou ANTHROPIC_API_KEY não configurado")
                return
            print("🔑 Claude API configurado")

        elif provider == "openai":
            if not os.getenv("OPEN_AI_API_KEY"):
                print("❌ OPEN_AI_API_KEY não configurado")
                return
            print("🔑 OpenAI API configurado")

        # Criar serviço
        print("🔧 Inicializando serviço AGNO...")
        agno_service = AgnoMethodologyService(model_id=model_id, provider=provider)

        # Testar pergunta simples
        test_query = "Explique o conceito de variável em programação de forma simples."

        print("❓ Fazendo pergunta de teste...")
        print(f"Query: {test_query}")

        import time
        start_time = time.time()

        response = agno_service.ask(
            methodology=MethodologyType.WORKED_EXAMPLES,
            user_query=test_query
        )

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ Resposta gerada! (Tempo: {duration:.2f}s)")
        print("-" * 50)
        print("📝 Resposta:")
        print("-" * 50)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-" * 50)
        print("🎉 Teste concluído com sucesso!")

    except Exception as e:
        print(f"❌ Erro durante o teste: {str(e)}")
        import traceback
        print("Detalhes do erro:")
        traceback.print_exc()

async def list_available_models():
    """Lista modelos disponíveis por provedor."""
    print("📋 Modelos disponíveis por provedor:")
    print("=" * 50)

    try:
        from app.services.agno_models import get_available_models

        models = get_available_models()

        for provider, provider_models in models.items():
            print(f"\n🔧 {provider.upper()}:")
            for model_key, model_id in provider_models.items():
                print(f"   • {model_key}: {model_id}")

    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}")

async def show_usage():
    """Mostra instruções de uso."""
    print("🚀 CoderBot v2 - Teste de Provedores de IA")
    print("=" * 50)
    print()
    print("Uso:")
    print("  python test_providers.py [provedor] [modelo]")
    print()
    print("Exemplos:")
    print("  python test_providers.py ollama llama3.2")
    print("  python test_providers.py openrouter anthropic/claude-3-5-sonnet")
    print("  python test_providers.py claude claude-3-5-sonnet-20241022")
    print("  python test_providers.py openai gpt-4o")
    print()
    print("Listar modelos disponíveis:")
    print("  python test_providers.py --list")
    print()
    print("Provedores suportados:")
    print("  • ollama - Modelos locais via Ollama")
    print("  • openrouter - +100 modelos via Open Router")
    print("  • claude - Modelos Anthropic")
    print("  • openai - Modelos OpenAI")
    print()
    print("Pré-requisitos:")
    print("  • Arquivo .env configurado com chaves de API")
    print("  • Para Ollama: 'ollama serve' rodando")
    print("  • Para Open Router: Chave de API válida")
    print()

async def main():
    """Função principal."""
    if len(sys.argv) < 2:
        await show_usage()
        return

    if sys.argv[1] == "--list":
        await list_available_models()
        return

    if len(sys.argv) < 3:
        print("❌ Erro: Modelo não especificado")
        print()
        await show_usage()
        return

    provider = sys.argv[1].lower()
    model_id = sys.argv[2]

    # Validar provedor
    valid_providers = ["ollama", "openrouter", "claude", "openai"]
    if provider not in valid_providers:
        print(f"❌ Provedor '{provider}' não suportado")
        print(f"Provedores válidos: {', '.join(valid_providers)}")
        return

    await test_provider(provider, model_id)

if __name__ == "__main__":
    asyncio.run(main())
