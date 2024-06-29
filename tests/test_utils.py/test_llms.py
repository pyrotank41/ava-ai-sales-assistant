import os
import pytest
from unittest.mock import patch, MagicMock
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.anthropic import Anthropic

# Import the functions to be tested
from ava.utils.llms import get_azure_openai_client, get_anthropic_client


@pytest.fixture
def mock_env_vars():
    """Fixture to mock environment variables."""
    with patch.dict(
        os.environ,
        {
            "AZURE_OPENAI_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "test-api-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
        },
    ):
        yield

@pytest.fixture
def mock_env_vars_missing():
    """Fixture to mock missing environment variables."""
    with patch.dict(
        os.environ,
        {
        },
    ):
        yield

def test_get_azure_openai_client(mock_env_vars):
    """Test the get_azure_openai_client function."""
    with patch("ava.utils.llms.AzureOpenAI") as mock_azure:
        mock_azure.return_value = MagicMock(spec=AzureOpenAI)

        client = get_azure_openai_client()

        assert isinstance(client, AzureOpenAI)
        mock_azure.assert_called_once_with(
            engine="test-deployment",
            model="gpt-4o",
            temperature=0.0,
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-api-key",
            api_version="2024-02-01",
        )


def test_get_anthropic_client(mock_env_vars):
    """Test the get_anthropic_client function."""
    with patch("ava.utils.llms.Anthropic") as mock_anthropic:
        mock_anthropic.return_value = MagicMock(spec=Anthropic)

        client = get_anthropic_client()

        assert isinstance(client, Anthropic)
        mock_anthropic.assert_called_once_with(
            model="claude-3-5-sonnet-20240620", api_key="test-anthropic-key"
        )


def test_azure_openai_client_missing_env_vars(mock_env_vars_missing):
    """Test get_azure_openai_client with missing environment variables."""
    with pytest.raises(TypeError):
        get_azure_openai_client()


def test_anthropic_client_missing_env_vars(mock_env_vars_missing):
    """Test get_anthropic_client with missing environment variables."""
    with pytest.raises(TypeError):
        get_anthropic_client()
