#!/usr/bin/env python3
"""
Demonstração das Ferramentas Cognitivas e Memory Consolidation Engine

Este script demonstra como usar as novas funcionalidades implementadas:
1. ProblemUnderstandingTool - Análise cognitiva de problemas
2. KnowledgeRecallTool - Recuperação inteligente de conhecimento
3. SolutionExaminationTool - Validação de soluções
4. MemoryConsolidationEngine - Consolidação de memória

Uso:
python examples/cognitive_tools_demo.py
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Adicionar o diretório do backend ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.agno_methodology_service import (
    AgnoMethodologyService,
    ProblemUnderstandingTool,
    KnowledgeRecallTool,
    SolutionExaminationTool,
    CognitiveToolsPipeline,
    MemoryConsolidationEngine,
    CompactInternalState
)
from app.services.rag_service import RAGService

async def demo_problem_understanding():
    """Demonstra a ProblemUnderstandingTool"""
    print("🧠 DEMONSTRAÇÃO: ProblemUnderstandingTool")
    print("=" * 50)

    # Criar ferramenta (sem RAG para demonstração)
    tool = ProblemUnderstandingTool(rag_service=None)

    # Testar diferentes tipos de problemas
    test_queries = [
        "Como resolver x² + 5x + 6 = 0?",
        "Explique o conceito de orientação a objetos",
        "Como funciona uma função recursiva?",
        "Prove que a soma dos ângulos internos de um triângulo é 180°",
        "O que é machine learning?"
    ]

    for query in test_queries:
        print(f"\n🔍 Analisando: '{query}'")
        analysis = tool.analyze(query)

        print(f"   📋 Tipo: {analysis['problem_type']}")
        print(f"   🎯 Conceitos: {', '.join(analysis['key_concepts'])}")
        print(f"   📊 Dificuldade: {analysis['difficulty_level']}")
        print(f"   📚 Metodologia sugerida: {analysis['methodology_hint']}")
        print(f"   🧠 Carga cognitiva: {analysis['cognitive_load']}")
        print(f"   📖 Objetivos: {', '.join(analysis['learning_objectives'])}")

        if analysis['prerequisites']:
            print(f"   📋 Pré-requisitos: {', '.join(analysis['prerequisites'])}")

async def demo_solution_examination():
    """Demonstra a SolutionExaminationTool"""
    print("\n\n🔍 DEMONSTRAÇÃO: SolutionExaminationTool")
    print("=" * 50)

    tool = SolutionExaminationTool()

    # Teste de validação de solução
    problem = "Como resolver x² + 5x + 6 = 0?"
    solution = """
    Para resolver x² + 5x + 6 = 0, podemos usar a fórmula quadrática.
    A fórmula é x = (-b ± √(b² - 4ac)) / 2a

    Neste caso: a = 1, b = 5, c = 6
    x = (-5 ± √(25 - 24)) / 2
    x = (-5 ± √1) / 2
    x = (-5 ± 1) / 2

    Então: x = (-5 + 1) / 2 = -4/2 = -2
    Ou: x = (-5 - 1) / 2 = -6/2 = -3

    Verificação: (-2)² + 5(-2) + 6 = 4 - 10 + 6 = 0 ✓
    """

    context = {
        "problem_type": "quadratic_equation",
        "difficulty": "intermediate",
        "subject": "mathematics"
    }

    print(f"❓ Problema: {problem}")
    print(f"💡 Solução proposta: {solution[:100]}...")
    print("\n🔍 Análise da solução:")

    examination = tool.examine_solution(solution, problem, context)

    print(f"   ✅ Correção: {examination.get('correctness_score', 0.0):.2f}")
    print(f"   📝 Clareza: {examination.get('clarity_score', 0.0):.2f}")
    print(f"   📋 Completude: {examination.get('completeness_score', 0.0):.2f}")
    print(f"   📊 Valor educacional: {examination.get('educational_value', 0.0):.2f}")

    if examination['error_analysis']:
        print("   ⚠️  Erros detectados:")
        for error in examination['error_analysis']:
            print(f"      - {error['description']} ({error['severity']})")

    if examination['improvement_suggestions']:
        print("   💡 Sugestões de melhoria:")
        for suggestion in examination['improvement_suggestions']:
            print(f"      - {suggestion}")

async def demo_memory_consolidation():
    """Demonstra a MemoryConsolidationEngine"""
    print("\n\n🧠 DEMONSTRAÇÃO: MemoryConsolidationEngine")
    print("=" * 50)

    engine = MemoryConsolidationEngine()

    # Simular interações de aprendizado
    interactions = [
        {
            "cognitive_analysis": {
                "problem_analysis": {
                    "key_concepts": ["função", "derivada"],
                    "problem_type": "calculus_problem",
                    "difficulty_level": "advanced"
                }
            },
            "methodology_used": "worked_examples",
            "solution_validation": {
                "solution_analysis": {
                    "correctness_score": 0.9,
                    "completeness_score": 0.8,
                    "clarity_score": 0.7
                }
            }
        },
        {
            "cognitive_analysis": {
                "problem_analysis": {
                    "key_concepts": ["matriz", "determinante"],
                    "problem_type": "linear_algebra",
                    "difficulty_level": "intermediate"
                }
            },
            "methodology_used": "worked_examples",
            "solution_validation": {
                "solution_analysis": {
                    "correctness_score": 0.8,
                    "completeness_score": 0.9,
                    "clarity_score": 0.8
                }
            }
        },
        {
            "cognitive_analysis": {
                "problem_analysis": {
                    "key_concepts": ["função", "recursão"],
                    "problem_type": "programming_problem",
                    "difficulty_level": "intermediate"
                }
            },
            "methodology_used": "scaffolding",
            "solution_validation": {
                "solution_analysis": {
                    "correctness_score": 0.7,
                    "completeness_score": 0.6,
                    "clarity_score": 0.9
                }
            }
        }
    ]

    print("📊 Consolidando interações de aprendizado...")

    for i, interaction in enumerate(interactions, 1):
        print(f"\n🔄 Interação {i}:")
        print(f"   📚 Conceitos: {interaction['cognitive_analysis']['problem_analysis']['key_concepts']}")
        print(f"   🎯 Metodologia: {interaction['methodology_used']}")

        # Consolidar interação
        consolidated_state = engine.consolidate_interaction(
            engine.compact_state,
            interaction
        )

        # Mostrar estatísticas
        stats = engine.get_memory_stats(consolidated_state)
        print(f"   📈 Estado após consolidação:")
        print(f"      • Conceitos aprendidos: {stats['learned_concepts_count']}")
        print(f"      • Marcadores de progresso: {stats['progress_markers_count']}")
        print(f"      • Preferências: {stats['methodology_preferences_count']}")

    print("
🎯 Estado final consolidado:"    final_stats = engine.get_memory_stats(engine.compact_state)
    print(f"   📚 Conceitos únicos aprendidos: {final_stats['learned_concepts_count']}")
    print(f"   📊 Marcadores de progresso: {final_stats['progress_markers_count']}")
    print(f"   🎯 Preferências de metodologia: {engine.compact_state.methodology_preferences}")
    print(f"   🧠 Contexto comprimido: {len(engine.compact_state.session_context)} caracteres")

async def demo_cognitive_pipeline():
    """Demonstra o CognitiveToolsPipeline completo"""
    print("\n\n🔄 DEMONSTRAÇÃO: CognitiveToolsPipeline")
    print("=" * 50)

    # Simular pipeline sem RAG (usando None)
    pipeline = CognitiveToolsPipeline(rag_service=None, agno_service=None)

    test_query = "Como implementar uma função recursiva para calcular fatorial em Python?"

    print(f"❓ Query: {test_query}")
    print("\n🔍 Processando através do pipeline cognitivo...")

    # Processar query
    cognitive_analysis = pipeline.process_query(test_query)

    print("\n📊 Resultado da análise cognitiva:")
        print(f"   🎯 Metodologia sugerida: {cognitive_analysis.get('suggested_methodology', 'N/A')}")
    print(f"   🧠 Carga cognitiva: {cognitive_analysis.get('cognitive_load', 'N/A')}")
    print(f"   📖 Objetivos de aprendizagem: {cognitive_analysis.get('learning_objectives', [])}")

    if 'problem_analysis' in cognitive_analysis:
        analysis = cognitive_analysis['problem_analysis']
        print(f"   📋 Tipo de problema: {analysis.get('problem_type', 'N/A')}")
        print(f"   🎯 Conceitos-chave: {analysis.get('key_concepts', [])}")
        print(f"   📊 Dificuldade: {analysis.get('difficulty_level', 'N/A')}")

    # Simular validação de solução
    mock_solution = """
    def fatorial(n):
        if n <= 1:
            return 1
        else:
            return n * fatorial(n-1)

    # Exemplo de uso
    print(fatorial(5))  # Saída: 120
    """

    print("\n🔍 Validando solução proposta...")
    validation_result = pipeline.validate_solution(
        mock_solution,
        test_query,
        cognitive_analysis.get('problem_analysis', {})
    )

    print("\n📊 Resultado da validação:")
    if 'solution_analysis' in validation_result:
        analysis = validation_result['solution_analysis']
        # If 'educational_value' is a float, format with .2f, else print as is
        educational_value = analysis.get('educational_value', 'N/A')
        if isinstance(educational_value, float):
            print(f"   📊 Valor educacional: {educational_value:.2f}")
        else:
            print(f"   📊 Valor educacional: {educational_value}")

        if analysis.get('improvement_suggestions'):
            print("   💡 Sugestões:")
            for suggestion in analysis['improvement_suggestions'][:2]:
                print(f"      • {suggestion}")

async def demo_integration_with_agno():
    """Demonstra integração com AgnoMethodologyService"""
    print("\n\n🔗 DEMONSTRAÇÃO: Integração com AgnoMethodologyService")
    print("=" * 50)

    # Nota: Esta demonstração requer configuração completa do ambiente
    print("⚠️  Para esta demonstração completa, é necessário:")
    print("   • RAG Service configurado")
    print("   • Base de dados vetorial (Qdrant)")
    print("   • Chaves de API configuradas")
    print()
    print("📝 Exemplo de uso integrado:")
    print("""
    # 1. Configurar serviço AGNO
    agno_service = AgnoMethodologyService(model_id="llama3.2", provider="ollama")

    # 2. Configurar RAG (ativa ferramentas cognitivas)
    rag_service = RAGService()
    agno_service.set_rag_service(rag_service)

    # 3. Usar com análise cognitiva automática
    response = await agno_service.ask(
        methodology=MethodologyType.WORKED_EXAMPLES,
        user_query="Como funciona recursão?"
    )

    # 4. Verificar consolidação de memória
    memory_stats = agno_service.get_memory_stats()
    """)

async def demo_methodology_control():
    """Demonstra os diferentes modos de controle de metodologia"""
    print("\n\n🎯 DEMONSTRAÇÃO: Controle de Metodologia")
    print("=" * 50)

    print("📋 Cenário: Usuário quer especificamente Worked Examples")
    print("❓ Query: 'Como resolver x² + 5x + 6 = 0?'")
    print()

    # Simular análise cognitiva
    print("🧠 Análise Cognitiva sugeriria:")
    print("   • Tipo: quadratic_equation")
    print("   • Metodologia sugerida: worked_examples ✅")
    print("   • Mas vamos simular uma sugestão diferente para demonstração...")
    print()

    print("🔄 Cenário 1: MODO FIXO (Mantém escolha do usuário)")
    print("   Usuário escolheu: worked_examples")
    print("   Sistema mantém: worked_examples ✅")
    print("   Resultado: Resposta sempre em Worked Examples")
    print()

    print("🔄 Cenário 2: MODO ADAPTATIVO (Inteligente)")
    print("   Usuário sugeriu: worked_examples")
    print("   Sistema pode alterar: scaffolding (se análise sugerir)")
    print("   Resultado: Adaptação baseada em análise cognitiva")
    print()

    print("🔄 Cenário 3: APENAS SUGESTÃO (Usuário decide)")
    print("   Sistema apenas sugere: scaffolding")
    print("   Usuário pode aceitar ou rejeitar")
    print("   Resultado: Controle total do usuário")
    print()

    print("📊 Comparação:")
    print("┌─────────────────┬─────────────────────┬─────────────────────┐")
    print("│ Modo           │ Alteração Automática │ Controle do Usuário │")
    print("├─────────────────┼─────────────────────┼─────────────────────┤")
    print("│ Fixo          │ ❌ Não              │ ✅ Total            │")
    print("│ Adaptativo    │ ✅ Sim              │ ⚠️  Parcial         │")
    print("│ Sugestão      │ ❌ Não              │ ✅ Total            │")
    print("└─────────────────┴─────────────────────┴─────────────────────┘")

async def demo_api_endpoints():
    """Demonstra os novos endpoints de API"""
    print("\n\n🔗 DEMONSTRAÇÃO: Novos Endpoints de API")
    print("=" * 50)

    print("📡 Endpoints de Controle de Metodologia:")
    print()
    print("1️⃣  POST /agno/ask/fixed-methodology")
    print("   • Mantém exatamente a metodologia escolhida")
    print("   • Não permite alteração cognitiva")
    print("   • Uso: Quando usuário quer controle total")
    print()

    print("2️⃣  POST /agno/ask/adaptive")
    print("   • Permite adaptação baseada na análise")
    print("   • Sistema otimiza automaticamente")
    print("   • Uso: Quando usuário quer inteligência")
    print()

    print("3️⃣  POST /agno/cognitive/suggest")
    print("   • Apenas retorna sugestão cognitiva")
    print("   • Não processa a pergunta")
    print("   • Uso: Para decisão consciente do usuário")
    print()

    print("📡 Endpoints de Context Engineering:")
    print()
    print("4️⃣  POST /agno/cognitive/analyze")
    print("   • Análise cognitiva completa")
    print("   • Extração de conceitos e dificuldade")
    print("   • Sugestão de metodologia otimizada")
    print()

    print("5️⃣  POST /agno/cognitive/validate-solution")
    print("   • Validação automática de soluções")
    print("   • Scores de qualidade e completude")
    print("   • Sugestões de melhoria")
    print()

    print("6️⃣  GET /agno/memory/stats")
    print("   • Estatísticas da memória consolidada")
    print("   • Contagem de conceitos aprendidos")
    print("   • Estado atual da consolidação")
    print()

    print("💡 Dica: Use /agno/cognitive/suggest antes de escolher o endpoint!")

async def main():
    """Função principal da demonstração"""
    print("🚀 CoderBot v2 - Demonstração Completa de Context Engineering")
    print("=" * 80)
    print("Este script demonstra TODAS as funcionalidades implementadas:")
    print("• 🧠 ProblemUnderstandingTool - Análise inteligente de problemas")
    print("• 🔍 SolutionExaminationTool - Validação automática de soluções")
    print("• 🧠 MemoryConsolidationEngine - Consolidação inteligente de memória")
    print("• 🔄 CognitiveToolsPipeline - Orquestração completa")
    print("• 🎯 Methodology Control - Controle de estratégia de ensino")
    print("• 📡 API Endpoints - Novos endpoints especializados")
    print("=" * 80)

    try:
        # Executar demonstrações
        await demo_problem_understanding()
        await demo_solution_examination()
        await demo_memory_consolidation()
        await demo_cognitive_pipeline()
        await demo_integration_with_agno()

        print("\n\n🎉 Demonstração concluída com sucesso!")
        print("\n📚 As ferramentas cognitivas estão agora disponíveis em:")
        print("   • AgnoMethodologyService.analyze_query_cognitively()")
        print("   • AgnoMethodologyService.validate_solution_cognitively()")
        print("   • AgnoMethodologyService.consolidate_memory()")
        print("   • API endpoints: /agno/cognitive/* e /agno/memory/*")

        # Executar demonstrações adicionais
        await demo_methodology_control()
        await demo_api_endpoints()

        print("\n🎯 RESPOSTA À SUA PERGUNTA:")
        print("✅ SIM! Usuário pode fazer request específica de worked examples")
        print("✅ Sistema respeita escolha - não altera estratégia automaticamente")
        print("✅ Use: POST /agno/ask/fixed-methodology com methodology=worked_examples")
        print()
        print("🔧 Modos disponíveis:")
        print("   • ask_with_fixed_methodology() - Mantém EXATAMENTE a escolha")
        print("   • ask_with_cognitive_adaptation() - Permite adaptação inteligente")
        print("   • get_cognitive_suggestion() - Apenas mostra sugestão")

    except Exception as e:
        print(f"\n❌ Erro durante demonstração: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
