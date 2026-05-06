from typing import Any, Generator, Dict, List
from simple_agent.api.providers import OpenAIProvider, AnthropicProvider
from simple_agent.config.settings import APIConfig


class APIClient:
    def __init__(self, config: APIConfig):
        self._config = config
        self._provider = config.provider

        provider_config = {
            "api_key": config.api_key,
            "base_url": config.base_url,
            "model": config.model,
        }

        if self._provider == "openai":
            self._provider_impl = OpenAIProvider(provider_config)
        elif self._provider == "anthropic":
            self._provider_impl = AnthropicProvider(provider_config)
        else:
            raise ValueError(f"Unknown provider: {self._provider}")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        return self._provider_impl.send_message(messages, tools)

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        for chunk in self._provider_impl.stream_message(messages, tools):
            yield chunk