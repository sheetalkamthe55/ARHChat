from injector import inject, singleton

from api.settings.settings import Settings
from .MongoDBChatMessageHistory import MongoDBChatMessageHistory

import logging

@singleton
class MongoChatHistoryComponent:

    @inject
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def get_session_history(self, session_id: str,user_id: str) -> MongoDBChatMessageHistory:
        try:
            return MongoDBChatMessageHistory(self.settings.mongodb.url, session_id,
                                              user_id, database_name=self.settings.mongodb.db_name, collection_name=self.settings.mongodb.history_collectionname)
        except Exception as e:
            logging.error(f"Error getting session history: {e}")

