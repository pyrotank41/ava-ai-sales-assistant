import os
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from loguru import logger

def get_embedding_model():
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    logger.info(f"{api_key} {azure_endpoint}")

    return AzureOpenAIEmbedding(
        model="text-embedding-ada-002",
        deployment_name="text-embedding-ada-002",
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version="2024-02-01",
    )

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    model = get_embedding_model()
    logger.info(model.get_text_embedding("Hello, world!"))
