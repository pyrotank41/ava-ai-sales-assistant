import json
import os
from loguru import logger
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError


def upload_file_to_blob(connection_string, container_name, blob_name, file_path):
    """
    Upload a file to Azure Blob Storage.

    :param connection_string: Azure Storage account connection string
    :param container_name: Name of the container to upload to
    :param blob_name: Name to give the blob in storage
    :param file_path: Local path of the file to upload
    :return: True if upload was successful, False otherwise
    """
    try:
        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )

        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Create the container if it doesn't exist
        try:
            container_client.create_container()
            logger.info(f"Container '{container_name}' created.")
        except ResourceExistsError:
            logger.info(f"Container '{container_name}' already exists.")

        # Get the blob client
        blob_client = container_client.get_blob_client(blob_name)

        # Upload the file
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        logger.info(
            f"File '{file_path}' uploaded to blob '{blob_name}' in container '{container_name}' successfully."
        )
        return True

    except Exception as e:
        logger.error(f"An error occurred while uploading file to blob: {str(e)}")
        logger.exception(e)
        return False


def get_blob_content(connection_string, container_name, blob_name):
    """
    Retrieve the content of a blob from Azure Blob Storage.
    """
    try:
        logger.info("Using connection string to access Azure Blob Storage")
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        logger.info(f"Downloading blob content from {container_name}/{blob_name}")
        download_stream = blob_client.download_blob()
        return download_stream.readall()
    except ResourceNotFoundError:
        logger.error(
            f"The blob {blob_name} in container {container_name} was not found"
        )
        return None
    except Exception as e:
        logger.error(f"An error occurred while getting blob content: {str(e)}")
        logger.info("Full error details:")
        logger.exception(e)
        return None


def get_default_azure_connection_string():
    """
    Retrieve the Azure Storage account connection string from environment variables.
    """
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError(
            "Azure Storage connection string not found in environment variables"
        )
    return connection_string


def get_default_azure_container_name():
    """
    Retrieve the Azure Storage container name from environment variables.
    """
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    if not container_name:
        raise ValueError(
            "Azure Storage container name not found in environment variables"
        )
    return container_name

def upload_json_to_blob(
    connection_string, container_name, blob_name, json_data
) -> bool:
    """
    Upload a JSON object to Azure Blob Storage.

    :param connection_string: Azure Storage account connection string
    :param container_name: Name of the container to upload to
    :param blob_name: Name to give the blob in storage
    :param json_data: Python dictionary to be uploaded as JSON
    :return: True if upload was successful, False otherwise
    """
    try:
        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )

        # Get the container client
        container_client = blob_service_client.get_container_client(container_name)

        # Create the container if it doesn't exist
        try:
            container_client.create_container()
            logger.info(f"Container '{container_name}' created.")
        except ResourceExistsError:
            logger.info(f"Container '{container_name}' already exists.")

        # Get the blob client
        blob_client = container_client.get_blob_client(blob_name)

        # Convert the dictionary to a JSON string
        json_string = json.dumps(json_data, indent=2)

        # Upload the JSON string
        blob_client.upload_blob(
            json_string, overwrite=True, content_type="application/json"
        )

        logger.info(
            f"JSON data uploaded to blob '{blob_name}' in container '{container_name}' successfully."
        )
        return True

    except Exception as e:
        logger.error(f"An error occurred while uploading JSON to blob: {str(e)}")
        logger.exception(e)
        return False


def get_json_from_blob(connection_string, container_name, blob_name) -> dict:
    """
    Retrieve and parse a JSON object from Azure Blob Storage.

    :param connection_string: Azure Storage account connection string
    :param container_name: Name of the container
    :param blob_name: Name of the blob to retrieve
    :return: Parsed JSON data as a Python dictionary, or None if retrieval fails
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(
            connection_string
        )
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )

        logger.info(f"Downloading JSON blob content from {container_name}/{blob_name}")
        download_stream = blob_client.download_blob()
        json_string = download_stream.readall().decode("utf-8")

        # Parse the JSON string
        json_data = json.loads(json_string)

        logger.info(f"JSON data retrieved and parsed successfully from {blob_name}")
        return json_data

    except ResourceNotFoundError:
        logger.error(
            f"The blob {blob_name} in container {container_name} was not found"
        )
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON content from blob {blob_name}")
        return None
    except Exception as e:
        logger.error(f"An error occurred while getting JSON from blob: {str(e)}")
        logger.exception(e)
        return None
