import os
import time

from llama_index.core.base.llms.types import ChatMessage
from dotenv import load_dotenv
from loguru import logger
from ava.utils.llms import get_anthropic_client, get_azure_openai_client

load_dotenv(".env")

azure_llm = get_azure_openai_client()
with open("prompt/main_v1.txt", "r") as f:
    system_message = f.read()
    if system_message == "":
        logger.error("Prompt file is empty")
        exit(1)
     
start_time = time.time()
resp = azure_llm.chat(
    [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content="How you doing?"),
    ]
)
stop_time = time.time()
logger.info(f"Time taken: {stop_time - start_time}")
logger.info(resp)

start_time = time.time()
anthropic_llm = get_anthropic_client()
resp = anthropic_llm.chat(
    [
        ChatMessage(role="system", content=system_message),
        ChatMessage(role="user", content="How you doing?"),
    ]
)
stop_time = time.time()
logger.info(f"Time taken: {stop_time - start_time}")
logger.info(resp)
