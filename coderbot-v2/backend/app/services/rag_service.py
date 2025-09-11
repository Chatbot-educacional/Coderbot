"""
RAG (Retrieval-Augmented Generation) Service

Este serviço implementa um sistema completo de RAG para o sistema educacional,
incluindo context engineering, vectorização inteligente e busca semântica
otimizada para aprendizado personalizado.

Características principais:
- Integração com Qdrant para armazenamento vetorial
- Suporte a múltiplos modelos de embeddings (OpenAI, Claude, local)
- Context engineering avançado com isolamento e compressão
- Busca semântica otimizada para conteúdo educacional
- Cache inteligente para melhorar performance
- Métricas de qualidade e avaliação de relevância
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import asyncio
import json
import logging
import hashlib
import time
from pathlib import Path
import os
from functools import lru_cache

from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
import httpx
from sentence_transformers import SentenceTransformer
import numpy as np
from pydantic import BaseModel, Field

from app.config import settings
from app.services.agno_methodology_service import MethodologyType

logger = logging.getLogger(__name__)

class EducationalContent(BaseModel):
    """Modelo para conteúdo educacional indexado."""
    id: str
    title: str
    content: str
    content_type: str = Field(description="Tipo de conteúdo: lesson, exercise, example, theory, etc.")
    subject: str = Field(description="Matéria/disciplina")
    topic: str = Field(description="Tópico específico")
    difficulty: str = Field(description="Nível de dificuldade: beginner, intermediate, advanced")
    methodology: Optional[str] = Field(description="Metodologia educacional associada")
    tags: List[str] = Field(default_factory=list, description="Tags para busca")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SearchQuery(BaseModel):
    """Modelo para consultas de busca."""
    query: str
    user_context: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class SearchResult(BaseModel):
    """Modelo para resultados de busca."""
    content_id: str
    score: float
    content: EducationalContent
    context_snippet: Optional[str] = None
    relevance_explanation: Optional[str] = None

class RAGContext(BaseModel):
    """Modelo para contexto RAG estruturado."""
    query: str
    retrieved_content: List[SearchResult]
    user_profile: Optional[Dict[str, Any]] = None
    session_context: Optional[Dict[str, Any]] = None
    methodology_context: Optional[str] = None
    compressed_context: str = ""
    context_tokens: int = 0
    relevance_score: float = 0.0

class RAGService:
    """
    Serviço principal de RAG para o sistema educacional.

    Recursos:
    - Indexação inteligente de conteúdo educacional
    - Busca semântica com filtros contextuais
    - Context engineering com isolamento e compressão
    - Cache de embeddings para performance
    - Métricas de qualidade e avaliação
    """

    def __init__(self):
        from app.config import settings
        self.qdrant_url = settings.qdrant_url
        self.qdrant_api_key = settings.qdrant_api_key
        self.collection_name = "educational_content"

        # Inicializar cliente Qdrant
        self.qdrant_client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            timeout=30.0
        )

        # Modelos de embedding (fallback local se APIs falharem)
        self.embedding_model = None
        self.embedding_dimension = 1536  # OpenAI text-embedding-3-large

        # Cache de embeddings
        self.embedding_cache = {}

        # Configurações de context engineering
        self.max_context_tokens = 4000
        self.compression_ratio = 0.7
        self.isolation_threshold = 0.3

        # Inicializar coleção se não existir
        asyncio.create_task(self._ensure_collection())

    async def _ensure_collection(self):
        """Garante que a coleção Qdrant existe e está configurada."""
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"Criando coleção {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.embedding_dimension,
                        distance=models.Distance.COSINE,
                        on_disk=False  # Melhor performance para educação
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=10000,
                        memmap_threshold=20000,
                        max_segment_size=100000
                    )
                )
                logger.info(f"Coleção {self.collection_name} criada com sucesso")
            else:
                logger.info(f"Coleção {self.collection_name} já existe")

        except Exception as e:
            logger.error(f"Erro ao verificar/criar coleção: {e}")
            raise

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para o texto usando múltiplas estratégias.

        Prioridade:
        1. OpenAI (mais preciso para português/inglês)
        2. Claude (fallback)
        3. Modelo local (SentenceTransformers)
        """
        # Cache check
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        try:
            # Tentar OpenAI primeiro
            if settings.open_ai_api_key:
                async with httpx.AsyncClient(
                    base_url="https://api.openai.com/v1",
                    headers={"Authorization": f"Bearer {settings.open_ai_api_key}"},
                    timeout=30.0
                ) as client:
                    resp = await client.post(
                "/embeddings",
                        json={
                            "model": "text-embedding-3-large",
                            "input": text[:8000],  # Limitar tamanho
                            "encoding_format": "float"
                        }
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data["data"][0]["embedding"]

            # Cache
            self.embedding_cache[cache_key] = embedding
            return embedding

        except Exception as e:
            logger.warning(f"OpenAI embedding falhou: {e}")

        try:
            # Fallback para Claude
            if hasattr(settings, 'claude_api_key') and settings.claude_api_key:
                async with httpx.AsyncClient(
                    base_url="https://api.anthropic.com/v1",
                    headers={
                        "x-api-key": settings.claude_api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=30.0
                ) as client:
                    resp = await client.post(
                        "/embeddings",
                        json={
                            "model": "claude-3-sonnet-20240229",
                            "input": text[:8000]
                        }
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    embedding = data["embedding"]

                    # Cache
                    self.embedding_cache[cache_key] = embedding
                    return embedding

        except Exception as e:
            logger.warning(f"Claude embedding falhou: {e}")

        # Fallback para modelo local
        try:
            if not self.embedding_model:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.embedding_dimension = 384

            embedding = self.embedding_model.encode(text, convert_to_list=True)

            # Cache
            self.embedding_cache[cache_key] = embedding
            return embedding

        except Exception as e:
            logger.error(f"Todos os métodos de embedding falharam: {e}")
            raise RuntimeError("Não foi possível gerar embedding")

    async def index_content(self, content: EducationalContent) -> str:
        """
        Indexa novo conteúdo educacional no Qdrant.
        
        Args:
            content: Conteúdo educacional a ser indexado

        Returns:
            str: ID do conteúdo indexado
        """
        try:
            # Gerar embedding do conteúdo
            embedding = await self._get_embedding(content.content)

            # Preparar payload para Qdrant
            payload = {
                "title": content.title,
                "content": content.content,
                "content_type": content.content_type,
                "subject": content.subject,
                "topic": content.topic,
                "difficulty": content.difficulty,
                "methodology": content.methodology,
                "tags": content.tags,
                "metadata": json.dumps(content.metadata),
                "created_at": content.created_at.isoformat(),
                "updated_at": content.updated_at.isoformat()
            }

            # Indexar no Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    models.PointStruct(
                        id=content.id,
                        vector=embedding,
                        payload=payload
                    )
                ]
            )

            logger.info(f"Conteúdo indexado: {content.title} (ID: {content.id})")
            return content.id

        except Exception as e:
            logger.error(f"Erro ao indexar conteúdo {content.id}: {e}")
            raise

    async def search_content(self, query: SearchQuery) -> List[SearchResult]:
        """
        Busca conteúdo educacional relevante baseado na consulta.

        Args:
            query: Consulta de busca com filtros

        Returns:
            List[SearchResult]: Lista de resultados ordenados por relevância
        """
        try:
            # Gerar embedding da consulta
            query_embedding = await self._get_embedding(query.query)

            # Construir filtros Qdrant
            qdrant_filter = None
            if query.filters:
                conditions = []
                if "subject" in query.filters:
                    conditions.append(
                        models.FieldCondition(
                            key="subject",
                            match=models.MatchValue(value=query.filters["subject"])
                        )
                    )
                if "difficulty" in query.filters:
                    conditions.append(
                        models.FieldCondition(
                            key="difficulty",
                            match=models.MatchValue(value=query.filters["difficulty"])
                        )
                    )
                if "content_type" in query.filters:
                    conditions.append(
                        models.FieldCondition(
                            key="content_type",
                            match=models.MatchValue(value=query.filters["content_type"])
                        )
                    )
                if conditions:
                    qdrant_filter = models.Filter(must=conditions)

            # Buscar no Qdrant
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=qdrant_filter,
                limit=query.limit,
                score_threshold=query.score_threshold,
                with_payload=True
            )

            # Converter para SearchResult
            results = []
            for hit in search_results:
                # Reconstruir EducationalContent
                payload = hit.payload
                content = EducationalContent(
                    id=hit.id,
                    title=payload.get("title", ""),
                    content=payload.get("content", ""),
                    content_type=payload.get("content_type", ""),
                    subject=payload.get("subject", ""),
                    topic=payload.get("topic", ""),
                    difficulty=payload.get("difficulty", ""),
                    methodology=payload.get("methodology"),
                    tags=payload.get("tags", []),
                    metadata=json.loads(payload.get("metadata", "{}")),
                    created_at=datetime.fromisoformat(payload.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(payload.get("updated_at", datetime.utcnow().isoformat()))
                )

                # Criar snippet de contexto
                context_snippet = self._create_context_snippet(
                    query.query, content.content, max_length=200
                )

                result = SearchResult(
                    content_id=hit.id,
                    score=hit.score,
                    content=content,
                    context_snippet=context_snippet,
                    relevance_explanation=self._explain_relevance(hit.score, content)
                )
                results.append(result)

            logger.info(f"Busca realizada: '{query.query}' -> {len(results)} resultados")
            return results

        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            raise

    def _create_context_snippet(self, query: str, content: str, max_length: int = 200) -> str:
        """Cria snippet de contexto relevante ao redor da consulta."""
        query_lower = query.lower()
        content_lower = content.lower()

        # Encontrar posição da consulta
        query_pos = content_lower.find(query_lower)
        if query_pos == -1:
            # Fallback: retornar início do conteúdo
            return content[:max_length] + "..." if len(content) > max_length else content

        # Extrair contexto ao redor da consulta
        start = max(0, query_pos - max_length // 2)
        end = min(len(content), query_pos + len(query) + max_length // 2)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def _explain_relevance(self, score: float, content: EducationalContent) -> str:
        """Explica por que o resultado é relevante."""
        explanations = []

        if score > 0.9:
            explanations.append("Excelente correspondência semântica")
        elif score > 0.8:
            explanations.append("Boa correspondência semântica")
        elif score > 0.7:
            explanations.append("Correspondência razoável")

        if content.difficulty:
            explanations.append(f"Nível: {content.difficulty}")
        if content.subject:
            explanations.append(f"Matéria: {content.subject}")
        if content.content_type:
            explanations.append(f"Tipo: {content.content_type}")

        return " | ".join(explanations)

    async def build_rag_context(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None,
        methodology: Optional[MethodologyType] = None
    ) -> RAGContext:
        """
        Constrói contexto RAG inteligente com context engineering.
        
        Args:
            query: Consulta do usuário
            user_context: Contexto do usuário (perfil, histórico)
            session_context: Contexto da sessão atual
            methodology: Metodologia educacional
            
        Returns:
            RAGContext: Contexto estruturado e otimizado
        """
        try:
            # Buscar conteúdo relevante
            search_query = SearchQuery(
                query=query,
                user_context=user_context,
                filters=self._build_search_filters(user_context, session_context),
                limit=15,
                score_threshold=0.6
            )

            retrieved_content = await self.search_content(search_query)

            # Aplicar context engineering
            compressed_context = await self._compress_context(
                retrieved_content, query, max_tokens=self.max_context_tokens
            )

            # Calcular score de relevância geral
            relevance_score = np.mean([r.score for r in retrieved_content]) if retrieved_content else 0.0

            rag_context = RAGContext(
                query=query,
                retrieved_content=retrieved_content,
                user_profile=user_context,
                session_context=session_context,
                methodology_context=methodology.value if methodology else None,
                compressed_context=compressed_context,
                context_tokens=self._estimate_tokens(compressed_context),
                relevance_score=relevance_score
            )

            logger.info(f"Contexto RAG construído: {len(retrieved_content)} itens, {rag_context.context_tokens} tokens")
            return rag_context

        except Exception as e:
            logger.error(f"Erro ao construir contexto RAG: {e}")
            raise

    def _build_search_filters(
        self,
        user_context: Optional[Dict[str, Any]],
        session_context: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Constrói filtros de busca baseados no contexto."""
        filters = {}

        if user_context:
            if "subject" in user_context:
                filters["subject"] = user_context["subject"]
            if "difficulty" in user_context:
                filters["difficulty"] = user_context["difficulty"]

        if session_context:
            if "current_topic" in session_context:
                filters["topic"] = session_context["current_topic"]

        return filters if filters else None

    async def _compress_context(
        self,
        search_results: List[SearchResult],
        query: str,
        max_tokens: int
    ) -> str:
        """
        Comprime contexto usando técnicas de context engineering.

        Técnicas aplicadas:
        - Remoção de redundâncias
        - Priorização por relevância
        - Isolamento de seções importantes
        - Compressão hierárquica
        """
        if not search_results:
            return ""

        # Ordenar por relevância
        sorted_results = sorted(search_results, key=lambda x: x.score, reverse=True)

        # Remover redundâncias
        unique_content = []
        seen_titles = set()

        for result in sorted_results:
            if result.content.title not in seen_titles:
                unique_content.append(result)
                seen_titles.add(result.content.title)

        # Construir contexto comprimido
        context_parts = []
        current_tokens = 0

        for result in unique_content:
            # Estimar tokens do conteúdo
            content_tokens = self._estimate_tokens(result.content.content)

            if current_tokens + content_tokens > max_tokens:
                # Comprimir conteúdo se necessário
                compressed_content = self._compress_single_content(
                    result.content.content, query, max_tokens - current_tokens
                )
                if compressed_content:
                    context_parts.append(f"## {result.content.title}\n{compressed_content}")
                    current_tokens += self._estimate_tokens(compressed_content)
            else:
                context_parts.append(f"## {result.content.title}\n{result.content.content}")
                current_tokens += content_tokens

            if current_tokens >= max_tokens * 0.9:  # Parar em 90% para margem
                break

        return "\n\n".join(context_parts)

    def _compress_single_content(self, content: str, query: str, max_tokens: int) -> str:
        """Comprime um único conteúdo mantendo partes mais relevantes."""
        if self._estimate_tokens(content) <= max_tokens:
            return content

        # Estratégia simples: manter parágrafos mais relevantes
        paragraphs = content.split('\n\n')
        query_lower = query.lower()

        # Pontuar parágrafos por relevância
        scored_paragraphs = []
        for para in paragraphs:
            score = sum(1 for word in query_lower.split() if word in para.lower())
            scored_paragraphs.append((score, para))

        # Selecionar parágrafos mais relevantes
        scored_paragraphs.sort(key=lambda x: x[0], reverse=True)

        compressed = []
        current_tokens = 0

        for _, para in scored_paragraphs:
            para_tokens = self._estimate_tokens(para)
            if current_tokens + para_tokens <= max_tokens:
                compressed.append(para)
                current_tokens += para_tokens
            else:
                break

        return '\n\n'.join(compressed)

    def _estimate_tokens(self, text: str) -> int:
        """Estima número de tokens (aproximação simples: 4 chars = 1 token)."""
        return len(text) // 4

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas da coleção Qdrant."""
        try:
            info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vectors_count": info.vectors_count,
                "segments_count": info.segments_count,
                "status": info.status,
                "config": {
                    "vectors": info.config.params.vectors,
                    "optimizers": info.config.optimizer_config
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {"error": str(e)}

    async def clear_cache(self):
        """Limpa cache de embeddings."""
        self.embedding_cache.clear()
        logger.info("Cache de embeddings limpo")

# Instância global do serviço
rag_service = RAGService()