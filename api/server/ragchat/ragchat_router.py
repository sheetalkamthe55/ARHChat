from fastapi import APIRouter, Request
from pydantic import BaseModel
from api.server.ragchat.ragchat_service import RagChatService
from starlette.responses import StreamingResponse
from typing import Union
from collections.abc import Iterator

class ChatCompletion(BaseModel):
    response: str
    sources: Union[list, None]

ragchat_router = APIRouter(prefix="/v1")

class RAGChatBody(BaseModel):
    message: str
    stream: bool = False
    session_id: str
    user_id: str

def to_openai_sse_stream(
    response_generator: Iterator[dict],
) -> Iterator[dict]:
    for response in response_generator:
            yield f"data: {response}\n\n"

@ragchat_router.post("/arahchat", response_model=None)
async def arahchat(request: Request, body: RAGChatBody) -> Union[ChatCompletion, StreamingResponse]:
    service = request.state.injector.get(RagChatService)
    if body.stream:
        completion_gen = service.stream(body.message, body.session_id, body.user_id)
        return StreamingResponse(
            to_openai_sse_stream(
                completion_gen.response
            ),
            media_type="text/event-stream",
        )
    else:
        chatcompletion = service.chat(body.message, body.session_id, body.user_id)
        return chatcompletion
    
@ragchat_router.get("/get_aggregated_history_per_user/{user_id}")
async def get_aggregated_history_per_user(request: Request, user_id: str):
    service = request.state.injector.get(RagChatService)
    history = service.get_aggregated_history_per_user(user_id)
    return history

@ragchat_router.delete("/delete_session_history/{session_id}/{user_id}")
async def delete_session_history(request: Request, session_id: str, user_id: str):
    try:
        service = request.state.injector.get(RagChatService)
        service.delete_session_history(session_id, user_id)
        return True
    except Exception as e:
        return str(e)
