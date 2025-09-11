"""
Modelos customizados para AGNO que suportam múltiplos provedores de IA.

Este módulo implementa modelos compatíveis com a biblioteca AGNO para
diferentes provedores como OpenAI e Claude (Anthropic).
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

# Imports necessários
from agno.models.base import Model
from agno.models.response import ModelResponse
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import MessageParam
from openai import OpenAI, AsyncOpenAI
import ollama
import aiohttp

from ..config import settings

logger = logging.getLogger(__name__)

@dataclass
class ClaudeConfig:
    """Configuração para modelos Claude/Anthropic."""
    api_key: str
    model_name: str
    max_tokens: int = 4096
    temperature: float = 0.7
    base_url: str = "https://api.anthropic.com"

@dataclass
class OllamaConfig:
    """Configuração para modelos Ollama (local)."""
    model_name: str
    host: str = "http://localhost:11434"
    timeout: int = 120
    temperature: float = 0.7
    num_ctx: int = 4096

@dataclass
class OpenRouterConfig:
    """Configuração para Open Router."""
    api_key: str
    model_name: str
    base_url: str = "https://openrouter.ai/api/v1"
    max_tokens: int = 4096
    temperature: float = 0.7

class ClaudeModel(Model):
    """
    Implementação de modelo Claude compatível com AGNO.
    
    Esta classe adapta a API do Claude/Anthropic para funcionar
    com a interface esperada pela biblioteca AGNO.
    """
    
    def __init__(
        self,
        id: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Inicializa o modelo Claude.
        
        Args:
            id: ID do modelo Claude
            api_key: Chave da API Anthropic (usa variável de ambiente se não fornecida)
            max_tokens: Número máximo de tokens na resposta
            temperature: Temperatura para geração
            **kwargs: Argumentos adicionais
        """
        super().__init__(id=id, **kwargs)
        
        self.api_key = api_key or settings.claude_api_key
        self.model_name = id
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        if not self.api_key:
            raise ValueError("Claude API key is required but not provided")
        
        # Log para debug
        logger.info(f"Inicializando ClaudeModel com chave: {self.api_key[:20]}...{self.api_key[-10:] if self.api_key else None}")
        logger.info(f"Modelo: {self.model_name}")
        
        # Inicializar clientes síncronos e assíncronos
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
    
    def _format_messages_for_claude(self, messages: List[Dict[str, Any]]) -> tuple[str, List[MessageParam]]:
        """
        Converte mensagens do formato AGNO para o formato Claude.
        
        Args:
            messages: Lista de mensagens no formato AGNO
            
        Returns:
            Tuple com (system_prompt, claude_messages)
        """
        system_prompt = ""
        claude_messages: List[MessageParam] = []
        
        # Se messages é uma string simples, converter para formato adequado
        if isinstance(messages, str):
            claude_messages.append(MessageParam(role="user", content=messages))
            return system_prompt, claude_messages
        
        for message in messages:
            # Converter Message object para dict se necessário
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            elif hasattr(message, '__dict__'):
                message_dict = message.__dict__
            elif isinstance(message, dict):
                message_dict = message
            elif isinstance(message, str):
                # Se for string simples, tratar como mensagem de usuário
                claude_messages.append(MessageParam(role="user", content=message))
                continue
            else:
                logger.warning(f"Tipo de mensagem desconhecido: {type(message)}")
                continue
                
            role = message_dict.get("role", "user")
            content = message_dict.get("content", "")
            
            # Garantir que content seja string
            if not isinstance(content, str):
                content = str(content)
            
            if role == "system":
                system_prompt = content
            elif role in ["user", "assistant"]:
                claude_messages.append(MessageParam(role=role, content=content))
        
        return system_prompt, claude_messages
    
    def _create_model_response(self, claude_response: Any) -> ModelResponse:
        """
        Converte resposta do Claude para formato ModelResponse do AGNO.
        
        Args:
            claude_response: Resposta da API Claude
            
        Returns:
            ModelResponse compatível com AGNO
        """
        # Extrair conteúdo da resposta
        if hasattr(claude_response, 'content') and claude_response.content:
            content = claude_response.content[0].text if claude_response.content else ""
        else:
            content = str(claude_response)
        
        # Criar usage info se disponível (simplificado)
        usage = None
        if hasattr(claude_response, 'usage'):
            usage = {
                'input_tokens': getattr(claude_response.usage, 'input_tokens', 0),
                'output_tokens': getattr(claude_response.usage, 'output_tokens', 0),
                'total_tokens': getattr(claude_response.usage, 'input_tokens', 0) + 
                              getattr(claude_response.usage, 'output_tokens', 0)
            }
        
        return ModelResponse(
            content=content
        )
    
    def invoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Claude de forma síncrona.
        
        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais
            
        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            system_prompt, claude_messages = self._format_messages_for_claude(messages)
            
            # Fazer chamada para Claude
            call_kwargs = {
                "model": self.model_name,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "messages": claude_messages
            }
            
            # Só adicionar system se não estiver vazio
            if system_prompt and system_prompt.strip():
                call_kwargs["system"] = system_prompt
            
            response = self.client.messages.create(**call_kwargs)
            
            return self._create_model_response(response)
            
        except Exception as e:
            logger.error(f"Erro ao invocar modelo Claude: {str(e)}")
            raise
    
    async def ainvoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Claude de forma assíncrona.
        
        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais
            
        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            system_prompt, claude_messages = self._format_messages_for_claude(messages)
            
            # Fazer chamada assíncrona para Claude
            call_kwargs = {
                "model": self.model_name,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "messages": claude_messages
            }
            
            # Só adicionar system se não estiver vazio
            if system_prompt and system_prompt.strip():
                call_kwargs["system"] = system_prompt
            
            response = await self.async_client.messages.create(**call_kwargs)
            
            return self._create_model_response(response)
            
        except Exception as e:
            logger.error(f"Erro ao invocar modelo Claude (async): {str(e)}")
            raise
    
    def response(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência para obter apenas o texto da resposta.
        
        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais
            
        Returns:
            String com o conteúdo da resposta
        """
        try:
            # Converter string para formato de mensagens se necessário
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]
            
            model_response = self.invoke(messages, **kwargs)
            return model_response.content
        except Exception as e:
            logger.error(f"Erro no método response: {e}")
            raise
    
    async def aresponse(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência assíncrono para obter apenas o texto da resposta.
        
        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais
            
        Returns:
            String com o conteúdo da resposta
        """
        # Converter string para formato de mensagens se necessário
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        
        model_response = await self.ainvoke(messages, **kwargs)
        return model_response.content
    
    # Implementar métodos abstratos necessários
    def invoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming síncrono - implementação básica que retorna resposta completa."""
        try:
            # Por enquanto, retorna a resposta completa como se fosse streaming
            response = self.invoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming síncrono: {e}")
            raise
    
    async def ainvoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming assíncrono - implementação básica que retorna resposta completa."""
        try:
            # Por enquanto, retorna a resposta completa como se fosse streaming
            response = await self.ainvoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming assíncrono: {e}")
            raise
    
    def parse_provider_response(self, response: Any) -> Dict[str, Any]:
        """Parse response do provedor."""
        try:
            if hasattr(response, 'content') and response.content:
                content = response.content[0].text if response.content else ""
            else:
                content = str(response)
            
            usage = {}
            if hasattr(response, 'usage'):
                usage = {
                    'input_tokens': getattr(response.usage, 'input_tokens', 0),
                    'output_tokens': getattr(response.usage, 'output_tokens', 0),
                    'total_tokens': getattr(response.usage, 'input_tokens', 0) + 
                                  getattr(response.usage, 'output_tokens', 0)
                }
            
            return {
                "content": content,
                "model": getattr(response, 'model', self.model_name)
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse da resposta: {e}")
            return {"content": str(response)}
    
    def parse_provider_response_delta(self, delta: Any) -> Dict[str, Any]:
        """Parse response delta do provedor."""
        try:
            if hasattr(delta, 'content'):
                content = delta.content
            elif hasattr(delta, 'text'):
                content = delta.text
            else:
                content = str(delta)
            
            return {
                "content": content,
                "delta": True
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse do delta: {e}")
            return {"content": str(delta)}


class OllamaModel(Model):
    """
    Implementação de modelo Ollama compatível com AGNO.

    Esta classe adapta a API do Ollama para funcionar
    com a interface esperada pela biblioteca AGNO.
    """

    def __init__(
        self,
        id: str = "llama3.2",
        host: str = "http://localhost:11434",
        timeout: int = 120,
        temperature: float = 0.7,
        num_ctx: int = 4096,
        **kwargs
    ):
        """
        Inicializa o modelo Ollama.

        Args:
            id: Nome do modelo Ollama
            host: URL do servidor Ollama
            timeout: Timeout para requisições
            temperature: Temperatura para geração
            num_ctx: Contexto máximo
            **kwargs: Argumentos adicionais
        """
        super().__init__(id=id, **kwargs)

        self.model_name = id
        self.host = host
        self.timeout = timeout
        self.temperature = temperature
        self.num_ctx = num_ctx

        # Inicializar cliente Ollama
        self.client = ollama.Client(host=host, timeout=timeout)

        logger.info(f"Inicializando OllamaModel: {self.model_name} em {self.host}")

    def _format_messages_for_ollama(self, messages: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Converte mensagens do formato AGNO para o formato Ollama.

        Args:
            messages: Lista de mensagens no formato AGNO

        Returns:
            Tuple com (system_prompt, ollama_messages)
        """
        system_prompt = ""
        ollama_messages: List[Dict[str, Any]] = []

        for message in messages:
            # Converter Message object para dict se necessário
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            elif hasattr(message, '__dict__'):
                message_dict = message.__dict__
            elif isinstance(message, dict):
                message_dict = message
            elif isinstance(message, str):
                ollama_messages.append({"role": "user", "content": message})
                continue
            else:
                logger.warning(f"Tipo de mensagem desconhecido: {type(message)}")
                continue

            role = message_dict.get("role", "user")
            content = message_dict.get("content", "")

            if not isinstance(content, str):
                content = str(content)

            if role == "system":
                system_prompt = content
            elif role in ["user", "assistant"]:
                ollama_messages.append({"role": role, "content": content})

        return system_prompt, ollama_messages

    def _create_model_response(self, ollama_response: Any) -> ModelResponse:
        """
        Converte resposta do Ollama para formato ModelResponse do AGNO.

        Args:
            ollama_response: Resposta da API Ollama

        Returns:
            ModelResponse compatível com AGNO
        """
        if isinstance(ollama_response, dict) and 'response' in ollama_response:
            content = ollama_response['response']
        elif hasattr(ollama_response, 'get'):
            content = ollama_response.get('response', str(ollama_response))
        else:
            content = str(ollama_response)

        return ModelResponse(content=content)

    def invoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Ollama de forma síncrona.

        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais

        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            system_prompt, ollama_messages = self._format_messages_for_ollama(messages)

            # Preparar opções do Ollama
            options = {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_ctx": kwargs.get("num_ctx", self.num_ctx),
            }

            # Fazer chamada para Ollama
            response = self.client.generate(
                model=self.model_name,
                prompt=self._messages_to_prompt(ollama_messages, system_prompt),
                options=options,
                stream=False
            )

            return self._create_model_response(response)

        except Exception as e:
            logger.error(f"Erro ao invocar modelo Ollama: {str(e)}")
            raise

    async def ainvoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Ollama de forma assíncrona.

        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais

        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            system_prompt, ollama_messages = self._format_messages_for_ollama(messages)

            # Preparar opções do Ollama
            options = {
                "temperature": kwargs.get("temperature", self.temperature),
                "num_ctx": kwargs.get("num_ctx", self.num_ctx),
            }

            # Fazer chamada assíncrona para Ollama
            # Ollama não tem API assíncrona nativa, então executamos em thread separado
            import concurrent.futures

            def _generate():
                return self.client.generate(
                    model=self.model_name,
                    prompt=self._messages_to_prompt(ollama_messages, system_prompt),
                    options=options,
                    stream=False
                )

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_generate)
                response = await asyncio.wrap_future(future)

            return self._create_model_response(response)

        except Exception as e:
            logger.error(f"Erro ao invocar modelo Ollama (async): {str(e)}")
            raise

    def _messages_to_prompt(self, messages: List[Dict[str, Any]], system_prompt: str = "") -> str:
        """
        Converte mensagens para um prompt único (Ollama usa chat completion).

        Args:
            messages: Lista de mensagens
            system_prompt: Prompt do sistema

        Returns:
            String formatada para Ollama
        """
        prompt_parts = []

        if system_prompt:
            prompt_parts.append(f"Sistema: {system_prompt}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                prompt_parts.append(f"Usuário: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistente: {content}")

        return "\n\n".join(prompt_parts)

    def response(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência para obter apenas o texto da resposta.

        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais

        Returns:
            String com o conteúdo da resposta
        """
        try:
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]

            model_response = self.invoke(messages, **kwargs)
            return model_response.content
        except Exception as e:
            logger.error(f"Erro no método response: {e}")
            raise

    async def aresponse(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência assíncrono para obter apenas o texto da resposta.

        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais

        Returns:
            String com o conteúdo da resposta
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        model_response = await self.ainvoke(messages, **kwargs)
        return model_response.content

    def invoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming síncrono - implementação básica que retorna resposta completa."""
        try:
            response = self.invoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming síncrono: {e}")
            raise

    async def ainvoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming assíncrono - implementação básica que retorna resposta completa."""
        try:
            response = await self.ainvoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming assíncrono: {e}")
            raise

    def parse_provider_response(self, response: Any) -> Dict[str, Any]:
        """Parse response do provedor."""
        try:
            if isinstance(response, dict) and 'response' in response:
                content = response['response']
            elif hasattr(response, 'get'):
                content = response.get('response', str(response))
            else:
                content = str(response)

            return {
                "content": content,
                "model": getattr(response, 'model', self.model_name)
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse da resposta: {e}")
            return {"content": str(response)}

    def parse_provider_response_delta(self, delta: Any) -> Dict[str, Any]:
        """Parse response delta do provedor."""
        try:
            if isinstance(delta, dict) and 'response' in delta:
                content = delta['response']
            elif hasattr(delta, 'get'):
                content = delta.get('response', str(delta))
            else:
                content = str(delta)

            return {
                "content": content,
                "delta": True
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse do delta: {e}")
            return {"content": str(delta)}


class OpenRouterModel(Model):
    """
    Implementação de modelo Open Router compatível com AGNO.

    Esta classe adapta a API do Open Router para funcionar
    com a interface esperada pela biblioteca AGNO.
    """

    def __init__(
        self,
        id: str = "anthropic/claude-3-5-sonnet",
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Inicializa o modelo Open Router.

        Args:
            id: ID do modelo Open Router (ex: "anthropic/claude-3-5-sonnet")
            api_key: Chave da API Open Router
            base_url: URL base da API
            max_tokens: Número máximo de tokens na resposta
            temperature: Temperatura para geração
            **kwargs: Argumentos adicionais
        """
        super().__init__(id=id, **kwargs)

        self.api_key = api_key or settings.openrouter_api_key
        self.model_name = id
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_key:
            raise ValueError("Open Router API key is required but not provided")

        # Inicializar cliente HTTP
        self.session = None

        logger.info(f"Inicializando OpenRouterModel: {self.model_name}")

    async def _ensure_session(self):
        """Garante que a sessão HTTP está inicializada."""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

    async def close(self):
        """Fecha a sessão HTTP."""
        if self.session:
            await self.session.close()
            self.session = None

    def _format_messages_for_openrouter(self, messages: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """
        Converte mensagens do formato AGNO para o formato Open Router.

        Args:
            messages: Lista de mensagens no formato AGNO

        Returns:
            Tuple com (system_prompt, openrouter_messages)
        """
        system_prompt = ""
        openrouter_messages: List[Dict[str, Any]] = []

        for message in messages:
            # Converter Message object para dict se necessário
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            elif hasattr(message, '__dict__'):
                message_dict = message.__dict__
            elif isinstance(message, dict):
                message_dict = message
            elif isinstance(message, str):
                openrouter_messages.append({"role": "user", "content": message})
                continue
            else:
                logger.warning(f"Tipo de mensagem desconhecido: {type(message)}")
                continue

            role = message_dict.get("role", "user")
            content = message_dict.get("content", "")

            if not isinstance(content, str):
                content = str(content)

            if role == "system":
                system_prompt = content
            elif role in ["user", "assistant"]:
                openrouter_messages.append({"role": role, "content": content})

        return system_prompt, openrouter_messages

    def _create_model_response(self, openrouter_response: Any) -> ModelResponse:
        """
        Converte resposta do Open Router para formato ModelResponse do AGNO.

        Args:
            openrouter_response: Resposta da API Open Router

        Returns:
            ModelResponse compatível com AGNO
        """
        if isinstance(openrouter_response, dict):
            if 'choices' in openrouter_response and openrouter_response['choices']:
                content = openrouter_response['choices'][0]['message']['content']
            else:
                content = str(openrouter_response)
        else:
            content = str(openrouter_response)

        return ModelResponse(content=content)

    async def _make_api_call(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Faz chamada para a API do Open Router.

        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais

        Returns:
            Resposta da API
        """
        await self._ensure_session()

        system_prompt, openrouter_messages = self._format_messages_for_openrouter(messages)

        payload = {
            "model": self.model_name,
            "messages": openrouter_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
        }

        url = f"{self.base_url}/chat/completions"

        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Open Router API error: {response.status} - {error_text}")

            return await response.json()

    def invoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Open Router de forma síncrona.

        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais

        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            # Executar chamada assíncrona em loop de eventos
            import nest_asyncio
            nest_asyncio.apply()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                response_data = loop.run_until_complete(self._make_api_call(messages, **kwargs))
                return self._create_model_response(response_data)
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Erro ao invocar modelo Open Router: {str(e)}")
            raise

    async def ainvoke(self, messages: List[Dict[str, Any]], **kwargs) -> ModelResponse:
        """
        Invoca o modelo Open Router de forma assíncrona.

        Args:
            messages: Lista de mensagens
            **kwargs: Argumentos adicionais

        Returns:
            ModelResponse com a resposta do modelo
        """
        try:
            response_data = await self._make_api_call(messages, **kwargs)
            return self._create_model_response(response_data)

        except Exception as e:
            logger.error(f"Erro ao invocar modelo Open Router (async): {str(e)}")
            raise

    def response(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência para obter apenas o texto da resposta.

        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais

        Returns:
            String com o conteúdo da resposta
        """
        try:
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]

            model_response = self.invoke(messages, **kwargs)
            return model_response.content
        except Exception as e:
            logger.error(f"Erro no método response: {e}")
            raise

    async def aresponse(self, messages: Union[str, List[Dict[str, Any]]], **kwargs) -> str:
        """
        Método de conveniência assíncrono para obter apenas o texto da resposta.

        Args:
            messages: Mensagens (string ou lista)
            **kwargs: Argumentos adicionais

        Returns:
            String com o conteúdo da resposta
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        model_response = await self.ainvoke(messages, **kwargs)
        return model_response.content

    def invoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming síncrono - implementação básica que retorna resposta completa."""
        try:
            response = self.invoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming síncrono: {e}")
            raise

    async def ainvoke_stream(self, messages: List[Dict[str, Any]], **kwargs):
        """Streaming assíncrono - implementação básica que retorna resposta completa."""
        try:
            response = await self.ainvoke(messages, **kwargs)
            yield response
        except Exception as e:
            logger.error(f"Erro no streaming assíncrono: {e}")
            raise

    def parse_provider_response(self, response: Any) -> Dict[str, Any]:
        """Parse response do provedor."""
        try:
            if isinstance(response, dict):
                if 'choices' in response and response['choices']:
                    content = response['choices'][0]['message']['content']
                else:
                    content = str(response)
            else:
                content = str(response)

            return {
                "content": content,
                "model": getattr(response, 'model', self.model_name)
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse da resposta: {e}")
            return {"content": str(response)}

    def parse_provider_response_delta(self, delta: Any) -> Dict[str, Any]:
        """Parse response delta do provedor."""
        try:
            if isinstance(delta, dict):
                if 'choices' in delta and delta['choices']:
                    content = delta['choices'][0]['delta']['content']
                else:
                    content = str(delta)
            else:
                content = str(delta)

            return {
                "content": content,
                "delta": True
            }
        except Exception as e:
            logger.error(f"Erro ao fazer parse do delta: {e}")
            return {"content": str(delta)}


def create_model(provider: str, model_name: str, **kwargs) -> Model:
    """
    Factory function para criar modelos baseado no provedor.

    Args:
        provider: Nome do provedor ('openai', 'claude', 'ollama', 'openrouter')
        model_name: Nome do modelo
        **kwargs: Argumentos adicionais para o modelo

    Returns:
        Instância do modelo apropriado

    Raises:
        ValueError: Se o provedor não for suportado
    """
    provider_lower = provider.lower()

    if provider_lower == 'claude':
        return ClaudeModel(id=model_name, **kwargs)
    elif provider_lower == 'openai':
        # Usar o modelo OpenAI padrão da AGNO
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_name, **kwargs)
    elif provider_lower == 'ollama':
        return OllamaModel(id=model_name, **kwargs)
    elif provider_lower == 'openrouter':
        return OpenRouterModel(id=model_name, **kwargs)
    else:
        raise ValueError(f"Provedor não suportado: {provider}. Use 'openai', 'claude', 'ollama' ou 'openrouter'.")


# Modelos pré-configurados para conveniência
CLAUDE_MODELS = {
    "claude-3-opus": "claude-3-opus-20240229",
    "claude-3-sonnet": "claude-3-sonnet-20240229",
    "claude-3-haiku": "claude-3-haiku-20240307",
    "claude-3-5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
}

OPENAI_MODELS = {
    "gpt-3.5-turbo": "gpt-3.5-turbo",
    "gpt-4": "gpt-4",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "o3-mini": "o3-mini",
}

OLLAMA_MODELS = {
    "llama3.2": "llama3.2",
    "llama3.2:1b": "llama3.2:1b",
    "llama3.2:3b": "llama3.2:3b",
    "llama3.1": "llama3.1",
    "llama3.1:8b": "llama3.1:8b",
    "llama3.1:70b": "llama3.1:70b",
    "llama3.1:405b": "llama3.1:405b",
    "mistral": "mistral",
    "mistral:7b": "mistral:7b",
    "codellama": "codellama",
    "codellama:7b": "codellama:7b",
    "codellama:13b": "codellama:13b",
    "codellama:34b": "codellama:34b",
    "qwen2": "qwen2",
    "qwen2:0.5b": "qwen2:0.5b",
    "qwen2:1.5b": "qwen2:1.5b",
    "qwen2:7b": "qwen2:7b",
    "qwen2:72b": "qwen2:72b",
    "gemma": "gemma",
    "gemma:2b": "gemma:2b",
    "gemma:7b": "gemma:7b",
}

OPENROUTER_MODELS = {
    # Modelos Claude via Open Router
    "anthropic/claude-3-5-sonnet": "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-haiku": "anthropic/claude-3-haiku",
    "anthropic/claude-3-opus": "anthropic/claude-3-opus",

    # Modelos OpenAI via Open Router
    "openai/gpt-4o": "openai/gpt-4o",
    "openai/gpt-4o-mini": "openai/gpt-4o-mini",
    "openai/gpt-4-turbo": "openai/gpt-4-turbo",
    "openai/gpt-3.5-turbo": "openai/gpt-3.5-turbo",

    # Modelos Google via Open Router
    "google/gemini-pro": "google/gemini-pro",
    "google/gemini-pro-vision": "google/gemini-pro-vision",

    # Modelos Meta via Open Router
    "meta-llama/llama-3-70b-instruct": "meta-llama/llama-3-70b-instruct",
    "meta-llama/llama-3-8b-instruct": "meta-llama/llama-3-8b-instruct",

    # Modelos Mistral via Open Router
    "mistralai/mistral-7b-instruct": "mistralai/mistral-7b-instruct",
    "mistralai/mixtral-8x7b-instruct": "mistralai/mixtral-8x7b-instruct",
}

def get_available_models() -> Dict[str, Dict[str, str]]:
    """
    Retorna todos os modelos disponíveis organizados por provedor.

    Returns:
        Dictionary com modelos por provedor
    """
    return {
        "claude": CLAUDE_MODELS,
        "openai": OPENAI_MODELS,
        "ollama": OLLAMA_MODELS,
        "openrouter": OPENROUTER_MODELS,
    } 