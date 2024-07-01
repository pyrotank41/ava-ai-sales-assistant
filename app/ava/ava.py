import time
import timeit
from typing import List, Optional

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
from app.ava.llm.llama_index_llms import get_anthropic_client, get_azure_openai_client
from app.ava.retriever.obj_handelling_retriever import ObjectionHandelingRetriever

azure_llm = get_azure_openai_client()
def get_system_message_template(file: str = "prompt/main_v1.txt"):
    with open(file, "r", encoding="utf-8") as f:
        system_message = f.read()
        if system_message == "":
            logger.error("Prompt file is empty")
            exit(1)
    return system_message

class ChatHistory(BaseModel):
    messages: List[ChatMessage]


class Ava():
    def __init__(self):
        self.llm = get_azure_openai_client()
        self.system_message = get_system_message_template()
        self.objection_handelling_retriver = ObjectionHandelingRetriever(similarity_top_k=2)

    def _get_chat_response(self, messages: List[ChatMessage]) -> ChatResponse:
        return self.llm.chat(messages)

    def chat(
        self, user_message: str, message_history: Optional[ChatHistory] = None
    ) -> ChatResponse:

        # validate user_message
        if not user_message:
            logger.error("User message is empty")
            return {"error": "User message is empty"}
        # validate message_history
        if message_history:
            if not isinstance(message_history, ChatHistory):
                logger.error("message_history should be a ChatHistory")
                return {"error": "message_history should be a ChatHistory"}

        # get objection handelling response
        objection_handelling_resp = self.objection_handelling_retriver.retrieve(user_message)
        template = "I found these objections related to the query:\n{objections}"
        obj_str = ""
        for i, obj in enumerate(objection_handelling_resp):
            obj_str += f"Objection {i}: {obj.text}\nRebuttal:{obj.metadata['rebuttal']}\n\n"
            
        logger.debug(template.format(objections=obj_str))
        system_message = self.system_message + "\n" + template.format(objections=obj_str)
        messages = [ChatMessage(role="system", content=system_message)]
        if message_history:
            messages += message_history.messages
        messages.append(ChatMessage(role="user", content=user_message))

        resp = self._get_chat_response(messages=messages)
        return resp


if __name__ == "__main__":
    load_dotenv(".env")
    ava = Ava()
    while True:
        user_message = input("You: ")
        start_time = timeit.default_timer()
        resp = ava.chat(user_message)
        stop_time = timeit.default_timer()
        logger.info(f"Time taken: {stop_time - start_time}")
        logger.info(resp)
