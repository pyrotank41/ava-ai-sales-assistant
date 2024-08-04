import os
import timeit
from typing import List, Optional
import json

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.llms.llm import LLM
from dotenv import load_dotenv
from loguru import logger
from pydantic import BaseModel
from ava.llm.llama_index_llms import get_anthropic_client, get_azure_openai_client
from ava.retriever.base_retriever import BaseRetriever
from ava.retriever.obj_handelling_retriever import ObjectionHandelingRetriever

azure_llm = get_azure_openai_client()


def get_system_message_template(file: str = "prompt/main_v1.txt"):
    with open(file, "r", encoding="utf-8") as f:
        system_message = f.read()
        if system_message == "":
            logger.error("Prompt file is empty")
            exit(1)
    return system_message

def str_to_bool(string_value:str):
    if string_value.lower() in ["true", "1", "t", "yes", "y"]:
        return True
    elif string_value.lower() in ["false", "0", "f", "no", "n"]:
        return False
    else:
        raise ValueError(f"Cannot convert {string_value} to boolean")

def is_message_an_objection(
        messages: List[ChatMessage],
        llm:LLM
    ) -> bool:

    if not isinstance(llm, LLM):
        logger.error(f"llm must be an instance of LLM, got {type(llm)}")
        raise ValueError("llm must be an instance of LLM")

    if not isinstance(messages, list):
        logger.error(f"messages must be a list of ChatMessage, got {type(messages)}")
        raise ValueError("messages must be a list of ChatMessage")

    if not all(isinstance(message, ChatMessage) for message in messages):
        logger.error("messages must be a list of ChatMessage")
        raise ValueError("messages must be a list of ChatMessage")

    messages_for_obj_check = [
            ChatMessage(
                role="system",
                content="is the following message an objection?, respond with `True` or `False`",
            )
        ]

    # get the last 3 messages from the messages
    messages_for_obj_check += messages[-min(3, len(messages)) :]

    obj_resp = llm.chat(messages_for_obj_check)

    obj_resp_content = str(obj_resp.message.content).lower().strip()
    logger.debug(f"obj resp content: {obj_resp_content}")

    # validate that the response is one of two values, 'true' or 'flase'
    if obj_resp_content not in ["true", "false"]:
        logger.error(f"obj_resp must be either 'True' or 'False', got {obj_resp.message.content}")
        raise ValueError("obj_resp must be either 'True' or 'False'")
    resp = str_to_bool(obj_resp.message.content)
    logger.info(f"Is message an objection: {resp}")
    return resp

def add_obj_handelling_examples_to_system_messsage(
        retriever: BaseRetriever,
        system_message: str, 
        user_message: ChatMessage
    ) -> ChatMessage:
    
    # get objection handelling response
    objection_handelling_resp = retriever.retrieve(
        user_message.content
    )
    # postprecessing nodes
    from llama_index.core.postprocessor import SimilarityPostprocessor
    processors = [
        SimilarityPostprocessor(similarity_cutoff=0.5),
    ]

    filtered_nodes = []
    for node in objection_handelling_resp:
        logger.debug(node)

    for processor in processors:
        logger.debug(f"Postprocessing with {processor.__class__.__name__}")
        filtered_nodes = processor.postprocess_nodes(objection_handelling_resp, query_str=user_message.content)
        logger.debug(f"Postprocessing dropped {len(objection_handelling_resp) - len(filtered_nodes)} nodes")

    if len(filtered_nodes) > 0:
        template = "I found these objections related to the query:\n{objections}"
        obj_str = ""
        for i, obj in enumerate(objection_handelling_resp):
            obj_str += (
                f"Objection {i+1}: {obj.text}\nRebuttal:{obj.metadata['rebuttal']}\n\n"
            )

        logger.debug(template.format(objections=obj_str))
        system_message = "\n" + template.format(objections=obj_str)
        
    return system_message

class Ava:
    def __init__(self, system_message: Optional[str]=None):
        self.llm:LLM = get_azure_openai_client()

        self.system_message = system_message if system_message is not None else get_system_message_template()
        logger.debug(f"System message: {self.system_message}")
        self.objection_handelling_retriver = ObjectionHandelingRetriever(
            similarity_top_k=2
        )

    def _get_chat_response(self, messages: List[ChatMessage]) -> ChatResponse:
        return self.llm.chat(messages)

    def _validate_chat_params(self, user_message: ChatMessage, message_history: List[ChatMessage]):
        if not isinstance(user_message, ChatMessage):
            logger.error("user_message must be an instance of ChatMessage")
            raise ValueError("user_message must be an instance of ChatMessage")

        if not isinstance(message_history, list):
            logger.error(f"message_history must be a list of ChatMessage, got {type(message_history)}")
            raise ValueError("message_history must be a list of ChatMessage")

        if not all(isinstance(message, ChatMessage) for message in message_history):
            logger.error("message_history must be a list of ChatMessage")
            raise ValueError("message_history must be a list of ChatMessage")

    def chat(
        self,
        user_message: ChatMessage, 
        message_history: List[ChatMessage] = [],
        system_message: Optional[str] = None
    ) -> ChatResponse:

        # validation
        self._validate_chat_params(user_message, message_history)

        # main logic -------------
        logger.info(f"User message: {user_message.content}")

        system_message = system_message if system_message is not None else self.system_message

        ## check if the user message is a objection.
        all_messages = message_history + [user_message]
        if is_message_an_objection(messages=all_messages, llm=self.llm):
            system_message = add_obj_handelling_examples_to_system_messsage(
                    self.objection_handelling_retriver,
                    system_message,
                    user_message
                )

        messages = [ChatMessage(role="system", content=system_message)] + message_history + [user_message]
        logger.debug(f"All messages: {json.dumps([message.dict() for message in messages], indent=4)}")

        chat_resp = self.llm.chat(messages)
        logger.info(f"AVA response: {chat_resp.message.content}")

        # validation
        if not isinstance(chat_resp, ChatResponse):
            logger.error(f"chat_resp must be an instance of ChatMessage, got {type(chat_resp)}")
            raise ValueError("chat_resp must be an instance of ChatMessage")

        return chat_resp

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
