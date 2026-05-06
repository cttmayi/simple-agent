from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk


class BaseProvider(ABC):
    @abstractmethod
    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        pass


class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any]):
        self.client = OpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
        )
        self.model = config.get("model", "gpt-4o")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        response: ChatCompletion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content or "",
        }

        if response.choices[0].message.tool_calls:
            assistant_message["tool_calls"] = [
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

        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
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
    def __init__(self, config: Dict[str, Any]):
        # Anthropic uses OpenAI SDK with custom base_url
        self.client = OpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.anthropic.com"),
        )
        self.model = config.get("model", "claude-sonnet-4-20250514")

    def send_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
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

        if response.choices[0].message.tool_calls:
            assistant_message["tool_calls"] = [
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

        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
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