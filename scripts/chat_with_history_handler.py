import gc
import sys
sys.path.append('~/Project/ARHChat/')
from dbutils.MongoDBChatMessageHistory import MongoDBChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    ConfigurableFieldSpec,
    RunnablePassthrough,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from qdrant_client import QdrantClient
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant

parse_output = StrOutputParser()
retriever_output = None
model = None

class MessageHistoryHandler:
    def __init__(self, mongodb_uri, db_name, vector_db_url, vector_db_apikey, vector_db_collection_name, inference_server_url, embedding_model_name):
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.vector_db_url = vector_db_url
        self.vector_db_apikey = vector_db_apikey
        self.vector_db_collection_name = vector_db_collection_name
        self.inference_server_url = inference_server_url
        self.embedding_model_name = embedding_model_name
    
    def instantiate_llm(self):
        try:
            inference_server_url = self.inference_server_url
            kwargs = {
                k: v
                for k, v in [
                    ("model", "no-llm"),
                    ("openai_api_key", "no-key"),
                    ("openai_api_base", inference_server_url),
                    ("temperature", 0),
                    ("streaming", True)
                    # ("max_tokens", 100)
                ]
                if v is not None
            }
            llm = ChatOpenAI(**kwargs)
            return llm
        except Exception as e:
            print(
                f"failed to instantiate the LLM model, please check the inference server URL and the model path: {e}")

    def initialize_retriever(self):
        try:
            client = QdrantClient(url=self.vector_db_url, api_key=self.vector_db_apikey)
            embed_model= HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            qdrant = Qdrant(client=client, collection_name=self.vector_db_collection_name, embeddings=embed_model)
            retriever = qdrant.as_retriever()
            return retriever
        except Exception as e:
            print(
                f"failed to instantiate the retriever, please check the Qdrant server URL and the model path: {e}")

    def get_session_history(self, session_id: str,user_id: str) -> MongoDBChatMessageHistory:
            try:
                return MongoDBChatMessageHistory(self.mongodb_uri, session_id,
                                                  user_id, database_name=self.db_name, collection_name="chat_history")
            except Exception as e:
                print(f"failed to get the session history, please check the MongoDB server URL and the model path: {e}")
    
    def intialize_question_chain(self):
        try:
            global model
            question_system_prompt = """
            Given a chat history and a follow-up question, rephrase the follow-up question to be a standalone question. \
            Do NOT answer the question, just reformulate it if needed, otherwise return it as is. \
            Only return the final standalone question. \
            """
            rephrase_question_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", question_system_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{question}"),
                ]
            )
            model = self.instantiate_llm()
            question_chain = rephrase_question_prompt | model  | parse_output
            return question_chain
        except Exception as e:
            print(
                f"failed to initialize the question chain, please check the LLM model and the model path: {e}"
            )
    
    def initialize_retriever_chain(self):
        try:
            retriever_chain = RunnablePassthrough.assign(context=self.intialize_question_chain() | self.initialize_retriever() | (lambda docs: {
                'content': "\n\n".join([d.page_content for d in docs]),
                'sources': [d.metadata['source'] for d in docs]
            }))
            return retriever_chain
        except Exception as e:
            print(
                f"failed to initialize the retriever chain, please check the retriever and the model path: {e}")
    
    
    def with_message_history(self):
            try:
                rag_system_prompt = """Answer the question based only on the following context: \{context}"""
                rag_prompt = ChatPromptTemplate.from_messages(
                [
                ("system", rag_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
                ])
                
                rag_chain = (self.initialize_retriever_chain() | rag_prompt | model | parse_output)
                with_message_history = RunnableWithMessageHistory(rag_chain,
                                                                  self.get_session_history,
                                                                  input_messages_key="question",
                                                                  history_messages_key="chat_history",
                                                                  history_factory_config=[
                                                                    ConfigurableFieldSpec(
                                                                        id="user_id",
                                                                        annotation=str,
                                                                        name="User ID",
                                                                        description="Unique identifier for the user.",
                                                                        default="",
                                                                        is_shared=True,
                                                                    ),
                                                                    ConfigurableFieldSpec(
                                                                        id="session_id",
                                                                        annotation=str,
                                                                        name="Session ID",
                                                                        description="Unique identifier for the conversation.",
                                                                        default="",
                                                                        is_shared=True,
                                                                    )])
                return with_message_history
            except Exception as e:
                print(
                    f"failed to initialize the retriever chain, please check the retriever and the model path: {e}")
                