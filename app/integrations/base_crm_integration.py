from abc import ABC, abstractmethod
from typing import List

class BaseLeadConnector(ABC):
    
    @abstractmethod
    def get_contact_info(self, contact_id: str) -> LCContactInfo:
        pass

    @abstractmethod
    def get_conversation(self, conversation_id: str):
        pass

    @abstractmethod
    def search_conversations(self, location_id: str, contact_id: str):
        pass

    @abstractmethod
    def get_conversation_id(self, location_id: str, contact_id: str):
        pass

    @abstractmethod
    def get_all_messages(
        self, conversation_id: str, limit: int = 50
    ) -> List[LCMessage]:
        pass

    @abstractmethod
    def send_message(self, contact_id: str, message: str, message_channel: str):
        pass

    @abstractmethod
    def delete_conversation(self, conversation_id: str):
        pass
