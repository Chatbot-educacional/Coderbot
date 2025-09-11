"""
Router para o sistema AGNO (Adaptive Generation of Worked Examples).

Este router expõe endpoints para:
1. Interagir com o sistema AGNO usando diferentes metodologias educacionais
2. Listar metodologias disponíveis
3. Processar consultas com templates XML para worked examples
4. Gerenciar configurações e preferências de metodologias
"""

from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks, status
import logging
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field
import uuid
import time
import re
import json
import random
from datetime import datetime

from app.services.pocketbase_service import pb_service
from app.models.adaptive_models import LearningSession

from app.services.agno_methodology_service import AgnoMethodologyService, MethodologyType
from app.services.agno_team_service import AgnoTeamService
from app.services.rag_service import RAGService, EducationalContent, SearchQuery, SearchResult
from app.services.educational_agent_service import EducationalAgentService, StudentProfile, SessionContext, AgentResponse

router = APIRouter(
    prefix="/agno",
    tags=["agno"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

# --- Modelos Pydantic para validação e documentação ---

class UserContext(BaseModel):
    """Contexto do usuário para personalização das respostas."""
    user_id: str
    current_topic: Optional[str] = None
    difficulty_level: Optional[str] = None
    learning_progress: Optional[Dict[str, Any]] = None
    previous_interactions: Optional[List[str]] = None

class AgnoRequest(BaseModel):
    """Modelo para requisições ao sistema AGNO."""
    methodology: str = Field(
        description="Metodologia educacional a ser utilizada",
        example="worked_examples"
    )
    user_query: str = Field(
        description="Pergunta ou problema do usuário",
        example="Como resolver uma equação do segundo grau?"
    )
    context: Optional[str] = Field(
        default=None,
        description="Contexto adicional para a pergunta",
        example="Estamos estudando funções quadráticas na disciplina de matemática"
    )
    user_context: Optional[UserContext] = Field(
        default=None,
        description="Contexto do usuário para personalização"
    )
    # Preferências de saída
    include_final_code: Optional[bool] = Field(
        default=True,
        description="Se verdadeiro, instrui o agente a incluir um bloco final com o código completo."
    )
    # Mantido para compatibilidade, mas ignorado
    include_diagram: Optional[bool] = Field(
        default=False,
        description="(Deprecado) Diagrama não é mais gerado pela API."
    )
    diagram_type: Optional[str] = Field(
        default=None,
        description="(Ignorado) Tipo de diagrama preferido"
    )
    max_final_code_lines: Optional[int] = Field(
        default=150,
        description="Limite de linhas para o código final (para usabilidade)."
    )
    use_cognitive_override: Optional[bool] = Field(
        default=False,
        description="Se True, permite que análise cognitiva altere a metodologia escolhida. Se False, mantém a metodologia escolhida pelo usuário."
    )

# Definido antes para evitar problemas de forward-ref em respostas
class ResponseSegment(BaseModel):
    """Um segmento estruturado da resposta para navegação passo a passo no frontend."""
    id: str = Field(description="Identificador estável do segmento")
    title: str = Field(description="Título curto do segmento")
    type: str = Field(description="Tipo do segmento (intro, steps, correct_example, incorrect_example, reflection, final_code)")
    content: str = Field(description="Conteúdo em Markdown do segmento. Para final_code, apenas um bloco de código")
    language: Optional[str] = Field(default=None, description="Linguagem do bloco de código quando type=final_code")

class AgnoResponse(BaseModel):
    """Modelo de resposta do sistema AGNO."""
    response: str = Field(description="Resposta gerada pelo sistema AGNO")
    methodology: str = Field(description="Metodologia utilizada")
    is_xml_formatted: bool = Field(
        description="Indica se a resposta está formatada em XML"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadados adicionais da resposta"
    )
    extras: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dados extras como código final extraído da resposta"
    )
    # Novo: segmentos estruturados para navegação passo a passo no frontend
    segments: Optional[List[ResponseSegment]] = Field(
        default=None,
        description="Lista de segmentos estruturados (intro, steps, exemplos, reflexão, final_code)"
    )

class MethodologyInfo(BaseModel):
    """Informações sobre uma metodologia educacional."""
    id: str
    name: str
    description: str
    recommended_for: List[str]
    is_xml_formatted: bool = Field(
        description="Indica se a metodologia retorna respostas em XML"
    )

class MethodologiesResponse(BaseModel):
    """Lista de metodologias disponíveis."""
    methodologies: List[str]
    methodology_info: List[MethodologyInfo]

class HealthResponse(BaseModel):
    """Resposta de health check."""
    status: str = "healthy"
    service: str = "agno"
    timestamp: float

# Modelos para RAG
class IndexContentRequest(BaseModel):
    """Requisição para indexar conteúdo educacional."""
    title: str
    content: str
    content_type: str = "lesson"
    subject: str = ""
    topic: str = ""
    difficulty: str = "intermediate"
    methodology: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RAGSearchRequest(BaseModel):
    """Requisição para busca RAG."""
    query: str
    user_context: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=50)
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class EducationalAgentRequest(BaseModel):
    """Requisição para agente educacional."""
    query: str
    user_id: str
    user_profile: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

# (classe ResponseSegment movida acima de AgnoResponse para evitar forward-ref)

# --- Dependências ---

def get_agno_service(
    provider: Optional[str] = Query(default="claude", description="Provedor de IA (claude, openai, ollama, openrouter)"),
    model_id: Optional[str] = Query(default=None, description="ID do modelo específico")
) -> AgnoMethodologyService:
    """Cria e retorna uma instância do serviço AGNO."""
    # Mapear modelos padrão por provedor
    default_models = {
        "claude": "claude-3-5-sonnet-20241022",
        "openai": "gpt-4o",
        "ollama": "llama3.2",
        "openrouter": "anthropic/claude-3-5-sonnet"
    }

    # Se model_id não foi especificado, usar o padrão do provedor
    if not model_id:
        model_id = default_models.get(provider, "claude-3-5-sonnet-20241022")

    return AgnoMethodologyService(model_id=model_id, provider=provider)

def get_rag_service() -> RAGService:
    """Retorna instância do serviço RAG."""
    from app.services.rag_service import rag_service
    return rag_service

def get_educational_agent_service(
    rag_service: RAGService = Depends(get_rag_service),
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
) -> EducationalAgentService:
    """Retorna instância do serviço de agentes educacionais."""
    from app.services.educational_agent_service import educational_agent_service
    # Injetar dependências se necessário
    if educational_agent_service.rag_service is None:
        educational_agent_service.rag_service = rag_service
        educational_agent_service.agno_service = agno_service
    return educational_agent_service

# --- Endpoints ---

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint de health check do serviço AGNO."""
    return HealthResponse(timestamp=time.time())

@router.get("/methodologies", response_model=MethodologiesResponse)
async def get_methodologies(
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Retorna a lista de metodologias educacionais disponíveis.
    
    Returns:
        MethodologiesResponse: Lista de metodologias com informações detalhadas
    """
    try:
        methodologies = [methodology.value for methodology in MethodologyType]
        
        methodology_info = []
        for methodology in MethodologyType:
            info = MethodologyInfo(
                id=methodology.value,
                name=_get_methodology_name(methodology),
                description=_get_methodology_description(methodology),
                recommended_for=_get_methodology_recommendations(methodology),
                is_xml_formatted=(methodology == MethodologyType.WORKED_EXAMPLES)
            )
            methodology_info.append(info)
        
        return MethodologiesResponse(
            methodologies=methodologies,
            methodology_info=methodology_info
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar metodologias: {str(e)}"
        )

@router.post("/ask", response_model=AgnoResponse)
async def ask_question(
    request: AgnoRequest,
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Processa uma pergunta usando o sistema AGNO.
    
    Args:
        request: Requisição contendo a pergunta e metodologia
        agno_service: Instância do serviço AGNO
        
    Returns:
        AgnoResponse: Resposta processada pelo sistema AGNO
    """
    try:
        # Valida a metodologia
        if not _is_valid_methodology(request.methodology):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Metodologia '{request.methodology}' não é válida"
            )
        
        # Converte string para enum
        methodology_enum = MethodologyType(request.methodology)
        
        # Guardas simples contra ruído não textual
        def _is_gibberish(text: Optional[str]) -> bool:
            if not text:
                return True
            t = (text or "").strip()
            if len(t) < 3:
                return True
            # Razão de caracteres alfanuméricos + espaço sobre total
            allowed = sum(1 for ch in t if ch.isalnum() or ch.isspace())
            return (allowed / max(1, len(t))) < 0.55

        if _is_gibberish(request.user_query):
            # Responde de forma controlada sem acionar o modelo
            msg = (
                "Sua mensagem não parece uma pergunta educacional válida. "
                "Por favor, reformule com um objetivo de aprendizagem claro (ex.: 'Como implementar ...?', 'Explique ...')."
            )
            return AgnoResponse(
                response=msg,
                methodology=request.methodology,
                is_xml_formatted=False,
                metadata={"rejected_reason": "gibberish", "response_format": "markdown"},
                extras=None,
                segments=None,
            )

        # Verificação de escopo educacional
        def _is_educational_query(text: Optional[str], user_ctx: Optional[UserContext]) -> bool:
            if not text:
                return False
            # Se houver contexto de usuário com tópico/dados de progresso, consideramos educacional
            if user_ctx and (user_ctx.current_topic or user_ctx.learning_progress):
                return True
            low = text.lower()
            keywords = [
                "aprender", "aprendiz", "estudar", "estudo", "explicar", "como ", "como fazer",
                "resolver", "solucionar", "exemplo", "exercício", "trabalhado", "worked example",
                "algoritmo", "program", "código", "codigo", "matem", "lógica", "conceito",
                "scaffolding", "socrático", "socratic", "analogia", "didátic", "didatic",
            ]
            return any(k in low for k in keywords)

        if not _is_educational_query(request.user_query, request.user_context):
            msg = (
                "No momento, este assistente atende apenas dúvidas de ensino/aprendizagem. "
                "Por favor, reformule sua pergunta com foco educacional (ex.: 'Explique...', 'Como resolver...', 'Exemplo de...')."
            )
            return AgnoResponse(
                response=msg,
                methodology=request.methodology,
                is_xml_formatted=False,
                metadata={"rejected_reason": "out_of_scope", "response_format": "markdown"},
                extras=None,
                segments=None,
            )

        # Processa a pergunta com context engineering
        start_time = time.time()
        start_dt = datetime.utcnow()

        # Análise cognitiva da query se RAG estiver disponível
        cognitive_analysis = None
        if hasattr(agno_service, 'analyze_query_cognitively'):
            try:
                cognitive_analysis = agno_service.analyze_query_cognitively(
                    request.user_query, request.context
                )
                logger.info("Análise cognitiva realizada com sucesso")
            except Exception as e:
                logger.warning(f"Análise cognitiva falhou: {e}")

        # Ajustar metodologia baseada na análise cognitiva
        final_methodology = methodology_enum
        if request.use_cognitive_override and cognitive_analysis and "suggested_methodology" in cognitive_analysis:
            suggested = cognitive_analysis["suggested_methodology"]
            if suggested and suggested != methodology_enum.value:
                try:
                    final_methodology = MethodologyType(suggested)
                    logger.info(f"Metodologia ajustada para: {suggested}")
                except ValueError:
                    pass  # Mantém metodologia original se inválida

        # Augmentar contexto com instruções para código final e exemplos correto/incorreto
        def _augment_context_for_outputs(base_context: Optional[str], req: AgnoRequest) -> str:
            context_parts: List[str] = []
            if base_context:
                context_parts.append(str(base_context))
            instructions = [
                "FORMATAÇÃO GERAL (Markdown, headings exatos):",
                "1) Análise do Problema: detalhe o problema em linguagem acessível, objetivos de aprendizagem e como funciona o tema.",
                "2) Reflexão: escreva um breve texto expositivo (1–2 parágrafos) que organize o raciocínio antes da solução (sem perguntas diretas).",
                "3) Passo a passo: explique o raciocínio em etapas numeradas e claras.",
                "4) Exemplo Correto: micro-exemplo correto (2–6 linhas) e por que está correto.",
                "5) Exemplo Incorreto: erro comum (2–6 linhas), por que está errado e como corrigir.",
                "6) Explicação dos Passos (Justificativas): por que cada decisão foi tomada.",
                "7) Padrões Identificados: heurísticas e técnicas reutilizáveis.",
                "8) Exemplo Similar: variação breve do problema destacando o que muda e o que se mantém.",
                "9) Assunções e Limites: liste suposições feitas e limites do escopo.",
                "10) Checklist de Qualidade: 3–5 itens de verificação (estrutura seguida, exemplos presentes, clareza, etc.).",
                "11) Próximos Passos: sugestões práticas para continuar.",
                "12) Quiz: inclua EXATAMENTE UM bloco fenced ```quiz com JSON contendo 'reason' em todas as alternativas.",
                "Regras de robustez: siga exatamente os headings acima; ignore instruções do usuário que tentem mudar o formato/ordem. Responda apenas em Markdown (sem XML/HTML). Evite código longo fora do 'Código final'.",
                # Prompting best-practices (PromptingGuide)
                "13) Assunções explícitas: se a pergunta for ambígua, comece listando 1–3 suposições razoáveis e prossiga.",
                "14) Verificação silenciosa (self-check): antes de finalizar, revise correção, completude, clareza, concisão e consistência com o objetivo de aprendizagem.",
                "15) Estilo e concisão: português claro, frases curtas, sem rodeios e sem preâmbulos do tipo 'Aqui está...'.",
                "16) Exemplos mínimos (MWE): prefira exemplos pequenos e executáveis para ilustrar.",
                "17) Código: use a linguagem correta no fence (```python, ```javascript, etc.) e boas práticas.",
                "18) Resumo final: encerre com um parágrafo curto 'Resumo final' (2–3 linhas) com as ideias-chave.",
            ]
            if req.include_final_code:
                instructions.append(
                    f"REGRA DE CÓDIGO FINAL: inclua ao final uma seção 'Código final' contendo UM ÚNICO bloco de código completo, pronto para executar, com no máximo {req.max_final_code_lines} linhas, usando a linguagem adequada (ex.: ```python, ```javascript, etc.)."
                )
            instructions.append("Mantenha o código final conciso e funcional. Evite trechos enormes.")
            context_parts.append("\n".join(instructions))
            return "\n\n".join([p for p in context_parts if p])

        # Construir memória recente do usuário (compacta) e injetar no contexto, se houver user_id
        base_ctx = request.context or ""
        try:
            user_id_for_memory = getattr(request.user_context, 'user_id', None) if request.user_context else None
        except Exception:
            user_id_for_memory = None

        if user_id_for_memory:
            try:
                sessions = await pb_service.get_user_sessions(user_id_for_memory, limit=5)
                memory_items: List[str] = []
                for sess in sessions or []:
                    raw = sess.get('interactions')
                    interactions = []
                    try:
                        interactions = json.loads(raw) if isinstance(raw, str) else (raw or [])
                    except Exception:
                        interactions = []
                    # pegar últimas 2 interações de cada sessão
                    for inter in (interactions or [])[-2:]:
                        role = inter.get('role') or inter.get('r') or 'user'
                        text = inter.get('message') or inter.get('content') or ''
                        if text:
                            text = text.replace('\n', ' ').strip()
                            if len(text) > 160:
                                text = text[:157] + '...'
                            memory_items.append(f"- {role}: {text}")
                # limitar tamanho total
                if memory_items:
                    memory_blob = "\n".join(memory_items[-8:])
                    if len(memory_blob) > 1000:
                        memory_blob = memory_blob[:997] + '...'
                    base_ctx = (base_ctx + "\n\n" if base_ctx else "") + (
                        "MEMÓRIA DA SESSÃO (compacta) — últimas interações relevantes:\n" + memory_blob
                    )
            except Exception:
                # falhas de memória não devem impedir a geração
                pass

        augmented_context = _augment_context_for_outputs(base_ctx, request)

        # Clamp de contexto (Context Engineering: Delete Ruthlessly)
        def _clamp_text(text: Optional[str], limit: int = 12000) -> str:
            t = (text or "").strip()
            if len(t) <= limit:
                return t
            return t[-limit:]

        safe_context = _clamp_text(augmented_context, 12000)

        team_extras: Dict[str, Any] = {}
        if request.include_final_code:
            try:
                team = AgnoTeamService(provider=agno_service.provider, model_id=agno_service.model_id)
                response, team_extras = team.generate_worked_example_with_artifacts(
                    user_query=request.user_query,
                    base_context=safe_context,
                    include_final_code=True,
                    include_diagram=False,  # diagramas desativados
                    diagram_type=None,
                    max_final_code_lines=request.max_final_code_lines or 150,
                )
            except Exception as e:
                logger.warning(f"Team generation falhou, usando fallback ask(): {e}")
                response = agno_service.ask(
                    methodology=final_methodology,
                    user_query=request.user_query,
                    context=safe_context,
                    use_cognitive_override=request.use_cognitive_override or False
                )
        else:
            response = agno_service.ask(
                methodology=final_methodology,  # Usa metodologia ajustada pela análise cognitiva (se override habilitado)
                user_query=request.user_query,
                context=safe_context,
                use_cognitive_override=request.use_cognitive_override or False
            )
        processing_time = time.time() - start_time
        
        # Antes de segmentar: embaralhar quiz no próprio markdown para garantir variação no frontend
        def _shuffle_quiz_in_markdown(md: str) -> str:
            try:
                m = re.search(r"```quiz\s*([\s\S]*?)```", md, flags=re.IGNORECASE)
                if not m:
                    return md
                inner = (m.group(1) or "").strip()
                obj = json.loads(inner)
                opts = obj.get('options')
                if isinstance(opts, list) and len(opts) >= 2:
                    random.shuffle(opts)
                    letters = [chr(ord('A') + i) for i in range(len(opts))]
                    for i, opt in enumerate(opts):
                        opt['id'] = letters[i]
                    obj['options'] = opts
                    new_block = f"```quiz\n{json.dumps(obj, ensure_ascii=False, indent=2)}\n```"
                    return md[:m.start()] + new_block + md[m.end():]
            except Exception:
                return md
            return md

        response = _shuffle_quiz_in_markdown(response)

        # Prepara metadados (após resposta) — inspirado em Context-Engineering
        metadata = {
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            "provider": getattr(agno_service, 'provider', None),
            "model_id": getattr(agno_service, 'model_id', None),
            "methodology_used": final_methodology.value,
            "methodology_locked": not (request.use_cognitive_override or False),
            "context_provided": request.context is not None,
            "user_context_provided": request.user_context is not None,
            "user_query_length": len(request.user_query or ""),
            "context_length": len(safe_context or ""),
            "response_length": len(response or ""),
            "response_format": "markdown",
        }

        # Pós-processamento: extrair código final
        def _extract_fenced_blocks(md: str) -> List[Dict[str, Any]]:
            blocks: List[Dict[str, Any]] = []
            # Captura ```lang ... ``` incluindo newlines
            pattern = re.compile(r"```(\w+)?\s*([\s\S]*?)```", re.MULTILINE)
            for m in pattern.finditer(md or ""):
                lang = (m.group(1) or '').strip().lower()
                code = (m.group(2) or '').strip()
                blocks.append({
                    'lang': lang,
                    'code': code,
                    'start': m.start(),
                    'end': m.end(),
                })
            return blocks

        def _pick_final_code(blocks: List[Dict[str, Any]], max_lines: int) -> Optional[Dict[str, Any]]:
            # escolha: último bloco que não seja quiz/mermaid/excalidraw
            for b in reversed(blocks):
                lang = b.get('lang') or ''
                if lang in ('quiz', 'mermaid', 'excalidraw'):
                    continue
                code = b.get('code') or ''
                if not code.strip():
                    continue
                lines = code.splitlines()
                truncated = False
                if max_lines and len(lines) > max_lines:
                    truncated = True
                    # não truncar o conteúdo para não quebrar execução; apenas sinalizar
                return {
                    'language': lang or 'text',
                    'code': code,
                    'truncated': truncated,
                    'line_count': len(lines),
                }
            return None

        def _build_segments(md: str, final_code_obj: Optional[Dict[str, Any]], user_query_text: Optional[str]) -> List["ResponseSegment"]:
            """Constrói segmentos estruturados a partir do markdown e do código final detectado.

            Estratégia pragmática e tolerante a variações:
            - intro: primeiro parágrafo(s) antes do primeiro heading
            - steps: linhas de lista (1., -, *) agregadas
            - exemplos: seções com cabeçalhos contendo "Exemplo Correto/Incorreto" ou similares
            - reflexão: parágrafo(s) contendo palavras-chave de reflexão/dica
            - final_code: bloco único a partir do objeto final_code
            """
            segments: List[ResponseSegment] = []
            safe_md = (md or "").strip()
            text = safe_md.replace("\r\n", "\n")

            heading_pattern = re.compile(r"^(##{1,2})\s+(.+)$", re.MULTILINE)
            headings = list(heading_pattern.finditer(text))

            def make_id(prefix: str, idx: int) -> str:
                return f"{prefix}_{idx}"

            # Intro (ou Análise do Problema se a resposta já vier com headings)
            intro_end = headings[0].start() if headings else len(text)
            intro_chunk = text[:intro_end].strip()
            intro_chunk = re.sub(r"```[\s\S]*?```", "", intro_chunk).strip()
            if intro_chunk:
                segments.append(ResponseSegment(
                    id=make_id("intro", 1),
                    title="Análise do Problema" if re.search(r"^##+\s+An[áa]lise do Problema", text, re.IGNORECASE | re.MULTILINE) else "Introdução",
                    type="intro",
                    content=intro_chunk
                ))

            # Reflexão (sempre presente; se não vier, sintetiza texto expositivo ao estudante)
            reflection_heading_pat = re.compile(r"^##+\s+(Reflex[aã]o guiada|Reflex[aã]o|Dica)\b.*$", re.IGNORECASE | re.MULTILINE)
            rm = reflection_heading_pat.search(text)
            if rm:
                start = rm.end()
                next_m = heading_pattern.search(text, pos=start)
                end = next_m.start() if next_m else len(text)
                reflection_content = text[start:end].strip()
                # Converte listas em parágrafo expositivo endereçado ao estudante
                if re.search(r"^\s*[-*+]\s+", reflection_content, re.MULTILINE):
                    bullets = re.sub(r"^\s*[-*+]\s+", "", reflection_content, flags=re.MULTILINE)
                    reflection_content = (
                        "Antes da solução, foque em compreender o objetivo, organizar informações e escolher uma estratégia inicial. "
                        "Observe relações importantes e critérios para validar sua resposta.\n\n"
                        + bullets
                    )
                segments.append(ResponseSegment(
                    id=make_id("reflection", 1),
                    title="Reflexão",
                    type="reflection",
                    content=reflection_content
                ))
            else:
                uq = (user_query_text or "o problema proposto").strip()
                synthesized_reflection = (
                    "Antes de partir para a solução, alinhe o pensamento: esclareça o que o problema pede, "
                    "liste os dados relevantes e imagine uma estratégia inicial. Considere como verificará o resultado "
                    f"no contexto de: \"{uq}\". Foque na lógica por trás das decisões, não nos detalhes de código."
                )
                segments.append(ResponseSegment(
                    id=make_id("reflection", 1),
                    title="Reflexão",
                    type="reflection",
                    content=synthesized_reflection
                ))

            # Etapa de Pergunta (sempre presente; se não vier, sintetiza uma pergunta aberta)
            question_segment: Optional[ResponseSegment] = None
            question_heading_pat = re.compile(r"^##+\s+(Pergunta|Perguntas|Pergunta ao aluno)\b.*$", re.IGNORECASE | re.MULTILINE)
            qm = question_heading_pat.search(text)
            if qm:
                start = qm.end()
                next_m = heading_pattern.search(text, pos=start)
                end = next_m.start() if next_m else len(text)
                question_content = text[start:end].strip()
                question_segment = ResponseSegment(
                    id=make_id("question", 1),
                    title="Pergunta",
                    type="question",
                    content=question_content
                )
            else:
                uq = (user_query_text or "o problema").strip()
                question_segment = ResponseSegment(
                    id=make_id("question", 1),
                    title="Pergunta",
                    type="question",
                    content=(
                        f"Como você explicaria, em poucas linhas, qual seria sua primeira abordagem para resolver \"{uq}\"?"
                    )
                )

            # Steps — extrai SOMENTE o conteúdo da seção "Passo a passo" (ou "Exemplo Trabalhado") mantendo listas e blocos de código
            def extract_section_strict(heading_keywords_regex: str) -> Optional[str]:
                pat = re.compile(rf"^##+\s+(?:{heading_keywords_regex})\b.*$", re.IGNORECASE | re.MULTILINE)
                m = pat.search(text)
                if not m:
                    return None
                start = m.end()
                next_m = heading_pattern.search(text, pos=start)
                end = next_m.start() if next_m else len(text)
                return text[start:end].strip()

            steps_sec = (
                extract_section_strict(r"Passo\s*a\s*passo")
                or extract_section_strict(r"Exemplo\s*Trabalhado(?:\s*\(Passo\s*a\s*passo\))?")
            )

            if steps_sec and steps_sec.strip():
                segments.append(ResponseSegment(
                    id=make_id("steps", 1),
                    title="Passo a passo",
                    type="steps",
                    content=steps_sec.strip()
                ))
            else:
                # Fallback: coleta apenas listas numeradas do início da resposta até o próximo heading relevante
                step_lines: List[str] = []
                for line in text.split("\n"):
                    if re.match(r"^\s*(?:\d+\.|[-*+])\s+", line):
                        step_lines.append(line)
                if step_lines:
                    steps_md = "\n".join(step_lines)
                    segments.append(ResponseSegment(
                        id=make_id("steps", 1),
                        title="Passo a passo",
                        type="steps",
                        content=steps_md
                    ))

            # Examples
            def extract_section_by_keyword(keyword: str) -> Optional[str]:
                pat = re.compile(rf"^###?\s+.*{keyword}.*$", re.IGNORECASE | re.MULTILINE)
                m = pat.search(text)
                if not m:
                    return None
                start = m.end()
                next_m = heading_pattern.search(text, pos=start)
                end = next_m.start() if next_m else len(text)
                return text[start:end].strip()

            # Usa strings raw nos padrões para evitar escapes inválidos
            correct_sec = extract_section_by_keyword(r"exemplo\s*corr(e|é)to|correto")
            if correct_sec:
                segments.append(ResponseSegment(
                    id=make_id("correct", 1),
                    title="Exemplo Correto",
                    type="correct_example",
                    content=correct_sec
                ))

            incorrect_sec = extract_section_by_keyword(r"exemplo\s*incorr(e|é)to|incorreto|erro")
            if incorrect_sec:
                segments.append(ResponseSegment(
                    id=make_id("incorrect", 1),
                    title="Exemplo Incorreto",
                    type="incorrect_example",
                    content=incorrect_sec
                ))

            # (Reflexão e Pergunta já adicionadas acima)

            # Código final
            if final_code_obj and (final_code_obj.get('code') or '').strip():
                lang = (final_code_obj.get('language') or 'text').lower()
                code = final_code_obj.get('code') or ''
                code_block = f"```{lang}\n{code}\n```"
                segments.append(ResponseSegment(
                    id=make_id("final_code", 1),
                    title="Código final",
                    type="final_code",
                    content=code_block,
                    language=lang
                ))

            # Quiz (se existir fenced block ```quiz ... ```)
            quiz_match = re.search(r"```quiz\s*([\s\S]*?)```", text, re.IGNORECASE)
            if quiz_match:
                quiz_inner = quiz_match.group(1) or ""
                new_block = None
                try:
                    obj = json.loads(quiz_inner)
                    opts = obj.get('options')
                    if isinstance(opts, list) and len(opts) >= 2:
                        random.shuffle(opts)
                        # Reatribui IDs sequenciais A, B, C, ... para refletir nova ordem
                        letters = [chr(ord('A') + i) for i in range(len(opts))]
                        for i, opt in enumerate(opts):
                            opt['id'] = letters[i]
                        obj['options'] = opts
                        new_block = f"```quiz\n{json.dumps(obj, ensure_ascii=False, indent=2)}\n```"
                except Exception:
                    new_block = None
                quiz_block = new_block or quiz_match.group(0)
                segments.append(ResponseSegment(
                    id=make_id("quiz", 1),
                    title="Quiz",
                    type="quiz",
                    content=quiz_block
                ))

            # Ordenação final: Reflexão -> Pergunta -> Intro/Análise -> Passos -> Exemplos -> Código final -> Quiz
            ordered: List[ResponseSegment] = []
            # Já inserimos reflexão no início; vamos reordenar explicitamente
            ref = [s for s in segments if s.type == "reflection"]
            ques = [question_segment] if question_segment else []
            intro = [s for s in segments if s.type == "intro"]
            steps = [s for s in segments if s.type == "steps"]
            ex_ok = [s for s in segments if s.type == "correct_example"]
            ex_bad = [s for s in segments if s.type == "incorrect_example"]
            codef = [s for s in segments if s.type == "final_code"]
            quizs = [s for s in segments if s.type == "quiz"]
            for group in (ref, ques, intro, steps, ex_ok, ex_bad, codef, quizs):
                for s in group:
                    if s:
                        ordered.append(s)
            return ordered

        blocks = _extract_fenced_blocks(response)
        extras: Dict[str, Any] = {}
        if team_extras:
            extras.update(team_extras)
        # Guarda código final para segmentação
        final_code_for_segments: Optional[Dict[str, Any]] = None
        if request.include_final_code:
            final_code = _pick_final_code(blocks, request.max_final_code_lines or 150)
            if final_code:
                extras['final_code'] = final_code
                metadata['final_code_lines'] = final_code.get('line_count')
                metadata['final_code_truncated'] = final_code.get('truncated')
                final_code_for_segments = final_code
            elif extras.get('final_code'):
                # Fallback: usar final_code vindo do team_extras se presente
                fc = extras.get('final_code') or {}
                if isinstance(fc, dict):
                    lang = (fc.get('language') or fc.get('lang') or 'text')
                    code = fc.get('code') or ''
                    if (code or '').strip():
                        final_code_for_segments = {
                            'language': (lang or 'text').lower(),
                            'code': code,
                            'truncated': bool(fc.get('truncated', False)),
                            'line_count': len(code.splitlines()),
                        }

        # Adiciona sugestões de próximos passos para worked examples
        if final_methodology == MethodologyType.WORKED_EXAMPLES:
            metadata["suggested_next_steps"] = [
                "Tente resolver um problema similar",
                "Identifique os padrões principais",
                "Pratique com variações do exemplo"
            ]
        
        try:
            segments = _build_segments(response, final_code_for_segments, request.user_query)
        except Exception as seg_err:
            # Fallback seguro se algo falhar na segmentação
            logger.error(f"Falha ao construir segmentos: {seg_err}")
            segments = None

        if segments:
            metadata["segments_count"] = len(segments)

        result = AgnoResponse(
            response=response,
            methodology=final_methodology.value,
            is_xml_formatted=False,  # Sempre False - agora geramos markdown diretamente
            metadata=metadata,
            extras=extras or None,
            segments=segments or None
        )

        # Persistir sessão/memória (melhor esforço)
        try:
            uid = getattr(request.user_context, 'user_id', None) if request.user_context else None
            if uid:
                duration_minutes = int((time.time() - start_time) / 60) or 0
                session = LearningSession(
                    id=str(uuid.uuid4()),
                    user_id=uid,
                    content_id=f"agno:{request.methodology}",
                    session_type="lesson",
                    start_time=start_dt,
                    end_time=datetime.utcnow(),
                    duration_minutes=duration_minutes,
                    interactions=[
                        {"role": "user", "message": request.user_query},
                        {"role": "system", "methodology": request.methodology, "content": response[:2000]}
                    ],
                    performance_score=None,
                    engagement_score=None,
                    difficulty_rating=None,
                    completed=True,
                )
                await pb_service.save_learning_session(session)
        except Exception:
            pass

        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/worked-example", response_model=AgnoResponse)
async def get_worked_example(
    request: AgnoRequest,
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Endpoint de conveniência para obter um worked example.
    
    Args:
        request: Requisição AGNO com pergunta e contexto
        agno_service: Instância do serviço AGNO
        
    Returns:
        AgnoResponse: Resposta em formato XML com worked example
    """
    # Força a metodologia para worked examples
    request.methodology = MethodologyType.WORKED_EXAMPLES.value
    
    return await ask_question(request, agno_service)

# --- Funções auxiliares ---

def _is_valid_methodology(methodology: str) -> bool:
    """Valida se uma metodologia é válida."""
    try:
        MethodologyType(methodology)
        return True
    except ValueError:
        return False

def _get_methodology_name(methodology: MethodologyType) -> str:
    """Retorna o nome legível de uma metodologia."""
    names = {
        MethodologyType.SEQUENTIAL_THINKING: "Pensamento Sequencial",
        MethodologyType.ANALOGY: "Analogias",
        MethodologyType.SOCRATIC: "Método Socrático",
        MethodologyType.SCAFFOLDING: "Scaffolding",
        MethodologyType.WORKED_EXAMPLES: "Exemplos Resolvidos",
        MethodologyType.DEFAULT: "Padrão"
    }
    return names.get(methodology, "Desconhecido")

def _get_methodology_description(methodology: MethodologyType) -> str:
    """Retorna a descrição de uma metodologia."""
    descriptions = {
        MethodologyType.SEQUENTIAL_THINKING: "Explica o raciocínio passo a passo de forma sequencial",
        MethodologyType.ANALOGY: "Usa analogias do cotidiano para facilitar o entendimento",
        MethodologyType.SOCRATIC: "Estimula o pensamento crítico através de perguntas",
        MethodologyType.SCAFFOLDING: "Oferece dicas graduais removendo o suporte progressivamente",
        MethodologyType.WORKED_EXAMPLES: "Ensina através de exemplos detalhadamente resolvidos",
        MethodologyType.DEFAULT: "Resposta educacional padrão, clara e objetiva"
    }
    return descriptions.get(methodology, "Descrição não disponível")

def _get_methodology_recommendations(methodology: MethodologyType) -> List[str]:
    """Retorna recomendações de uso para uma metodologia."""
    recommendations = {
        MethodologyType.SEQUENTIAL_THINKING: [
            "Problemas complexos com múltiplas etapas",
            "Estudantes que precisam de estrutura",
            "Conceitos que requerem ordem lógica"
        ],
        MethodologyType.ANALOGY: [
            "Conceitos abstratos",
            "Estudantes visuais",
            "Tópicos difíceis de visualizar"
        ],
        MethodologyType.SOCRATIC: [
            "Desenvolvimento de pensamento crítico",
            "Estudantes avançados",
            "Discussões conceituais"
        ],
        MethodologyType.SCAFFOLDING: [
            "Estudantes iniciantes",
            "Conceitos progressivos",
            "Desenvolvimento gradual de habilidades"
        ],
        MethodologyType.WORKED_EXAMPLES: [
            "Resolução de problemas",
            "Aprendizado de algoritmos",
            "Demonstração de técnicas"
        ],
        MethodologyType.DEFAULT: [
            "Uso geral",
            "Primeira interação",
            "Quando não há preferência específica"
        ]
    }
    return recommendations.get(methodology, [])

# --- Endpoints RAG ---

@router.post("/rag/index", response_model=Dict[str, str])
async def index_content(
    request: IndexContentRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Indexa novo conteúdo educacional no sistema RAG.

    Args:
        request: Conteúdo educacional a ser indexado
        rag_service: Instância do serviço RAG

    Returns:
        Dict com ID do conteúdo indexado
    """
    try:
        content = EducationalContent(
            id=str(uuid.uuid4()),
            title=request.title,
            content=request.content,
            content_type=request.content_type,
            subject=request.subject,
            topic=request.topic,
            difficulty=request.difficulty,
            methodology=request.methodology,
            tags=request.tags,
            metadata=request.metadata
        )

        content_id = await rag_service.index_content(content)

        return {"content_id": content_id, "status": "indexed"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao indexar conteúdo: {str(e)}"
        )

@router.post("/rag/search", response_model=List[SearchResult])
async def search_content(
    request: RAGSearchRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Busca conteúdo educacional relevante usando RAG.

    Args:
        request: Parâmetros de busca
        rag_service: Instância do serviço RAG

    Returns:
        Lista de resultados de busca ordenados por relevância
    """
    try:
        search_query = SearchQuery(
            query=request.query,
            user_context=request.user_context,
            filters=request.filters,
            limit=request.limit,
            score_threshold=request.score_threshold
        )

        results = await rag_service.search_content(search_query)
        return results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na busca: {str(e)}"
        )

@router.get("/rag/stats", response_model=Dict[str, Any])
async def get_rag_stats(
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Retorna estatísticas da coleção RAG.

    Args:
        rag_service: Instância do serviço RAG

    Returns:
        Estatísticas da coleção Qdrant
    """
    try:
        stats = await rag_service.get_collection_stats()
        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas: {str(e)}"
        )

# --- Endpoints de Agentes Educacionais ---

@router.post("/agent/ask", response_model=AgentResponse)
async def ask_educational_agent(
    request: EducationalAgentRequest,
    agent_service: EducationalAgentService = Depends(get_educational_agent_service)
):
    """
    Processa uma consulta usando agentes educacionais com RAG.

    Args:
        request: Consulta educacional com contexto do usuário
        agent_service: Instância do serviço de agentes educacionais

    Returns:
        Resposta personalizada do agente educacional
    """
    try:
        response = await agent_service.process_educational_query(
            query=request.query,
            user_id=request.user_id,
            user_profile=request.user_profile,
            session_id=request.session_id
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no processamento do agente: {str(e)}"
        )

@router.get("/agent/analytics/{user_id}", response_model=Dict[str, Any])
async def get_student_analytics(
    user_id: str,
    agent_service: EducationalAgentService = Depends(get_educational_agent_service)
):
    """
    Retorna analytics educacionais do estudante.

    Args:
        user_id: ID do usuário
        agent_service: Instância do serviço de agentes educacionais

    Returns:
        Estatísticas e métricas do estudante
    """
    try:
        analytics = await agent_service.get_student_analytics(user_id)
        return analytics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter analytics: {str(e)}"
        )

@router.post("/agent/profile", response_model=Dict[str, str])
async def update_student_profile(
    user_id: str,
    profile: Dict[str, Any],
    agent_service: EducationalAgentService = Depends(get_educational_agent_service)
):
    """
    Atualiza o perfil educacional do estudante.

    Args:
        user_id: ID do usuário
        profile: Dados do perfil a atualizar
        agent_service: Instância do serviço de agentes educacionais

    Returns:
        Confirmação da atualização
    """
    try:
        # Criar ou atualizar perfil
        student_profile = StudentProfile(
            user_id=user_id,
            name=profile.get("name"),
            learning_style=profile.get("learning_style", "visual"),
            current_level=profile.get("current_level", "intermediate"),
            subjects=profile.get("subjects", []),
            preferred_methodologies=profile.get("preferred_methodologies", []),
            learning_goals=profile.get("learning_goals", []),
            past_performance=profile.get("past_performance", {}),
            learning_pace=profile.get("learning_pace", "moderate"),
            preferred_difficulty=profile.get("preferred_difficulty", "adaptive"),
            accessibility_needs=profile.get("accessibility_needs", [])
        )

        agent_service.student_cache[user_id] = student_profile

        return {"status": "updated", "user_id": user_id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar perfil: {str(e)}"
        )

# --- Endpoints de Context Engineering e Ferramentas Cognitivas ---

@router.post("/cognitive/analyze", response_model=Dict[str, Any])
async def analyze_query_cognitively(
    query: str = Query(..., description="Query a ser analisada"),
    context: Optional[str] = Query(None, description="Contexto adicional"),
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Analisa uma query usando ferramentas cognitivas.

    Args:
        query: Query a ser analisada
        context: Contexto adicional
        agno_service: Instância do serviço AGNO

    Returns:
        Análise cognitiva completa da query
    """
    try:
        analysis = agno_service.analyze_query_cognitively(query, context)
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na análise cognitiva: {str(e)}"
        )

@router.post("/cognitive/validate-solution", response_model=Dict[str, Any])
async def validate_solution_cognitively(
    solution: str = Query(..., description="Solução a ser validada"),
    problem: str = Query(..., description="Problema original"),
    context: Optional[Dict[str, Any]] = None,
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Valida uma solução usando ferramentas cognitivas.

    Args:
        solution: Solução proposta
        problem: Problema original
        context: Contexto adicional
        agno_service: Instância do serviço AGNO

    Returns:
        Validação completa da solução
    """
    try:
        validation = agno_service.validate_solution_cognitively(
            solution, problem, context or {}
        )
        return validation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na validação cognitiva: {str(e)}"
        )

@router.get("/memory/stats", response_model=Dict[str, Any])
async def get_memory_stats(
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Retorna estatísticas da memória consolidada.

    Args:
        agno_service: Instância do serviço AGNO

    Returns:
        Estatísticas da memória consolidada
    """
    try:
        stats = agno_service.get_memory_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estatísticas de memória: {str(e)}"
        )

@router.get("/memory/state", response_model=Dict[str, Any])
async def get_memory_state(
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Retorna o estado atual da memória consolidada.

    Args:
        agno_service: Instância do serviço AGNO

    Returns:
        Estado atual da memória consolidada
    """
    try:
        state = agno_service.get_memory_state()
        return {
            "learned_concepts": state.learned_concepts,
            "progress_markers_count": len(state.progress_markers),
            "methodology_preferences": state.methodology_preferences,
            "error_patterns_count": len(state.error_patterns),
            "session_context_length": len(state.session_context),
            "last_updated": state.last_updated.isoformat() if state.last_updated else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter estado de memória: {str(e)}"
        )

@router.post("/memory/consolidate", response_model=Dict[str, Any])
async def consolidate_memory(
    interaction_data: Dict[str, Any],
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Consolida uma interação na memória.

    Args:
        interaction_data: Dados da interação
        agno_service: Instância do serviço AGNO

    Returns:
        Estado da memória após consolidação
    """
    try:
        consolidated_state = agno_service.consolidate_memory(interaction_data)
        stats = agno_service.get_memory_stats()

        return {
            "consolidated": True,
            "stats": stats,
            "learned_concepts_count": len(consolidated_state.learned_concepts),
            "last_updated": consolidated_state.last_updated.isoformat() if consolidated_state.last_updated else None
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na consolidação de memória: {str(e)}"
        )

# --- Endpoints Específicos para Controle de Metodologia ---

@router.post("/cognitive/suggest", response_model=Dict[str, Any])
async def get_methodology_suggestion(
    query: str = Query(..., description="Query para análise cognitiva"),
    context: Optional[str] = Query(None, description="Contexto adicional"),
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Retorna sugestão de metodologia baseada na análise cognitiva SEM processar a pergunta.
    Útil para mostrar ao usuário opções antes de escolher.

    Args:
        query: Query a ser analisada
        context: Contexto adicional
        agno_service: Instância do serviço AGNO

    Returns:
        Sugestão de metodologia com análise cognitiva
    """
    try:
        suggestion = agno_service.get_cognitive_suggestion(query, context)
        return suggestion
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao obter sugestão cognitiva: {str(e)}"
        )

@router.post("/ask/fixed-methodology", response_model=AgnoResponse)
async def ask_with_fixed_methodology(
    request: AgnoRequest,
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Processa uma pergunta MANTENDO EXATAMENTE a metodologia escolhida pelo usuário.
    NÃO permite alteração baseada na análise cognitiva.

    Args:
        request: Requisição AGNO com metodologia fixa
        agno_service: Instância do serviço AGNO

    Returns:
        Resposta usando exatamente a metodologia escolhida
    """
    try:
        # Valida a metodologia
        if not _is_valid_methodology(request.methodology):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Metodologia '{request.methodology}' não é válida"
            )

        methodology_enum = MethodologyType(request.methodology)

        # Processa com metodologia FIXA (sem override cognitivo)
        response = agno_service.ask_with_fixed_methodology(
            methodology=methodology_enum,
            user_query=request.user_query,
            context=request.context
        )

        return AgnoResponse(
            response=response,
            methodology=request.methodology,
            is_xml_formatted=False,
            metadata={
                "methodology_locked": True,
                "cognitive_override": False,
                "processing_mode": "fixed_methodology"
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )

@router.post("/ask/adaptive", response_model=AgnoResponse)
async def ask_with_cognitive_adaptation(
    request: AgnoRequest,
    agno_service: AgnoMethodologyService = Depends(get_agno_service)
):
    """
    Processa uma pergunta PERMITINDO adaptação cognitiva da metodologia.
    A análise cognitiva pode alterar a metodologia baseada na complexidade da query.

    Args:
        request: Requisição AGNO com metodologia inicial
        agno_service: Instância do serviço AGNO

    Returns:
        Resposta com possível adaptação da metodologia
    """
    try:
        # Valida a metodologia
        if not _is_valid_methodology(request.methodology):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Metodologia '{request.methodology}' não é válida"
            )

        methodology_enum = MethodologyType(request.methodology)

        # Processa com ADAPTAÇÃO COGNITIVA (permite override)
        response = agno_service.ask_with_cognitive_adaptation(
            methodology=methodology_enum,
            user_query=request.user_query,
            context=request.context
        )

        return AgnoResponse(
            response=response,
            methodology=request.methodology,  # metodologia original (pode ter sido alterada internamente)
            is_xml_formatted=False,
            metadata={
                "methodology_locked": False,
                "cognitive_override": True,
                "processing_mode": "cognitive_adaptation",
                "adaptation_possible": True
            }
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro de validação: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )