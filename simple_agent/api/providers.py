from abc import ABC, abstractmethod
from typing import Any, Generator, Dict, List, Optional
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from simple_agent.core.llm_logger import LLMLogger


class BaseProvider(ABC):
    @abstractmethod
    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        pass


class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any], logger: Optional[LLMLogger] = None):
        self.client = OpenAI(
            api_key=config.get("api_key") or "test-key",  # Fallback for tests
            base_url=config.get("base_url"),
        )
        self.model = config.get("model", "gpt-4o")
        self._logger = logger

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        # Generate request ID and log request
        request_id = LLMLogger.generate_request_id()
        if self._logger:
            self._logger.log_request(request_id, self.model, messages, tools)

        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }

        tool_calls = None
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]
            assistant_message["tool_calls"] = tool_calls

        # Log response
        if self._logger:
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            self._logger.log_response(
                request_id=request_id,
                content=response.choices[0].message.content,
                tool_calls=tool_calls,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
            )

        # Include request_id in response for tool logging
        assistant_message["_request_id"] = request_id
        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any], logger: Optional[LLMLogger] = None):
        # Anthropic uses OpenAI SDK with custom base_url
        self.client = OpenAI(
            api_key=config.get("api_key") or "test-key",  # Fallback for tests
            base_url=config.get("base_url", "https://api.anthropic.com"),
        )
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self._logger = logger

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        # Generate request ID and log request
        request_id = LLMLogger.generate_request_id()
        if self._logger:
            self._logger.log_request(request_id, self.model, messages, tools)

        # Anthropic compatible call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            extra_headers={"anthropic-version": "2023-06-01"},
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }

        tool_calls = None
        if response.choices[0].message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.choices[0].message.tool_calls
            ]
            assistant_message["tool_calls"] = tool_calls

        # Log response
        if self._logger:
            usage = None
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            self._logger.log_response(
                request_id=request_id,
                content=response.choices[0].message.content,
                tool_calls=tool_calls,
                usage=usage,
                finish_reason=response.choices[0].finish_reason,
            )

        # Include request_id in response for tool logging
        assistant_message["_request_id"] = request_id
        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            stream=True,
            extra_headers={"anthropic-version": "2023-06-01"},
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content