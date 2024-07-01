import os
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.anthropic import Anthropic

def get_azure_openai_client() -> AzureOpenAI:
    """
    Returns an instance of AzureOpenAI client.

    Returns:
        AzureOpenAI: An instance of AzureOpenAI client.
    """
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if not all([deployment_name, endpoint, api_key]):
        raise TypeError(
            "Missing required environment variables for Azure OpenAI client"
        )

    return AzureOpenAI(
        engine=deployment_name,
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

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        raise TypeError("Missing ANTHROPIC_API_KEY environment variable")

    return Anthropic(
        model="claude-3-5-sonnet-20240620",
        api_key=api_key,
    )
