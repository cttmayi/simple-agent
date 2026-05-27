from abc import ABC, abstractmethod
from typing import Any, Generator, Dict, List, Optional
from openai import OpenAI, Stream
from openai.types.chat import ChatCompletion, ChatCompletionChunk
import httpx
import time
import re
from simple_agent.core.llm_logger import LLMLogger


def _build_http_client() -> httpx.Client:
    """Build an httpx client that ignores system proxy environment variables."""
    return httpx.Client(proxy=None, trust_env=False, timeout=httpx.Timeout(300.0, connect=10.0))


class RetryConfig:
    """Retry configuration for API calls."""
    max_retries: int = float('inf')  # 无限重试
    initial_delay: float = 10.0      # 从 10s 开始
    max_delay: float = 60 * 60       # 最大 60 分钟
    backoff_factor: float = 2.0      # 指数退避因子

    @classmethod
    def get_delay(cls, attempt: int) -> float:
        """Calculate delay with exponential backoff.

        Args:
            attempt: Attempt number (1-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = cls.initial_delay * (cls.backoff_factor ** (attempt - 1))
        return min(delay, cls.max_delay)

    @classmethod
    def format_delay(cls, delay_seconds: float) -> str:
        """Format delay in human-readable format."""
        if delay_seconds < 60:
            return f"{int(delay_seconds)}秒"
        elif delay_seconds < 3600:
            minutes = int(delay_seconds / 60)
            return f"{minutes}分钟"
        else:
            hours = int(delay_seconds / 3600)
            minutes = int((delay_seconds % 3600) / 60)
            if minutes > 0:
                return f"{hours}小时{minutes}分钟"
            return f"{hours}小时"


class BaseProvider(ABC):
    @abstractmethod
    def send_message(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        pass

    def _should_retry(self, error: Exception) -> bool:
        """Determine if an error is retryable.

        Retryable errors include:
        - Connection errors (network issues)
        - Timeout errors
        - Rate limit errors (429)
        - Server errors (5xx)
        """
        error_msg = str(error).lower()
        error_type = type(error).__name__

        # Connection and timeout errors
        if "connection error" in error_msg or "timeout" in error_msg:
            return True

        # Rate limit (429)
        if "429" in error_msg or "rate limit" in error_msg:
            return True

        # Server errors (5xx) - use regex to match any 5xx code
        if re.search(r'5\d\d', error_msg) or "internal server error" in error_msg:
            return True

        # Specific OpenAI error types
        if error_type in ("APIConnectionError", "APITimeoutError", "InternalServerError"):
            return True

        return False


class OpenAIProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any], logger: Optional[LLMLogger] = None):
        # Strip trailing slashes from base_url to avoid double slash issues
        base_url = config.get("base_url")
        if base_url:
            base_url = base_url.rstrip('/')
        self.client = OpenAI(
            api_key=config.get("api_key") or "test-key",  # Fallback for tests
            base_url=base_url,
            http_client=_build_http_client(),
        )
        self.model = config.get("model", "gpt-4o")
        self._logger = logger

    def send_message(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        # Generate request ID and log request
        request_id = LLMLogger.generate_request_id()
        if self._logger:
            self._logger.log_request(
                request_id, self.model, messages, tools,
                subagent_call_id=subagent_call_id,
                subagent_agent_name=subagent_agent_name
            )

        # Retry logic for API calls
        response = None
        last_error = None
        attempt = 1
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools or None,
                )
                break
            except Exception as e:
                last_error = e
                if self._should_retry(e):
                    delay = RetryConfig.get_delay(attempt)
                    delay_str = RetryConfig.format_delay(delay)
                    print(f"[dim]连接错误，{delay_str}后重试... (第 {attempt} 次)[/dim]")
                    time.sleep(delay)
                    attempt += 1
                else:
                    raise

        if response is None:
            raise last_error if last_error else Exception("Unknown error")

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
                subagent_call_id=subagent_call_id,
                subagent_agent_name=subagent_agent_name,
            )

        # Include request_id and subagent context in response for tool logging
        assistant_message["_request_id"] = request_id
        if subagent_call_id:
            assistant_message["_subagent_call_id"] = subagent_call_id
        if subagent_agent_name:
            assistant_message["_subagent_agent_name"] = subagent_agent_name
        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        """Stream messages from the API with proper resource cleanup."""
        stream = None
        attempt = 1
        while True:
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools or None,
                    stream=True,
                )
                break
            except Exception as e:
                if self._should_retry(e):
                    delay = RetryConfig.get_delay(attempt)
                    delay_str = RetryConfig.format_delay(delay)
                    print(f"[dim]连接错误，{delay_str}后重试... (第 {attempt} 次)[/dim]")
                    time.sleep(delay)
                    attempt += 1
                else:
                    raise

        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        finally:
            # Ensure stream is closed properly
            if hasattr(stream, 'close'):
                stream.close()


class AnthropicProvider(BaseProvider):
    def __init__(self, config: Dict[str, Any], logger: Optional[LLMLogger] = None):
        # Anthropic uses OpenAI SDK with custom base_url
        # Strip trailing slashes from base_url to avoid double slash issues
        base_url = config.get("base_url", "https://api.anthropic.com")
        if base_url:
            base_url = base_url.rstrip('/')
        self.client = OpenAI(
            api_key=config.get("api_key") or "test-key",  # Fallback for tests
            base_url=base_url,
            http_client=_build_http_client(),
        )
        self.model = config.get("model", "claude-sonnet-4-20250514")
        self._logger = logger

    def send_message(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        subagent_call_id: Optional[str] = None,
        subagent_agent_name: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        # Generate request ID and log request
        request_id = LLMLogger.generate_request_id()
        if self._logger:
            self._logger.log_request(
                request_id, self.model, messages, tools,
                subagent_call_id=subagent_call_id,
                subagent_agent_name=subagent_agent_name
            )

        # Anthropic compatible call
        base_url = str(self.client.base_url) if self.client.base_url else ""
        extra_headers = {}
        # Only add anthropic-version header if not using ByteDance/Volcano API
        if "ark.cn-beijing.volces.com" not in base_url and "api.volcengine.com" not in base_url:
            extra_headers["anthropic-version"] = "2023-06-01"

        # Retry logic
        response = None
        last_error = None
        attempt = 1
        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools or None,
                    extra_headers=extra_headers if extra_headers else None,
                )
                break
            except Exception as e:
                last_error = e
                if self._should_retry(e):
                    delay = RetryConfig.get_delay(attempt)
                    delay_str = RetryConfig.format_delay(delay)
                    print(f"[dim]连接错误，{delay_str}后重试... (第 {attempt} 次)[/dim]")
                    time.sleep(delay)
                    attempt += 1
                else:
                    raise

        if response is None:
            raise last_error if last_error else Exception("Unknown error")

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
                subagent_call_id=subagent_call_id,
                subagent_agent_name=subagent_agent_name,
            )

        # Include request_id and subagent context in response for tool logging
        assistant_message["_request_id"] = request_id
        if subagent_call_id:
            assistant_message["_subagent_call_id"] = subagent_call_id
        if subagent_agent_name:
            assistant_message["_subagent_agent_name"] = subagent_agent_name
        return [assistant_message]

    def stream_message(
        self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]]
    ) -> Generator[str, None]:
        """Stream messages from the API with proper resource cleanup."""
        base_url = str(self.client.base_url) if self.client.base_url else ""
        extra_headers = {}
        # Only add anthropic-version header if not using ByteDance/Volcano API
        if "ark.cn-beijing.volces.com" not in base_url and "api.volcengine.com" not in base_url:
            extra_headers["anthropic-version"] = "2023-06-01"

        stream = None
        attempt = 1
        while True:
            try:
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools or None,
                    stream=True,
                    extra_headers=extra_headers if extra_headers else None,
                )
                break
            except Exception as e:
                if self._should_retry(e):
                    delay = RetryConfig.get_delay(attempt)
                    delay_str = RetryConfig.format_delay(delay)
                    print(f"[dim]连接错误，{delay_str}后重试... (第 {attempt} 次)[/dim]")
                    time.sleep(delay)
                    attempt += 1
                else:
                    raise

        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        finally:
            # Ensure stream is closed properly
            if hasattr(stream, 'close'):
                stream.close()