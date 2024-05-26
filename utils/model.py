import streamlit as st
from streamlit_server_state import server_state, no_rerun
import gc
from utils.user import update_server_state, clear_models
from utils.ui import populate_chat
import sys
import urllib

from langchain.memory import MongoDBChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from qdrant_client import QdrantClient
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant


MONGODB_URI = "mongodb+srv://sheetal:" + urllib.parse.quote("Sheetal@123") + "@ragcluster.uxamzan.mongodb.net/?retryWrites=true&w=majority&appName=RAGCluster"
DB_NAME = "ARH_chatbot"
parse_output = StrOutputParser()

def initialize_llm():
    "initialize the LLM model"
    # # clear out existing models
    # if "clear_llms" in st.session_state:
    #     with no_rerun:
    #         if st.session_state["clear_llms"]:
    #             for llm_title in st.session_state["llm_dict"].loc[:, "name"].values:
    #                 if llm_title in server_state:
    #                     del server_state[llm_title]
    #             gc.collect()

    if f'{st.session_state["user_name"]}_selected_llm' in server_state:
         llm_name = server_state[f'{st.session_state["user_name"]}_selected_llm']
    else:
         llm_name = ""
    st.write("last_used",server_state["last_used"])
    # if llm_name not in server_state:
    try:
        with st.spinner("Loading LLM..."):
            update_server_state(
                "llm_name",
                instantiate_llm(),
            )
        st.write("llm_name",server_state["llm_name"])
    except:
        st.error("Not enough memory to load this model.")

def instantiate_llm():
    try:
        inference_server_url = "http://129.69.217.24:8009/v1"
        kwargs = {
            k: v
            for k, v in [
                ("model", "/tmp/llama_index/models/llama-13b.Q5_K_M.gguf"),
                ("openai_api_key", "no-key"),
                ("openai_api_base", inference_server_url),
                ("temperature", 0),
            ]
            if v is not None
        }
        llm = ChatOpenAI(**kwargs)
        return llm
    except:
        print(
            "failed to instantiate the LLM model, please check the inference server URL and the model path"
        )

def initialize_retriever():
    client = QdrantClient(host="129.69.217.24", port=6333)
    embed_model= HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
    qdrant = Qdrant(client=client, collection_name="ARH_Recommendations", embeddings=embed_model)
    retriever = qdrant.as_retriever()
    return retriever
    
def get_session_history(session_id: str) -> MongoDBChatMessageHistory:
        return MongoDBChatMessageHistory(MONGODB_URI, session_id, database_name=DB_NAME, collection_name="chat_history")

def intialize_question_chain():
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

def initialize_retriever_chain():
    retriever_chain = RunnablePassthrough.assign(context=intialize_question_chain() | initialize_retriever() | (lambda docs: "\n\n".join([d.page_content for d in docs])))
    return retriever_chain

def initialize_rag_chain():
        
    if (
        f'model_{st.session_state["db_name"]}' not in server_state
    ):
        clear_models()
    # hid messages so you can see the initializer
        if "message_box" in st.session_state:
            st.session_state["message_box"].empty()
    
    # intialize progress bar in case necessary
        old_stdout = sys.stdout
        # sys.stdout = Logger(st.progress(0), st.empty())

    
    with st.spinner("Initializing..."):
        def model_initialization():
            initialize_llm()
            rag_system_prompt = """Answer the question based only on the following context: \{context}"""
            rag_prompt = ChatPromptTemplate.from_messages(
            [
            ("system", rag_system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{question}"),
            ])
            rag_chain = (initialize_retriever_chain() | rag_prompt | server_state["llm_name"] | parse_output)
            with_message_history = RunnableWithMessageHistory(rag_chain,get_session_history,input_messages_key="question",history_messages_key="chat_history")
            st.write(with_message_history.invoke({"question": "Define microservices"}, {"configurable": {"session_id": st.session_state["user_name"]}}))
            update_server_state(f'model_{st.session_state["db_name"]}', with_message_history)
            del with_message_history
            gc.collect()

        model_initialization()

        
        # clear the progress bar
        try:
            sys.stdout = sys.stdout.clear()
            sys.stdout = old_stdout
        except:
            pass

        populate_chat()
        st.info("Model successfully initialized!")

    