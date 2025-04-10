import json
from typing import Iterable, Union, cast, TypeAlias

import openai
from openai import NotGiven

from openai.types.responses import ComputerToolParam, WebSearchToolParam, FileSearchToolParam, FunctionToolParam
from openai.types.responses.response_input_param import ResponseInputItemParam

ToolParam: TypeAlias = Union[FunctionToolParam, FileSearchToolParam, ComputerToolParam, WebSearchToolParam]

MessageParam: TypeAlias = ResponseInputItemParam


from ..config import AppConfig
from ..types import MessageList, FunctionCallRequest, FunctionCallOutput, ToolBinding, TextMessage


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
            input=[cast(MessageParam, m.dict()) for m in messages],
            tools=cast(Iterable[ToolParam] | NotGiven, self.tool_definitions),
        )

        print("response.output=", response.output)
        # XXX: there seems to be only one output most of the time, need to read up on why this is an array
        last_output = response.output[0]

        if last_output.type == "function_call":
            tool_call = last_output
            if tool_call.name == "make_calculation":
                messages.append(
                    FunctionCallRequest(
                        type="function_call",
                        name=tool_call.name,
                        arguments=tool_call.arguments,
                        call_id=tool_call.call_id,
                    )
                )
                args = json.loads(tool_call.arguments)
                result = self.tools["make_calculation"]["ref"](**args)

                # Create a new object to add to input
                function_call_output = FunctionCallOutput(
                    type="function_call_output",
                    call_id=tool_call.call_id,
                    output=str(result),
                )

                # Send another openai.responses.create call with the function call output
                messages.append(function_call_output)
                return await self.create_response(messages)

        return TextMessage(
            role="assistant",
            content="" if last_output.type != "text" else last_output.content[0].text,
        )

    @property
    def tool_definitions(self) -> Iterable[FunctionToolParam]:
        return [FunctionToolParam(**tool["schema"], strict=True, type="function") for tool in self.tools.values()]
