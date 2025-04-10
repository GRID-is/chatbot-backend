from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from .types import ChatRequest

from .config import get_config
from .grid import GridAPI
from .llm.openai import OpenAITooledChat


config = get_config()
GRID = GridAPI()
openai_chat = OpenAITooledChat(config, tools=GRID.tools)


async def chat(request: Request):
    try:
        payload = await request.json()
        chat_request = ChatRequest(**payload)
    except Exception as e:
        return JSONResponse({"error": "Invalid request payload", "details": str(e)}, status_code=400)

    messages = chat_request.messages

    # Define the tool for collecting numbers

    response = await openai_chat.create_response(messages)

    return JSONResponse({"reply": response.content, "role": response.role})


app = Starlette(
    debug=True,
    routes=[
        Route("/chat", chat, methods=["POST"]),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])],
)
