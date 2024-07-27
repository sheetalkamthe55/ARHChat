import logging
from collections.abc import Callable
from typing import Any
from langchain_openai import ChatOpenAI

from api.settings.settings import Settings
from injector import inject, singleton

logger = logging.getLogger(__name__)

@singleton
class LLModelComponent:
    llm: ChatOpenAI

    @inject
    def __init__(self, settings: Settings) -> None:
        logger.info("Initializing LLModelComponent")
        kwargs = {
            k: v
            for k, v in [
                ("model",settings.llm.llm_name),
                ("openai_api_key", settings.llm.api_key),
                ("openai_api_base", settings.llm.inference_server_url),
                ("temperature", 0),
                ("streaming", settings.llm.stream)
            ]
            if v is not None
        }
        self.llm = ChatOpenAI(**kwargs)
        

