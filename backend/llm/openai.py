import json
from typing import Iterable

import openai
from openai.types.beta import FunctionToolParam

from ..config import AppConfig
from ..types import MessageList, Message, FunctionCallRequest, FunctionCallOutput, ToolBinding, ToolDefinition


class OpenAITooledChat:
    def __init__(self, config: AppConfig, tools: dict[str, ToolBinding]):
        self.tools = tools
        openai.api_key = config.OPENAI_API_KEY

    async def create_response(self, messages: MessageList) -> Message:
        """
        Wraps the openai.responses.create call, handles function calls, and sends the result back to OpenAI.
        """
        response = openai.responses.create(model="gpt-4o", input=[m.dict() for m in messages], tools=self.tool_definitions)

        print("response.output=", response.output)

        last_output = response.output[0]
        # XXX: there seems to be only one output most of the time, need to read up on why this is an array
        print("len of output=", len(response.output))

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
                result = make_calculation(**args)

                # Create a new object to add to input
                function_call_output = FunctionCallOutput(
                    type="function_call_output",
                    call_id=tool_call.call_id,
                    output=str(result),
                )

                # Send another openai.responses.create call with the function call output
                messages.append(function_call_output)
                return await self.create_response(messages)

        return last_output

    @property
    def tool_definitions(self) -> Iterable[FunctionToolParam]:
        return [
            FunctionToolParam(**tool["schema"]) for tool in self.tools.values()
        ]