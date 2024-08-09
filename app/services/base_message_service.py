from typing import Protocol


class MessagingService(Protocol):
    def process_special_codes(self, message: str, conversation_id: str) -> bool:
        """
        Process special codes in the given message for the specified conversation.

        Args:
            message (str): The message containing special codes.
            conversation_id (str): The ID of the conversation.

        Returns:
            bool: True if the special codes were successfully processed, False otherwise.
        """
        ...

    def process_to_inbound_message(self, contact_id: str, conversation_id: str) -> None:
        """
        This method is responsible for generating a response to a given contact and conversation ID.

        Args:
            contact_id (str): The ID of the contact.
            conversation_id (str): The ID of the conversation.

        Returns:
            None
        """
        ...
