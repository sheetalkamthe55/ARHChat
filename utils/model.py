import streamlit as st
from streamlit_server_state import server_state, no_rerun
import gc
from utils.user import update_server_state, clear_models
import sys
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

MONGODB_URI = server_state["mongodbURI"]
DB_NAME = server_state["mongo_db_name"]
parse_output = StrOutputParser()
retriever_output = None

# Define a function to capture the output of retriever_chain
def capture_output(output):
    st.session_state[f'{st.session_state["user_name"]} retriever_output'] = output
    return output

def initialize_llm():
    "initialize the LLM model"
    try:
        with st.spinner("Loading LLM..."):
            update_server_state(
                "llm_name",
                instantiate_llm(),
            )
    except:
        st.error("Not enough memory to load this model.")

def instantiate_llm():
    try:
        inference_server_url = server_state["inference_server_url"]
        kwargs = {
            k: v
            for k, v in [
                ("model", "no-llm"),
                ("openai_api_key", "no-key"),
                ("openai_api_base", inference_server_url),
                ("temperature", 0),
                ("streaming", True)
            ]
            if v is not None
        }
        llm = ChatOpenAI(**kwargs)
        return llm
    except Exception as e:
        print(
            f"failed to instantiate the LLM model, please check the inference server URL and the model path: {e}")

def initialize_retriever():
    try:
        client = QdrantClient(url=server_state["qdrant_server_url"],api_key=server_state["qdrant_API_key"])
        # https://python.langchain.com/v0.2/docs/integrations/text_embedding/huggingfacehub/
        embed_model= HuggingFaceEmbeddings(model_name=server_state["embeddingmodelname"])
        qdrant = Qdrant(client=client, collection_name=server_state["vector_collectionname"], embeddings=embed_model)
        retriever = qdrant.as_retriever(search_type="mmr",search_kwargs={'k': 3, 'lambda_mult': 0.25})
        return retriever
    except Exception as e:
        st.write(
            f"failed to instantiate the retriever, please check the Qdrant server URL and the model path: {e}")

def get_session_history(session_id: str,user_id: str) -> MongoDBChatMessageHistory:
        try:
            return MongoDBChatMessageHistory(MONGODB_URI, session_id,
                                              user_id, database_name=DB_NAME, collection_name=server_state["history_collectionname"])
        except Exception as e:
            st.write(f"failed to get the session history, please check the MongoDB server URL and the model path: {e}")

def intialize_question_chain():
    try:
        standalone_system_prompt = """
        Given a chat history and a follow-up question, rephrase the follow-up question to be a standalone question. \
        Do NOT answer the question, just reformulate it if needed, otherwise return it as is. \
        Only return the final standalone question. \
        """
        standalone_question_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", standalone_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        question_chain = standalone_question_prompt | server_state["llm_name"]  | parse_output
        return question_chain
    except Exception as e:
        st.write(
            f"failed to initialize the question chain, please check the LLM model and the model path: {e}"
        )

def initialize_retriever_chain():
    try:
        retriever_chain = RunnablePassthrough.assign(context=intialize_question_chain() | initialize_retriever() | (lambda docs: {
            'content': "\n\n".join([d.page_content for d in docs]),
            'sources': [str(d.metadata.get('page', '')) + ' ' + str(d.metadata.get('source', '')) for d in docs]
        }))
        return retriever_chain
    except Exception as e:
        st.write(
            f"failed to initialize the retriever chain, please check the retriever and the model path: {e}")

def initialize_rag_chain():
        
    if (
        f'model_{st.session_state["db_name"]}' not in server_state
    ):
        clear_models()

        if "message_box" in st.session_state:
            st.session_state["message_box"].empty()
    
        old_stdout = sys.stdout

        with st.spinner("Initializing..."):
            def model_initialization():
                initialize_llm()
                rag_system_prompt = """You are a chatbot specialized in answering questions in context concisely. If you cannot find the answer to a query in the provided context, say you cannot answer or provide related information that is in the context. Do not make up answers that are not contained in the context.: \Context: {context}"""
                rag_prompt = ChatPromptTemplate.from_messages(
                [
                ("system", rag_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
                ])
                
                rag_chain = (initialize_retriever_chain() | capture_output | rag_prompt | server_state["llm_name"] | parse_output)
                with_message_history = RunnableWithMessageHistory(rag_chain,
                                                                  get_session_history,
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
                update_server_state(f'model_{st.session_state["db_name"]}', with_message_history)
                del with_message_history
                gc.collect()
    
        model_initialization()

        try:
            sys.stdout = sys.stdout.clear()
            sys.stdout = old_stdout
        except:
            pass

        st.info("Model successfully initialized!")

    