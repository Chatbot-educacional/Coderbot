"""
Exemplo de uso do sistema RAG integrado com o CoderBot v2

Este script demonstra como:
1. Indexar conteúdo educacional no Qdrant
2. Realizar buscas RAG
3. Usar agentes educacionais personalizados
4. Integrar com o sistema AGNO existente
5. Usar diferentes provedores de IA (OpenAI, Claude, Ollama, Open Router)

Para executar:
python examples/rag_example.py

Pré-requisitos:
- Para Ollama: Instalar Ollama e executar 'ollama serve'
- Para Open Router: Obter chave da API em https://openrouter.ai/
- Configurar variáveis de ambiente no arquivo .env
"""

import asyncio
import json
import os
from app.services.rag_service import RAGService, EducationalContent
from app.services.educational_agent_service import EducationalAgentService, StudentProfile
from app.services.agno_methodology_service import AgnoMethodologyService

async def demo_rag_system():
    """Demonstração completa do sistema RAG educacional."""

    print("🚀 Iniciando demonstração do sistema RAG educacional\n")

    # 1. Inicializar serviços
    print("1️⃣ Inicializando serviços...")
    rag_service = RAGService()
    agno_service = AgnoMethodologyService()
    agent_service = EducationalAgentService(rag_service, agno_service)

    # Aguardar inicialização da coleção Qdrant
    await asyncio.sleep(2)

    print("✅ Serviços inicializados\n")

    # 2. Indexar conteúdo educacional de exemplo
    print("2️⃣ Indexando conteúdo educacional...")

    sample_content = [
        EducationalContent(
            id="algoritmos-intro",
            title="Introdução aos Algoritmos",
            content="""
            Algoritmos são sequências finitas de passos bem definidos para resolver um problema.
            Um algoritmo deve ter as seguintes características:

            1. **Finitude**: Deve terminar após um número finito de passos
            2. **Definição**: Cada passo deve ser definido de forma precisa
            3. **Entrada**: Pode receber dados de entrada
            4. **Saída**: Deve produzir um resultado
            5. **Efetividade**: Deve ser executável por uma máquina

            Exemplos comuns de algoritmos incluem:
            - Receitas de culinária
            - Instruções de montagem
            - Procedimentos médicos
            - Programas de computador

            Na programação, algoritmos são implementados usando estruturas de controle como:
            - Sequência (execução linear)
            - Seleção (if/else)
            - Iteração (loops while/for)
            """,
            content_type="lesson",
            subject="programação",
            topic="algoritmos",
            difficulty="beginner",
            tags=["algoritmos", "programação", "lógica", "introdução"]
        ),

        EducationalContent(
            id="funcoes-matematicas",
            title="Funções Matemáticas: Conceitos Básicos",
            content="""
            Uma função matemática é uma relação entre dois conjuntos que associa a cada elemento
            do primeiro conjunto exatamente um elemento do segundo conjunto.

            **Definição Formal:**
            Uma função f: A → B é uma relação que associa cada elemento x ∈ A a um único elemento y ∈ B.

            **Elementos de uma função:**
            - **Domínio**: Conjunto de valores de entrada (x)
            - **Contra-domínio**: Conjunto onde os valores de saída estão contidos
            - **Imagem**: Conjunto dos valores de saída efetivamente atingidos
            - **Gráfico**: Conjunto de pontos (x, f(x))

            **Propriedades importantes:**
            - Injetora (injetiva): Cada y tem no máximo um x
            - Sobrejetora (sobrejetiva): Todo y do contra-domínio é atingido
            - Bijetora: Injetora e sobrejetiva simultaneamente

            **Exemplos:**
            - f(x) = 2x + 1 (função linear)
            - f(x) = x² (função quadrática)
            - f(x) = sin(x) (função trigonométrica)
            """,
            content_type="theory",
            subject="matemática",
            topic="funções",
            difficulty="intermediate",
            tags=["funções", "matemática", "álgebra", "conceitos"]
        ),

        EducationalContent(
            id="programacao-python",
            title="Primeiros Passos em Python",
            content="""
            Python é uma linguagem de programação de alto nível, interpretada e multiparadigmática.

            **Sintaxe Básica:**

            ```python
            # Comentários começam com #
            print("Olá, mundo!")  # Saída: Olá, mundo!

            # Variáveis
            nome = "João"
            idade = 25
            altura = 1.75

            # Estruturas condicionais
            if idade >= 18:
                print("Maior de idade")
            else:
                print("Menor de idade")

            # Loops
            for i in range(5):
                print(f"Número: {i}")

            # Funções
            def saudacao(nome):
                return f"Olá, {nome}!"

            # Listas
            frutas = ["maçã", "banana", "laranja"]
            frutas.append("uva")
            ```

            **Conceitos Fundamentais:**
            - **Variáveis**: Armazenam dados
            - **Tipos**: int, float, str, bool, list, dict
            - **Operadores**: +, -, *, /, %, ==, !=, <, >, <=, >=
            - **Estruturas de controle**: if/elif/else, for, while
            - **Funções**: Definem comportamentos reutilizáveis
            """,
            content_type="tutorial",
            subject="programação",
            topic="python",
            difficulty="beginner",
            tags=["python", "programação", "sintaxe", "iniciante"]
        )
    ]

    for content in sample_content:
        await rag_service.index_content(content)
        print(f"✅ Indexado: {content.title}")

    print("\n✅ Conteúdo educacional indexado\n")

    # 3. Demonstrar busca RAG
    print("3️⃣ Demonstrando busca RAG...")

    search_queries = [
        "Como funciona um algoritmo?",
        "O que é uma função matemática?",
        "Como começar a programar em Python?"
    ]

    for query in search_queries:
        print(f"\n🔍 Busca: '{query}'")
        results = await rag_service.search_content(
            type('SearchQuery', (), {
                'query': query,
                'limit': 2,
                'score_threshold': 0.6
            })()
        )

        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.content.title} (score: {result.score:.2f})")
            print(f"     📄 {result.context_snippet[:100]}...")

    print("\n✅ Demonstração de busca concluída\n")

    # 4. Demonstrar agente educacional
    print("4️⃣ Demonstrando agente educacional personalizado...")

    # Criar perfil de estudante
    student_profile = StudentProfile(
        user_id="demo_student_001",
        name="João Silva",
        learning_style="visual",
        current_level="beginner",
        subjects=["programação", "matemática"],
        preferred_methodologies=["worked_examples", "sequential_thinking"],
        learning_goals=["Aprender Python", "Entender algoritmos"],
        learning_pace="moderate"
    )

    # Consulta educacional
    educational_query = "Como posso criar um algoritmo simples para calcular a média de uma lista de números?"

    print(f"👤 Estudante: {student_profile.name}")
    print(f"🎯 Consulta: {educational_query}")
    print(f"📚 Perfil: {student_profile.learning_style}, nível {student_profile.current_level}")

    # Processar com agente educacional
    response = await agent_service.process_educational_query(
        query=educational_query,
        user_id=student_profile.user_id,
        user_profile={
            "learning_style": student_profile.learning_style,
            "current_level": student_profile.current_level,
            "subjects": student_profile.subjects,
            "preferred_methodologies": student_profile.preferred_methodologies
        }
    )

    print("
🤖 Resposta do Agente Educacional:"    print(f"📝 Metodologia usada: {response.methodology_used}")
    print(f"🎯 Pontuação de personalização: {response.personalization_score:.2f}")
    print(f"💬 Pontuação de engajamento: {response.engagement_score:.2f}")
    print("
💡 Ações recomendadas:"    for action in response.recommended_actions[:3]:
        print(f"   • {action}")

    print("
📈 Próximos tópicos sugeridos:"    for topic in response.next_topics[:3]:
        print(f"   • {topic}")

    print(f"\n📄 Resposta completa:\n{response.response[:500]}...\n")

    # 5. Demonstrar integração com AGNO
    print("5️⃣ Demonstrando integração com sistema AGNO existente...")

    # Usar AGNO diretamente com contexto RAG
    rag_context = await rag_service.build_rag_context(
        query=educational_query,
        user_context={
            "learning_style": "visual",
            "difficulty": "beginner"
        }
    )

    print(f"📊 Contexto RAG construído:")
    print(f"   • {len(rag_context.retrieved_content)} documentos recuperados")
    print(f"   • {rag_context.context_tokens} tokens de contexto")
    print(f"   • Score de relevância: {rag_context.relevance_score:.2f}")

    print("\n✅ Demonstração completa do sistema RAG educacional concluída!")
    print("\n🎉 O sistema agora oferece:")
    print("   • Busca semântica inteligente de conteúdo educacional")
    print("   • Personalização baseada em perfil do estudante")
    print("   • Context engineering avançado")
    print("   • Integração perfeita com metodologias AGNO")
    print("   • Suporte a múltiplos provedores de IA (OpenAI, Claude, Ollama, Open Router)")

if __name__ == "__main__":
    asyncio.run(demo_rag_system())

async def demo_multiple_providers():
    """Demonstração de uso com diferentes provedores de IA."""

    print("\n🔄 Demonstrando suporte a múltiplos provedores de IA\n")

    providers_to_test = [
        ("claude", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("ollama", "llama3.2"),
        ("openrouter", "anthropic/claude-3-5-sonnet")
    ]

    test_query = "Explique o conceito de recursão em programação de forma simples"

    for provider, model in providers_to_test:
        try:
            print(f"\n🤖 Testando provedor: {provider.upper()} com modelo {model}")

            # Verificar se as chaves estão configuradas
            if provider == "ollama" and not os.getenv("OLLAMA_HOST"):
                print(f"   ⚠️  Ollama não configurado (OLLAMA_HOST), pulando...")
                continue
            elif provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
                print(f"   ⚠️  Open Router não configurado (OPENROUTER_API_KEY), pulando...")
                continue
            elif provider in ["claude", "openai"] and not any([
                os.getenv("CLAUDE_API_KEY"),
                os.getenv("OPEN_AI_API_KEY")
            ]):
                print(f"   ⚠️  {provider.upper()} não configurado, pulando...")
                continue

            # Criar serviço AGNO com o provedor específico
            agno_service = AgnoMethodologyService(model_id=model, provider=provider)

            # Fazer uma pergunta de teste
            start_time = asyncio.get_event_loop().time()
            response = agno_service.ask(
                methodology=agno_service._get_methodology_from_string("worked_examples"),
                user_query=test_query
            )
            end_time = asyncio.get_event_loop().time()

            print(f"   ✅ Resposta gerada em {end_time - start_time:.2f}s")
            print(f"   📝 Resposta: {response[:100]}...")

        except Exception as e:
            print(f"   ❌ Erro com {provider}: {str(e)}")

    print("\n🎯 Para usar um provedor específico na API:")
    print("   POST /agno/ask?provider=ollama&model_id=llama3.2")
    print("   POST /agno/ask?provider=openrouter&model_id=anthropic/claude-3-5-sonnet")
    print("   • Recomendações pedagógicas automáticas")

if __name__ == "__main__":
    asyncio.run(demo_rag_system())
