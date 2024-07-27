

from typing import Any, Literal

from pydantic import BaseModel, Field

from api.settings.settings_loader import load_settings_from_profile

class ARAHCorsSettings(BaseModel):
    enabled: bool = Field(
        description="Flag indicating if CORS headers are set or not.",
        default=False,
    )
    allow_credentials: bool = Field(
        description="Indicate that cookies should be supported for cross-origin requests",
        default=False,
    )
    allow_origins: list[str] = Field(
        description="A list of origins that should be permitted to make cross-origin requests.",
        default=[],
    )
    allow_origin_regex: list[str] = Field(
        description="A regex string to match against origins that should be permitted to make cross-origin requests.",
        default=None,
    )
    allow_methods: list[str] = Field(
        description="A list of HTTP methods that should be allowed for cross-origin requests.",
        default=[
            "GET",
        ],
    )
    allow_headers: list[str] = Field(
        description="A list of HTTP request headers that should be supported for cross-origin requests.",
        default=[],
    )

class ARAHAuthSettings(BaseModel):

    enabled: bool = Field(
        description="Flag indicating if authentication is enabled or not.",
        default=False,
    )
    secret: str = Field(
        description="The secret to be used for authentication. "
        "It can be any non-blank string. For HTTP basic authentication, "
        "this value should be the whole 'Authorization' header that is expected"
    )

class ARAHServerSettings(BaseModel):
    env_name: str = Field(
        description="Name of the environment (prod, staging, local...)"
    )
    host: str = Field(description="Host of ARAH FastAPI server, defaults to 0.0.0.0")
    port: int = Field(description="Port of ARAH FastAPI server, defaults to 8505")
    cors: ARAHCorsSettings = Field(
        description="CORS configuration", default=ARAHCorsSettings(enabled=False)
    )
    auth: ARAHAuthSettings = Field(
        description="Authentication configuration",
        default_factory=lambda: ARAHAuthSettings(enabled=False, secret="secret-key"),
    )

class ARAHLLMSettings(BaseModel):
    inference_server_url: str = Field(
        description="Llamacpp Inference Server URL",
        default="http://localhost:8009/v1",
    )
    llm_name: str = Field(
        description="Model name to use for inference",
        default="no-model",
    )
    api_key: str = Field(
        description="API key to use for inference",
        default="no-key",
    )
    stream: bool = Field(
        description="Flag indicating if the server should stream the response or not",
        default=False,
    )

class ARAHEmbeddingsSettings(BaseModel):
    embed_name: str = Field(
        description="Model name to use for embeddings",
        default="intfloat/e5-base-v2",
    )
    inference_server_url: str = Field(
        description="Embeddings Inference Server URL",
        default="http://localhost:8009/v1",
    )
    api_key: str = Field(
        description="API key to use for embeddings",
        default="no-key",
    )

class ARAHQdrantSettings(BaseModel):
    url: str = Field(
        description="Qdrant URL",
        default="http://localhost:6333",
    )
    api_key: str = Field(
        description="Qdrant API key",
        default="no-key",
    )
    vector_collectionname: str = Field(
        description="Qdrant Vector Collection Name",
        default="ARH_Tool",
    )
    search_type: Literal["mmr"] = Field(
        description="Qdrant Search Type",
        default="mmr",
    )
    lambda_mult: float = Field(
        description="Qdrant Lambda Multiplier",
        default=0.25,
    )
    similarity_top_k: int = Field(
        description="Qdrant Similarity Top K",
        default=3,
    )

class ARAHMongodbSettings(BaseModel):
    url: str = Field(
        description="MongoDB URL",
        default="mongodb://localhost:27017",
    )
    db_name: str = Field(
        description="MongoDB Database Name",
        default="ARH_chatbot",
    )
    history_collectionname: str = Field(
        description="MongoDB Collection Name",
        default="chat_history",
    )

class ARAHUISettings(BaseModel):
    enabled: bool = Field(
        description="Flag indicating if UI is enabled or not.",
        default=True,
    )
    app_title: str = Field(
        description="App Title",
        default="Architecture Refactoring AI Helper"
    )
    question_system_prompt: str = Field(
        description="Question System Prompt",
        default="Please ask me a question."
    )
    rag_system_prompt: str = Field(
        description="Rag System Prompt",
        default="Please ask me a question."
    )

class Settings(BaseModel):
    server: ARAHServerSettings
    llm: ARAHLLMSettings
    embeddings: ARAHEmbeddingsSettings
    qdrant: ARAHQdrantSettings
    mongodb: ARAHMongodbSettings
    ui: ARAHUISettings

unsafe_settings = load_settings_from_profile()
unsafe_typed_settings = Settings(**unsafe_settings)

def settings() -> Settings:
    from api.di import global_injector
    return global_injector.get(Settings)





