import json
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


class Ava:
    def __init__(self):
        self.llm = get_azure_openai_client()
        self.system_message = get_system_message_template()
        self.objection_handelling_retriver = ObjectionHandelingRetriever(
            similarity_top_k=2
        )

    def _get_chat_response(self, messages: List[ChatMessage]) -> ChatResponse:
        return self.llm.chat(messages)

    def chat(
        self, user_message: ChatMessage, message_history: List[ChatMessage] = []
    ) -> ChatResponse:

        if isinstance(message_history, list) and  len(message_history) > 0:
            # check if message_history is a list of ChatMessage
            if not all(isinstance(message, ChatMessage) for message in message_history):
                logger.error("message_history must be a list of ChatMessage")
                raise ValueError("message_history must be a list of ChatMessage")

        # validate user_message
        if not isinstance(user_message, ChatMessage):
            logger.error("user_message must be an instance of ChatMessage")

        logger.info(f"User message: {user_message.content}")
        # get objection handelling response
        objection_handelling_resp = self.objection_handelling_retriver.retrieve(
            user_message.content
        )
        template = "I found these objections related to the query:\n{objections}"
        obj_str = ""
        for i, obj in enumerate(objection_handelling_resp):
            obj_str += (
                f"Objection {i}: {obj.text}\nRebuttal:{obj.metadata['rebuttal']}\n\n"
            )

        logger.debug(template.format(objections=obj_str))
        system_message = (
            self.system_message + "\n" + template.format(objections=obj_str)
        )
        messages = [ChatMessage(role="system", content=system_message)]
        if message_history:
            messages += message_history
        messages.append(user_message)

        resp = self._get_chat_response(messages=messages)
        logger.info(f"AVA response: {resp.message.content}")
        return resp


if __name__ == "__main__":
    load_dotenv(".env")
    ava = Ava()
    chat_history = []
    while True:
        user_message = input("You: ")
        start_time = timeit.default_timer()
        user_message = ChatMessage(role="user", content=user_message)
        resp = ava.chat(user_message, chat_history)

        stop_time = timeit.default_timer()
        logger.info(f"Time taken: {stop_time - start_time}")
        logger.info(resp)

        chat_history.append(user_message)
        chat_history.append(resp.message)
