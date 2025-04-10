from pydantic import BaseModel
from typing import Literal, TypedDict, Callable


class TextMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class FunctionCallRequest(BaseModel):
    type: Literal["function_call"]
    name: str
    arguments: str  # JSON string of arguments
    call_id: str


class FunctionCallOutput(BaseModel):
    type: Literal["function_call_output"]
    call_id: str
    output: str


Message = TextMessage | FunctionCallRequest | FunctionCallOutput

MessageList = list[Message]


class ChatRequest(BaseModel):
    messages: MessageList


# XXX: This tool definition is OpenAI specific, might need to refactor to support other LLM API's
class ToolDefinition(TypedDict):
    type: Literal["function"]
    name: str
    description: str
    parameters: dict


class ToolBinding(TypedDict):
    ref: Callable
    schema: ToolDefinition
