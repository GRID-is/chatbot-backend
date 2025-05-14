from simple_query_api import AsyncGrid
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .config import get_config
from .grid import ProjectXRevenueModel
from .llm.openai import OpenAITooledChat, create_toolbinding
from .types import ChatRequest

config = get_config()

grid_client = AsyncGrid(api_key=config.GRID_API_KEY)
project_x = ProjectXRevenueModel(grid_client)

openai_chat = OpenAITooledChat(
    config,
    tools=dict(
        get_model_defaults=create_toolbinding(project_x.get_model_defaults),
        forecast_revenue=create_toolbinding(project_x.forecast_revenue, name="forecast_revenue"),
    ),
)


async def chat(request: Request):
    try:
        payload = await request.json()
        chat_request = ChatRequest(**payload)
    except Exception as e:
        return JSONResponse({"error": "Invalid request payload", "details": str(e)}, status_code=400)

    messages = chat_request.messages

    response = await openai_chat.create_response(messages)

    return JSONResponse({"reply": response.content, "role": response.role})


app = Starlette(
    debug=True,
    routes=[
        Route("/chat", chat, methods=["POST"]),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])],
)
