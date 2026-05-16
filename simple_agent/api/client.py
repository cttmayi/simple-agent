from pathlib import Path
from typing import Any, Generator, Dict, List, Optional
from simple_agent.api.providers import OpenAIProvider, AnthropicProvider
from simple_agent.config.settings import APIConfig
from simple_agent.core.llm_logger import LLMLogger


class APIClient:
    def __init__(self, config: APIConfig, logger: Optional[LLMLogger] = None):
        self._config = config
        self._provider = config.provider
        self._logger = logger

        provider_config = {
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
        }

        if self._provider == "openai":
            self._provider_impl = OpenAIProvider(provider_config, logger)
        elif self._provider == "anthropic":
            self._provider_impl = AnthropicProvider(provider_config, logger)
        else:
            raise ValueError(f"Unknown provider: {self._provider}")

    def send_message(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        return self._provider_impl.send_message(
            messages,
            tools,
            subagent_call_id=subagent_call_id,
            subagent_agent_name=subagent_agent_name,
        )

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        for chunk in self._provider_impl.stream_message(messages, tools):
            yield chunk

    @property
    def logger(self) -> Optional[LLMLogger]:
        """Get logger instance."""
        return self._logger