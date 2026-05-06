import pytest
from unittest.mock import Mock, patch
from simple_agent.api.client import APIClient
from simple_agent.config.settings import APIConfig

def test_api_client_init():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)
    assert client._provider == "openai"

def test_api_client_send_message():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)

    with patch.object(client._provider_impl, "send_message") as mock_send:
        mock_send.return_value = [{"role": "assistant", "content": "Response"}]

        messages = [{"role": "user", "content": "Hello"}]
        response = client.send_message(messages, tools=[])

        assert response == [{"role": "assistant", "content": "Response"}]
        mock_send.assert_called_once()

def test_api_client_stream():
    config = APIConfig(provider="openai", api_key="test-key")
    client = APIClient(config)

    chunks = ["Hello", " world", "!"]

    def mock_stream_func(messages, tools):
        for chunk in chunks:
            yield chunk

    with patch.object(client._provider_impl, "stream_message") as mock_stream:
        mock_stream.side_effect = mock_stream_func

        messages = [{"role": "user", "content": "Hello"}]
        result = []
        for chunk in client.stream_message(messages, tools=[]):
            result.append(chunk)

        assert result == chunks