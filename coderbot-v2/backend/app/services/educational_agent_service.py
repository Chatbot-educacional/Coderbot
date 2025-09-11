"""
Educational AI Agent Service

Este serviço implementa agentes de IA especializados para educação,
utilizando RAG para fornecer respostas personalizadas e contextualmente
relevantes baseadas no perfil do estudante e histórico de aprendizado.

Características principais:
- Agentes especializados por metodologia educacional
- Personalização baseada em perfil do estudante
- Memória de sessão inteligente
- Adptação dinâmica de dificuldade
- Avaliação contínua de progresso
- Recomendações pedagógicas inteligentes
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import asyncio
import json
import logging
import uuid
from enum import Enum

from pydantic import BaseModel, Field
import numpy as np

from app.services.agno_methodology_service import AgnoMethodologyService, MethodologyType
from app.services.rag_service import RAGService, RAGContext, EducationalContent
from app.config import settings

logger = logging.getLogger(__name__)

class StudentProfile(BaseModel):
    """Perfil detalhado do estudante."""
    user_id: str
    name: Optional[str] = None
    learning_style: str = Field(default="visual", description="Estilo de aprendizado predominante")
    current_level: str = Field(default="intermediate", description="Nível atual de conhecimento")
    subjects: List[str] = Field(default_factory=list, description="Matérias de interesse")
    preferred_methodologies: List[str] = Field(default_factory=list, description="Metodologias preferidas")
    learning_goals: List[str] = Field(default_factory=list, description="Objetivos de aprendizado")
    past_performance: Dict[str, float] = Field(default_factory=dict, description="Performance histórica por tópico")
    learning_pace: str = Field(default="moderate", description="Ritmo de aprendizado")
    preferred_difficulty: str = Field(default="adaptive", description="Preferência de dificuldade")
    accessibility_needs: List[str] = Field(default_factory=list, description="Necessidades de acessibilidade")

class SessionContext(BaseModel):
    """Contexto da sessão de aprendizado atual."""
    session_id: str
    current_topic: str
    sub_topics: List[str] = Field(default_factory=list)
    completed_topics: List[str] = Field(default_factory=list)
    current_methodology: str
    session_start: datetime = Field(default_factory=datetime.utcnow)
    interaction_count: int = 0
    average_engagement: float = 0.0
    current_difficulty: str = "intermediate"
    learning_objectives: List[str] = Field(default_factory=list)
    progress_metrics: Dict[str, Any] = Field(default_factory=dict)

class AgentResponse(BaseModel):
    """Resposta estruturada do agente educacional."""
    response: str
    methodology_used: str
    personalization_score: float = Field(description="Pontuação de personalização (0-1)")
    engagement_score: float = Field(description="Pontuação de engajamento estimada")
    recommended_actions: List[str] = Field(default_factory=list, description="Ações recomendadas para o estudante")
    next_topics: List[str] = Field(default_factory=list, description="Próximos tópicos sugeridos")
    difficulty_adjustment: Optional[str] = Field(description="Ajuste de dificuldade recomendado")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")

class EducationalAgent:
    """
    Agente de IA especializado para educação.

    Características:
    - Personalização baseada em perfil do estudante
    - Adaptação dinâmica de metodologia
    - Gerenciamento inteligente de contexto
    - Avaliação contínua de progresso
    - Recomendações pedagógicas
    """

    def __init__(self, rag_service: RAGService, agno_service: AgnoMethodologyService):
        self.rag_service = rag_service
        self.agno_service = agno_service

        # Configurações de personalização
        self.personalization_weights = {
            "learning_style": 0.3,
            "past_performance": 0.25,
            "learning_pace": 0.2,
            "methodology_preference": 0.15,
            "engagement_history": 0.1
        }

        # Configurações de adaptação
        self.difficulty_levels = ["beginner", "intermediate", "advanced"]
        self.adaptation_threshold = 0.7  # Threshold para mudança de dificuldade
        self.engagement_decay = 0.9  # Fator de decaimento para engajamento

    async def process_query(
        self,
        query: str,
        student_profile: StudentProfile,
        session_context: Optional[SessionContext] = None
    ) -> AgentResponse:
        """
        Processa uma consulta educacional com personalização completa.

        Args:
            query: Pergunta ou problema do estudante
            student_profile: Perfil detalhado do estudante
            session_context: Contexto da sessão atual

        Returns:
            AgentResponse: Resposta personalizada e estruturada
        """
        try:
            # 1. Selecionar metodologia mais apropriada
            methodology = await self._select_optimal_methodology(
                query, student_profile, session_context
            )

            # 2. Construir contexto RAG inteligente
            user_context = self._build_user_context(student_profile)
            rag_context = await self.rag_service.build_rag_context(
                query=query,
                user_context=user_context,
                session_context=session_context.dict() if session_context else None,
                methodology=methodology
            )

            # 3. Augmentar contexto com personalização
            augmented_context = await self._augment_context_with_personalization(
                rag_context, student_profile, session_context
            )

            # 4. Gerar resposta usando AGNO
            agno_response = self.agno_service.ask(
                methodology=methodology,
                user_query=query,
                context=augmented_context
            )

            # 5. Pós-processar resposta com recomendações
            processed_response = await self._post_process_response(
                agno_response, student_profile, session_context, methodology
            )

            # 6. Calcular métricas de personalização e engajamento
            personalization_score = self._calculate_personalization_score(
                student_profile, methodology, rag_context
            )

            engagement_score = self._estimate_engagement_score(
                processed_response, student_profile
            )

            # 7. Gerar recomendações pedagógicas
            recommendations = await self._generate_pedagogical_recommendations(
                student_profile, session_context, processed_response
            )

            response = AgentResponse(
                response=processed_response,
                methodology_used=methodology.value,
                personalization_score=personalization_score,
                engagement_score=engagement_score,
                recommended_actions=recommendations.get("actions", []),
                next_topics=recommendations.get("next_topics", []),
                difficulty_adjustment=recommendations.get("difficulty_adjustment"),
                metadata={
                    "rag_context_used": len(rag_context.retrieved_content),
                    "context_tokens": rag_context.context_tokens,
                    "relevance_score": rag_context.relevance_score,
                    "processing_time": recommendations.get("processing_time", 0)
                }
            )

            logger.info(f"Resposta do agente gerada: método={methodology.value}, "
                       f"personalização={personalization_score:.2f}, "
                       f"engajamento={engagement_score:.2f}")

            return response

        except Exception as e:
            logger.error(f"Erro no processamento da consulta: {e}")
            raise

    async def _select_optimal_methodology(
        self,
        query: str,
        student_profile: StudentProfile,
        session_context: Optional[SessionContext]
    ) -> MethodologyType:
        """
        Seleciona a metodologia mais apropriada baseada no perfil do estudante
        e contexto da consulta.
        """
        # Preferências do estudante
        preferred = student_profile.preferred_methodologies
        if preferred:
            # Mapear preferências para MethodologyType
            preferred_enum = []
            for pref in preferred:
                try:
                    preferred_enum.append(MethodologyType(pref))
                except ValueError:
                    continue

            if preferred_enum:
                return preferred_enum[0]  # Retorna primeira preferência válida

        # Análise baseada no tipo de consulta
        query_lower = query.lower()

        # Consultas que pedem explicação passo-a-passo
        if any(word in query_lower for word in ["como", "passo", "sequência", "ordem"]):
            return MethodologyType.SEQUENTIAL_THINKING

        # Consultas que envolvem exemplos
        if any(word in query_lower for word in ["exemplo", "exercício", "prática"]):
            return MethodologyType.WORKED_EXAMPLES

        # Consultas que pedem analogias
        if any(word in query_lower for word in ["como", "parecido", "similar", "analogia"]):
            return MethodologyType.ANALOGY

        # Consultas que estimulam reflexão crítica
        if any(word in query_lower for word in ["por que", "explica", "justifica", "razão"]):
            return MethodologyType.SOCRATIC

        # Consultas de iniciantes
        if student_profile.current_level == "beginner":
            return MethodologyType.SCAFFOLDING

        # Padrão baseado no progresso
        if session_context and session_context.interaction_count > 5:
            # Se já teve muitas interações, tentar método diferente
            return MethodologyType.SOCRATIC
        else:
            return MethodologyType.WORKED_EXAMPLES

    def _build_user_context(self, student_profile: StudentProfile) -> Dict[str, Any]:
        """Constrói contexto do usuário para busca RAG."""
        return {
            "user_id": student_profile.user_id,
            "learning_style": student_profile.learning_style,
            "difficulty": student_profile.preferred_difficulty,
            "subjects": student_profile.subjects,
            "current_level": student_profile.current_level,
            "past_performance": student_profile.past_performance,
            "learning_goals": student_profile.learning_goals
        }

    async def _augment_context_with_personalization(
        self,
        rag_context: RAGContext,
        student_profile: StudentProfile,
        session_context: Optional[SessionContext]
    ) -> str:
        """
        Augmenta o contexto RAG com informações de personalização
        específicas do estudante.
        """
        context_parts = [rag_context.compressed_context]

        # Adicionar informações do perfil
        profile_info = []

        if student_profile.learning_style:
            profile_info.append(f"Estilo de aprendizado: {student_profile.learning_style}")

        if student_profile.current_level:
            profile_info.append(f"Nível atual: {student_profile.current_level}")

        if student_profile.learning_goals:
            profile_info.append(f"Objetivos: {', '.join(student_profile.learning_goals[:3])}")

        if profile_info:
            context_parts.append("## Informações do Estudante\n" + "\n".join(profile_info))

        # Adicionar contexto da sessão
        if session_context:
            session_info = [
                f"Tópico atual: {session_context.current_topic}",
                f"Interações nesta sessão: {session_context.interaction_count}",
                f"Metodologia atual: {session_context.current_methodology}",
                f"Dificuldade atual: {session_context.current_difficulty}"
            ]

            if session_context.completed_topics:
                session_info.append(f"Tópicos concluídos: {', '.join(session_context.completed_topics[-3:])}")

            context_parts.append("## Contexto da Sessão\n" + "\n".join(session_info))

        # Adicionar dicas de personalização baseadas no perfil
        personalization_tips = self._generate_personalization_tips(student_profile)
        if personalization_tips:
            context_parts.append("## Dicas de Ensino Personalizadas\n" + personalization_tips)

        return "\n\n".join(context_parts)

    def _generate_personalization_tips(self, student_profile: StudentProfile) -> str:
        """Gera dicas de personalização baseadas no perfil do estudante."""
        tips = []

        # Dicas baseadas no estilo de aprendizado
        if student_profile.learning_style == "visual":
            tips.append("- Use diagramas, gráficos e exemplos visuais")
            tips.append("- Forneça mapas mentais e representações visuais")
        elif student_profile.learning_style == "auditory":
            tips.append("- Use explicações verbais e discussões")
            tips.append("- Incentive a verbalização de conceitos")
        elif student_profile.learning_style == "kinesthetic":
            tips.append("- Inclua atividades práticas e exercícios hands-on")
            tips.append("- Use analogias do mundo real")

        # Dicas baseadas no nível
        if student_profile.current_level == "beginner":
            tips.append("- Explique conceitos básicos primeiro")
            tips.append("- Use analogias simples e exemplos do dia a dia")
        elif student_profile.current_level == "advanced":
            tips.append("- Foque em aplicações avançadas e casos complexos")
            tips.append("- Incentive análise crítica e resolução de problemas")

        # Dicas baseadas no ritmo
        if student_profile.learning_pace == "fast":
            tips.append("- Mantenha ritmo dinâmico e desafiador")
            tips.append("- Introduza novos conceitos rapidamente")
        elif student_profile.learning_pace == "slow":
            tips.append("- Permita tempo extra para assimilação")
            tips.append("- Reforce conceitos com múltiplas explicações")

        return "\n".join(tips)

    async def _post_process_response(
        self,
        raw_response: str,
        student_profile: StudentProfile,
        session_context: Optional[SessionContext],
        methodology: MethodologyType
    ) -> str:
        """
        Pós-processa a resposta AGNO adicionando elementos de personalização
        e recomendações específicas.
        """
        processed_response = raw_response

        # Adicionar seção de reflexão personalizada se for estudante avançado
        if student_profile.current_level == "advanced":
            reflection_prompt = "\n\n## Reflexão Crítica\nConsidere: Como você aplicaria este conceito em um projeto real da sua área?"
            processed_response += reflection_prompt

        # Adicionar exercícios práticos para estudantes kinestéticos
        if student_profile.learning_style == "kinesthetic":
            practice_prompt = "\n\n## Prática Sugerida\nTente implementar um pequeno exemplo prático baseado neste conceito."
            processed_response += practice_prompt

        return processed_response

    def _calculate_personalization_score(
        self,
        student_profile: StudentProfile,
        methodology: MethodologyType,
        rag_context: RAGContext
    ) -> float:
        """Calcula pontuação de personalização da resposta."""
        score = 0.0

        # Verificar se metodologia está nas preferências
        if methodology.value in student_profile.preferred_methodologies:
            score += self.personalization_weights["methodology_preference"]

        # Verificar se conteúdo é relevante ao nível
        relevant_content = [
            r for r in rag_context.retrieved_content
            if r.content.difficulty == student_profile.current_level
        ]
        if relevant_content:
            score += 0.2

        # Verificar se assuntos são relevantes
        relevant_subjects = [
            r for r in rag_context.retrieved_content
            if r.content.subject in student_profile.subjects
        ]
        if relevant_subjects:
            score += 0.2

        # Base score por ter contexto personalizado
        if rag_context.relevance_score > 0.7:
            score += 0.3

        return min(1.0, score)

    def _estimate_engagement_score(
        self,
        response: str,
        student_profile: StudentProfile
    ) -> float:
        """Estima o nível de engajamento da resposta."""
        score = 0.5  # Base score

        # Verificar elementos de engajamento
        if "?" in response:
            score += 0.1  # Perguntas aumentam engajamento
        if any(word in response.lower() for word in ["você", "seu", "sua", "pense", "considere"]):
            score += 0.1  # Linguagem pessoal
        if "exercício" in response.lower() or "prática" in response.lower():
            score += 0.1  # Elementos práticos
        if len(response.split()) > 200:
            score += 0.1  # Respostas mais longas tendem a ser mais engajadoras

        # Ajustar baseado no perfil
        if student_profile.learning_style == "kinesthetic" and "prática" in response.lower():
            score += 0.1

        return min(1.0, score)

    async def _generate_pedagogical_recommendations(
        self,
        student_profile: StudentProfile,
        session_context: Optional[SessionContext],
        response: str
    ) -> Dict[str, Any]:
        """Gera recomendações pedagógicas inteligentes."""
        recommendations = {
            "actions": [],
            "next_topics": [],
            "difficulty_adjustment": None,
            "processing_time": 0
        }

        # Recomendações baseadas no progresso
        if session_context:
            if session_context.interaction_count > 10 and session_context.average_engagement > 0.8:
                recommendations["actions"].append("Considere avançar para tópicos mais complexos")
                recommendations["difficulty_adjustment"] = "advanced"
            elif session_context.average_engagement < 0.5:
                recommendations["actions"].append("Reforce conceitos básicos antes de avançar")
                recommendations["difficulty_adjustment"] = "beginner"

        # Recomendações baseadas no perfil
        if student_profile.learning_style == "visual":
            recommendations["actions"].append("Explore recursos visuais complementares")
        elif student_profile.learning_style == "auditory":
            recommendations["actions"].append("Ouça podcasts ou explicações em vídeo")

        # Sugerir próximos tópicos baseados no conteúdo
        if "função" in response.lower():
            recommendations["next_topics"].extend([
                "Derivadas de funções",
                "Aplicações de funções em problemas reais"
            ])
        elif "algoritmo" in response.lower():
            recommendations["next_topics"].extend([
                "Análise de complexidade",
                "Estruturas de dados avançadas"
            ])

        return recommendations

class EducationalAgentService:
    """
    Serviço principal para gerenciamento de agentes educacionais.

    Recursos:
    - Gerenciamento de múltiplos agentes especializados
    - Cache inteligente de perfis de estudantes
    - Métricas de performance e engajamento
    - Adaptação dinâmica baseada em feedback
    """

    def __init__(self, rag_service: RAGService, agno_service: AgnoMethodologyService):
        self.rag_service = rag_service
        self.agno_service = agno_service

        # Cache de perfis de estudantes
        self.student_cache = {}
        self.session_cache = {}

        # Instâncias de agentes especializados
        self.agents = {
            "adaptive": EducationalAgent(rag_service, agno_service),
            "beginner": EducationalAgent(rag_service, agno_service),
            "advanced": EducationalAgent(rag_service, agno_service)
        }

        logger.info("EducationalAgentService inicializado")

    async def process_educational_query(
        self,
        query: str,
        user_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        Processa uma consulta educacional usando o agente mais apropriado.

        Args:
            query: Pergunta ou problema do estudante
            user_id: ID do usuário
            user_profile: Perfil opcional do usuário
            session_id: ID da sessão atual

        Returns:
            AgentResponse: Resposta personalizada do agente
        """
        try:
            # Carregar ou criar perfil do estudante
            student_profile = await self._get_or_create_student_profile(user_id, user_profile)

            # Carregar ou criar contexto da sessão
            session_context = await self._get_or_create_session_context(session_id, user_id, query)

            # Selecionar agente apropriado
            agent = self._select_agent(student_profile)

            # Processar consulta
            response = await agent.process_query(query, student_profile, session_context)

            # Atualizar contexto da sessão
            await self._update_session_context(session_context, response)

            return response

        except Exception as e:
            logger.error(f"Erro no processamento educacional: {e}")
            raise

    async def _get_or_create_student_profile(
        self,
        user_id: str,
        user_profile: Optional[Dict[str, Any]]
    ) -> StudentProfile:
        """Carrega ou cria perfil do estudante."""
        if user_id in self.student_cache:
            return self.student_cache[user_id]

        if user_profile:
            # Criar perfil a partir dos dados fornecidos
            profile = StudentProfile(
                user_id=user_id,
                name=user_profile.get("name"),
                learning_style=user_profile.get("learning_style", "visual"),
                current_level=user_profile.get("current_level", "intermediate"),
                subjects=user_profile.get("subjects", []),
                preferred_methodologies=user_profile.get("preferred_methodologies", []),
                learning_goals=user_profile.get("learning_goals", []),
                past_performance=user_profile.get("past_performance", {}),
                learning_pace=user_profile.get("learning_pace", "moderate"),
                preferred_difficulty=user_profile.get("preferred_difficulty", "adaptive"),
                accessibility_needs=user_profile.get("accessibility_needs", [])
            )
        else:
            # Criar perfil padrão
            profile = StudentProfile(
                user_id=user_id,
                learning_style="visual",
                current_level="intermediate",
                learning_pace="moderate",
                preferred_difficulty="adaptive"
            )

        self.student_cache[user_id] = profile
        return profile

    async def _get_or_create_session_context(
        self,
        session_id: Optional[str],
        user_id: str,
        query: str
    ) -> SessionContext:
        """Carrega ou cria contexto da sessão."""
        if not session_id:
            session_id = str(uuid.uuid4())

        if session_id in self.session_cache:
            return self.session_cache[session_id]

        # Extrair tópico da consulta (simplificado)
        current_topic = self._extract_topic_from_query(query)

        context = SessionContext(
            session_id=session_id,
            current_topic=current_topic,
            current_methodology="worked_examples",  # Default
            learning_objectives=[f"Aprender sobre {current_topic}"]
        )

        self.session_cache[session_id] = context
        return context

    def _extract_topic_from_query(self, query: str) -> str:
        """Extrai tópico principal da consulta (implementação simplificada)."""
        query_lower = query.lower()

        # Mapeamentos simples de tópicos
        topic_mappings = {
            "função": "funções matemáticas",
            "algoritmo": "algoritmos",
            "programação": "programação",
            "matemática": "matemática",
            "física": "física",
            "química": "química",
            "biologia": "biologia"
        }

        for keyword, topic in topic_mappings.items():
            if keyword in query_lower:
                return topic

        return "conceito geral"

    def _select_agent(self, student_profile: StudentProfile) -> EducationalAgent:
        """Seleciona o agente mais apropriado baseado no perfil."""
        if student_profile.current_level == "beginner":
            return self.agents["beginner"]
        elif student_profile.current_level == "advanced":
            return self.agents["advanced"]
        else:
            return self.agents["adaptive"]

    async def _update_session_context(
        self,
        session_context: SessionContext,
        response: AgentResponse
    ):
        """Atualiza o contexto da sessão baseado na resposta."""
        session_context.interaction_count += 1

        # Atualizar engajamento médio
        if session_context.average_engagement == 0:
            session_context.average_engagement = response.engagement_score
        else:
            session_context.average_engagement = (
                session_context.average_engagement * self.agents["adaptive"].engagement_decay +
                response.engagement_score * (1 - self.agents["adaptive"].engagement_decay)
            )

        # Atualizar dificuldade se recomendado
        if response.difficulty_adjustment:
            session_context.current_difficulty = response.difficulty_adjustment

    async def get_student_analytics(self, user_id: str) -> Dict[str, Any]:
        """Retorna analytics do estudante."""
        if user_id not in self.student_cache:
            return {"error": "Perfil não encontrado"}

        profile = self.student_cache[user_id]

        # Calcular estatísticas
        total_sessions = len([s for s in self.session_cache.values() if s.session_id.startswith(user_id)])
        avg_engagement = np.mean([
            s.average_engagement for s in self.session_cache.values()
            if s.session_id.startswith(user_id) and s.average_engagement > 0
        ]) if total_sessions > 0 else 0

        return {
            "user_id": user_id,
            "learning_style": profile.learning_style,
            "current_level": profile.current_level,
            "total_sessions": total_sessions,
            "average_engagement": avg_engagement,
            "preferred_methodologies": profile.preferred_methodologies,
            "learning_goals": profile.learning_goals
        }

# Instância global do serviço
educational_agent_service = EducationalAgentService(
    rag_service=None,  # Será injetado posteriormente
    agno_service=None  # Será injetado posteriormente
)
