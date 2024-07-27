import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from injector import Injector
from api.server.ragchat.ragchat_router import ragchat_router
from api.settings.settings import Settings

logger = logging.getLogger(__name__)

def create_app(injector: Injector) -> FastAPI:

    async def bind_injector_to_request(request: Request) -> None:
        request.state.injector = injector
    
    app = FastAPI( title="ARAH Chat API", description="API for the ARAH Chat",dependencies=[Depends(bind_injector_to_request)])
    app.include_router(ragchat_router)

    ragsettings = injector.get(Settings)

    if ragsettings.server.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=ragsettings.server.cors.allow_origins,
            allow_origin_regex=ragsettings.server.cors.allow_origin_regex,
            allow_credentials=ragsettings.server.cors.allow_credentials,
            allow_methods=ragsettings.server.cors.allow_methods,
            allow_headers=ragsettings.server.cors.allow_headers,
        )

    return app