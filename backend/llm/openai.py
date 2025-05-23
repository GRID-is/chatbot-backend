import inspect
import json
import logging
from inspect import isawaitable
from typing import Any, Callable, Iterable, Optional, TypeAlias, Union, cast

import openai
from openai import NotGiven
from openai.types.responses import (
    ComputerToolParam,
    FileSearchToolParam,
    FunctionToolParam,
    WebSearchToolParam,
)
from openai.types.responses.response_input_param import ResponseInputItemParam
from pydantic import create_model

from backend.config import AppConfig
from backend.types import FunctionCallOutput, FunctionCallRequest, MessageList, TextMessage, ToolBinding

ToolParam: TypeAlias = Union[FunctionToolParam, FileSearchToolParam, ComputerToolParam, WebSearchToolParam]
MessageParam: TypeAlias = ResponseInputItemParam

logger = logging.getLogger(__name__)


class OpenAITooledChat:
    def __init__(self, config: AppConfig, tools: dict[str, ToolBinding]):
        self.tools = tools
        openai.api_key = config.OPENAI_API_KEY

    async def create_response(self, messages: MessageList) -> TextMessage:
        """
        Wraps the openai.responses.create call, handles function calls, and sends the result back to OpenAI.
        """
        response = openai.responses.create(
            model="gpt-4o",
            input=[cast(MessageParam, m.model_dump()) for m in messages],
            tools=cast(Iterable[ToolParam] | NotGiven, self.tool_definitions),
        )

        performed_function_calls = False

        for response_type, output in self.yield_responses(response):
            if response_type == "function_call":
                tool_call = output
                function_call_output = await self.handle_function_call(tool_call)
                if function_call_output:
                    messages.append(
                        FunctionCallRequest(
                            type="function_call",
                            name=tool_call.name,
                            arguments=tool_call.arguments,
                            call_id=tool_call.call_id,
                        )
                    )
                    messages.append(function_call_output)
                    print("function call response:", function_call_output)
                    performed_function_calls = True

        if performed_function_calls:
            # Recursive call to allow OpenAI to respond with the tool call responses
            return await self.create_response(messages)

        if len(response.output) == 1:
            output = response.output[0]
            if output.type == "message" and output.content[0].type == "output_text":
                return TextMessage(
                    role="assistant",
                    content=output.content[0].text,
                )

        logger.error(
            f"Unsupported response from OpenAI -- expected single message, got {len(response.output)} items",
            extra={"response": response},
        )
        return TextMessage(role="assistant", content="error, unexpected response type from LLM")

    async def handle_function_call(self, tool_call: FunctionCallRequest) -> Optional[FunctionCallOutput]:
        if tool_call.name in self.tools:
            args = json.loads(tool_call.arguments)
            # if the callable is an async function, await it, otherwise call it:
            result = self.tools[tool_call.name]["ref"](**args)
            if isawaitable(result):
                result = await result

            # Create a new object to add to input
            return FunctionCallOutput(
                type="function_call_output",
                call_id=tool_call.call_id,
                output=json.dumps(result),
            )
        else:
            logger.error(f"No tool found for function call: {tool_call.name}", extra={"tool_call": tool_call})
            return None

    @classmethod
    def yield_responses(cls, response: Any) -> Iterable[tuple[str, Any]]:
        for output in response.output:
            if output.type == "function_call":
                yield "function_call", output
            elif output.type == "message":
                yield "message", output
            else:
                logger.error(
                    f"Unsupported response from OpenAI -- expected message or function_call, got {output.type}",
                    extra={"output": output},
                )

    @property
    def tool_definitions(self) -> Iterable[FunctionToolParam]:
        return [FunctionToolParam(**tool["schema"], strict=True) for tool in self.tools.values()]


def create_toolbinding(method: Callable, name: Optional[str] = None) -> ToolBinding:
    """
    Create a ToolBinding object for a given method and name.
    If no name is provided, the method's name will be used.
    """
    if name is None:
        if method.__name__ is None:
            raise ValueError("Can't determine a tool name from the given method, consider providing one")
        name = method.__name__

    signature = inspect.signature(method)

    # Dynamically create a Pydantic model for the method's parameters
    fields: dict[str, tuple[str, Any]] = {
        param_name: (param.annotation, param.default if param.default is not inspect.Parameter.empty else ...)
        for param_name, param in signature.parameters.items()
        if param_name != "self" and param.annotation is not inspect.Parameter.empty
    }

    # Generate JSON Schema for the parameters
    parameter_schema = create_model(name + "Parameters", **fields).model_json_schema()  # type: ignore[call-overload]

    # Remove 'default' from all properties (OpenAI rejects default values in the schema)
    for prop in parameter_schema["properties"].values():
        prop.pop("default", None)

    # OpenAI demands all schemas have additionalProperties=false and all parameters are required..
    parameter_schema["additionalProperties"] = False
    parameter_schema["required"] = list([str(field) for field in fields.keys()])

    return {
        "ref": method,
        "schema": {
            "type": "function",
            "name": name,
            "description": (method.__doc__ or "").strip(),
            "parameters": parameter_schema,
        },
    }
