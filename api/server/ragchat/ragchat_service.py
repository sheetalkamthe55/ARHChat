from injector import inject, singleton

from api.settings.settings import Settings
from api.components.qdrant.qdrant_component import QdrantComponent
from api.components.llm.llmodel_component import LLModelComponent
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    ConfigurableFieldSpec,
    RunnablePassthrough,
    RunnableParallel,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from api.components.mongochathistory.mongochathistory import MongoChatHistoryComponent
from typing import Generator,Union
from pydantic import BaseModel


class ChatCompletionGen(BaseModel):
    response: Generator[dict, None, None]

class ChatCompletion(BaseModel):
    response: str
    sources: Union[list, None]

@singleton
class RagChatService:

    @inject
    def __init__(self, settings: Settings, qdrant: QdrantComponent, llm: LLModelComponent, mongodb: MongoChatHistoryComponent ) -> None:
        self.settings = settings
        self.qdrant = qdrant.qdrant
        self.llm = llm.llm
        self.mongodb = mongodb
        self.sources = []

    def format_docs(self,docs):
            return {
            'content': "\n\n".join([d.page_content for d in docs]),
            'sources': [str(d.metadata.get('page', '')) + ' ' + str(d.metadata.get('source', '')) for d in docs]}
    
    def capture_output(self, output):
        self.sources = output['context']['sources']
        return output
    
    def _with_message_history(self) -> RunnableWithMessageHistory:
        question_system_prompt = self.settings.ui.question_system_prompt
        rephrase_question_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", question_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ]
        )
        parse_output = StrOutputParser()

        retriever = self.qdrant.as_retriever(search_type=self.settings.qdrant.search_type,search_kwargs={'k': self.settings.qdrant.similarity_top_k, 'lambda_mult': self.settings.qdrant.lambda_mult})

        question_chain = rephrase_question_prompt | self.llm | parse_output

        retriever_chain = question_chain | retriever

        rag_system_prompt = self.settings.ui.rag_system_prompt

        rag_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", rag_system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{question}"),
            ])
        
        # rag_chain = (retriever_chain | self.capture_output | rag_prompt | self.llm | parse_output)
        

        rag_chain_from_docs = RunnablePassthrough.assign(context=(lambda x: self.format_docs(x["context"]))) | rag_prompt | self.llm | parse_output
        extract_history = RunnableLambda(lambda x: x['chat_history'])
        extract_question = RunnableLambda(lambda x: x['question'])
        rag_chain_with_source = RunnableParallel({"context": retriever_chain, "chat_history": extract_history,"question": extract_question}).assign(answer=rag_chain_from_docs)

        with_message_history = RunnableWithMessageHistory(rag_chain_with_source,
                                                          self.mongodb.get_session_history,
                                                          input_messages_key="question",
                                                          history_messages_key="chat_history",
                                                          output_messages_key="answer",
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
                
    def chat(self,message:str,session_id:str,user_id:str) -> ChatCompletion:
        response = self._with_message_history().invoke({"question": message}, {"configurable": {"session_id": session_id, "user_id": user_id}})
        sources = self.format_docs(response['context'])
        chatcompletion = ChatCompletion(response=response['answer'], sources=sources['sources'])
        return chatcompletion
    
    def stream(self,message:str,session_id:str,user_id:str) -> ChatCompletionGen:
        streamresponse = self._with_message_history().stream({"question": message}, {"configurable": {"session_id": session_id, "user_id": user_id}})
        chatcompletiongen = ChatCompletionGen(response=streamresponse)
        return chatcompletiongen

    def get_aggregated_history_per_user(self, user_id: str):
        pipeline = [
            {
                '$match': {
                    'UserId': user_id 
                }
            },
            {
                '$group': {
                    '_id': '$SessionId',  
                    'user_id': {'$first': '$UserId'}, 
                    'count': {'$sum': 1},  
                    'History': {'$push': '$History'} 
                }
            },
            {
                '$sort': {'timestamp': -1}  # Sort (descending) by timestamp
            }
            ]
        history = self.mongodb.get_session_history("","").getformatedmessage(pipeline)
        return history
    
    def delete_session_history(self, session_id: str, user_id: str):
        try:
            return self.mongodb.get_session_history(session_id, user_id).clear()
        except Exception as e:
            return str(e)
        
    def getsettings(self):
        return self.settings
                                                        



