from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

from backend.config import AppConfig, get_config
from backend.llm.openai import OpenAITooledChat
from backend.types import MessageList, TextMessage, ToolBinding

# filepath: backend/llm/test_openai.py


@dataclass
class MockResponseContent:
    type: str
    text: Optional[str] = None


@dataclass
class MockResponseOutput:
    type: str
    name: Optional[str] = None
    arguments: Optional[str] = None
    call_id: Optional[str] = None
    content: Optional[List[MockResponseContent]] = None


@pytest.fixture
def config() -> AppConfig:
    return get_config()


@pytest.fixture
def mock_tools() -> dict[str, ToolBinding]:
    return {
        "make_calculation": {
            "ref": lambda x, y: x + y,
            "schema": {"name": "make_calculation", "description": "Adds two numbers"},
        }
    }


@pytest.fixture
def openai_tooled_chat(config, mock_tools):
    return OpenAITooledChat(config=config, tools=mock_tools)


@patch("backend.llm.openai.openai.responses.create")
async def test_create_response_single_message(mock_create, openai_tooled_chat):
    # Mock OpenAI response with a single message
    mock_create.return_value = MagicMock(
        output=[
            MockResponseOutput(type="message", content=[MockResponseContent(type="output_text", text="Hello, world!")])
        ]
    )

    messages = MessageList([])
    response = await openai_tooled_chat.create_response(messages)

    assert isinstance(response, TextMessage)
    assert response.content == "Hello, world!"


@patch("backend.llm.openai.openai.responses.create")
async def test_create_response_function_call(mock_create, openai_tooled_chat):
    # Mock OpenAI response with a function call
    mock_create.side_effect = [
        MagicMock(
            output=[
                MockResponseOutput(
                    type="function_call", name="make_calculation", arguments='{"x": 2, "y": 3}', call_id="123"
                )
            ]
        ),
        MagicMock(
            output=[
                MockResponseOutput(type="message", content=[MockResponseContent(type="output_text", text="Result: 5")])
            ]
        ),
    ]

    # Ensure the tool mock is properly configured
    openai_tooled_chat.tools["make_calculation"] = {
        "ref": lambda x, y: x + y,
        "schema": {"name": "make_calculation", "description": "Adds two numbers"},
    }

    messages = MessageList([])
    response = await openai_tooled_chat.create_response(messages)

    assert isinstance(response, TextMessage)
    assert response.content == "Result: 5"


@patch("backend.llm.openai.openai.responses.create")
async def test_create_response_unsupported_type(mock_create, openai_tooled_chat, caplog):
    # Mock OpenAI response with an unsupported type
    mock_create.return_value = MagicMock(output=[MockResponseOutput(type="unsupported_type")])

    messages = MessageList([])
    response = await openai_tooled_chat.create_response(messages)

    assert isinstance(response, TextMessage)
    assert response.content == "error, unexpected response type from LLM"
    assert "Unsupported response from OpenAI" in caplog.text


@patch("backend.llm.openai.openai.responses.create")
async def test_create_response_multiple_outputs(mock_create, openai_tooled_chat, caplog):
    # Mock OpenAI response with multiple outputs
    mock_create.return_value = MagicMock(
        output=[
            MockResponseOutput(type="message", content=[MockResponseContent(type="output_text", text="Message 1")]),
            MockResponseOutput(type="message", content=[MockResponseContent(type="output_text", text="Message 2")]),
        ]
    )

    messages = MessageList([])
    response = await openai_tooled_chat.create_response(messages)

    assert isinstance(response, TextMessage)
    assert response.content == "error, unexpected response type from LLM"
    assert "Unsupported response from OpenAI" in caplog.text
