import os
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.anthropic import Anthropic

def get_env_value(key: str) -> str:
    """
    Returns the value of the specified environment variable.

    Args:
        key (str): The name of the environment variable.

    Returns:
        str: The value of the environment variable.
    """
    value = os.getenv(key, None)
    if value is None:
        raise ValueError(f"Missing environment variable: {key}")
    return value

def get_azure_openai_client() -> AzureOpenAI:
    """
    Returns an instance of AzureOpenAI client.

    Returns:
        AzureOpenAI: An instance of AzureOpenAI client.
    """
    engine = get_env_value("AZURE_OPENAI_DEPLOYMENT_NAME")
    endpoint = get_env_value("AZURE_OPENAI_ENDPOINT")
    api_key = get_env_value("AZURE_OPENAI_API_KEY")
    
    if not engine or not endpoint or not api_key:
        raise TypeError("Missing environment variables for AzureOpenAI client.")
    
    return AzureOpenAI(
        engine=engine,
        model="gpt-4o",
        temperature=0.0,
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-02-01",
    )


def get_anthropic_client() -> Anthropic:
    """
    Returns an instance of the Anthropic client.

    The client is initialized with the specified model and API key.

    Returns:
        Anthropic: An instance of the Anthropic client.
    """
    return Anthropic(
        model="claude-3-5-sonnet-20240620",
        api_key=get_env_value("ANTHROPIC_API_KEY"),
    )
