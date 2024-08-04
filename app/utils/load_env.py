import os
import tempfile
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.storage.blob import BlobClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
from loguru import logger

def get_and_load_env_file():
    load_dotenv(".env.local")

    blob_url = os.getenv("BLOB_URL")

    if not blob_url:
        logger.error("BLOB_URL environment variable is not set")
        raise ValueError("BLOB_URL environment variable is not set")

    try:
        # Determine the environment and set the appropriate credential
        if os.getenv("AZURE_ENVIRONMENT") == "production":
            logger.info("Using DefaultAzureCredential for production environment")
            credential = DefaultAzureCredential()
        else:
            logger.info("Using AzureCliCredential for local development")
            credential = AzureCliCredential()

        logger.info(f"Attempting to access blob at URL: {blob_url}")
        blob_client = BlobClient.from_blob_url(blob_url, credential=credential)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            logger.info("Downloading blob content")
            download_stream = blob_client.download_blob()
            temp_file.write(download_stream.readall())

        logger.info(f"Loading environment variables from {temp_file.name}")
        load_dotenv(temp_file.name)

        os.unlink(temp_file.name)
        logger.info("Environment variables loaded successfully from Azure Blob storage")

    except ResourceNotFoundError:
        logger.error(f"The blob at {blob_url} was not found")
    except ClientAuthenticationError as e:
        logger.error(f"Authentication failed: {str(e)}")
        logger.info(
            "Please check your Managed Identity configuration and role assignments"
        )
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.info("Full error details:")
        logger.exception(e)


if __name__ == "__main__":
    get_and_load_env_file()
