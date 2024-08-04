import os
import tempfile
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from loguru import logger


def load_env_vars():

    if os.path.exists(".env"):
        load_dotenv(".env")
        logger.info("Environment variables loaded successfully from local .env file")
        return

    logger.info("No local .env file found, attempting to load from remote storage")
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    blob_name = os.getenv("BLOB_NAME")

    if not connection_string or not container_name or not blob_name:
        logger.error(
            "Required environment variables (AZURE_STORAGE_CONNECTION_STRING, BLOB_CONTAINER_NAME, BLOB_NAME) are not set"
        )
        raise ValueError("Required environment variables are not set")

    try:
        logger.info("Using connection string to access Azure Blob Storage")
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        logger.info(f"Downloading blob content from {container_name}/{blob_name}")

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            logger.info("Downloading blob content")
            download_stream = blob_client.download_blob()
            temp_file.write(download_stream.readall())

        logger.info(f"Loading environment variables from {temp_file.name}")
        load_dotenv(temp_file.name)

        os.unlink(temp_file.name)
        logger.info("Environment variables loaded successfully from Azure Blob storage")

    except ResourceNotFoundError:
        logger.error(
            f"The blob {blob_name} in container {container_name} was not found"
        )
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        logger.info("Full error details:")
        logger.exception(e)


if __name__ == "__main__":
    load_env_vars()
