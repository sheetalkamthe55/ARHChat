import logging

from injector import inject, singleton
from api.settings.settings import Settings
from langchain.embeddings.huggingface import HuggingFaceEmbeddings


logger = logging.getLogger(__name__)

@singleton
class EmbedModelComponent:
    embed_model: HuggingFaceEmbeddings

    @inject
    def __init__(self, settings: Settings) -> None:
        logger.info("Initializing EmbedModelComponent")
        self.embed_model = HuggingFaceEmbeddings(
            model_name=settings.embeddings.embed_name
        )
        