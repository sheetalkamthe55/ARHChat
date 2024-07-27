import logging
import typing
from injector import inject, singleton

from qdrant_client import QdrantClient
from langchain_community.vectorstores import Qdrant
from api.settings.settings import Settings
from api.components.embedding.embedmodel_component import EmbedModelComponent


logger = logging.getLogger(__name__)

@singleton
class QdrantComponent:
    qdrant: Qdrant

    @inject
    def __init__(self, settings: Settings) -> None:
        logger.info("Initializing QdrantComponent")
        client = QdrantClient(url=settings.qdrant.url,api_key=settings.qdrant.api_key)
        self.qdrant = Qdrant(client=client, collection_name=settings.qdrant.vector_collectionname, embeddings=EmbedModelComponent(settings).embed_model)