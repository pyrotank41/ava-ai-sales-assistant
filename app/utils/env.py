import os
from dotenv import load_dotenv
from loguru import logger
from utils.utility import store_content_temporarily
from .azure import get_default_azure_connection_string, get_blob_content, get_default_azure_container_name


def get_environment() -> str:
    """
    Determine the current environment.
    Returns 'development', 'staging', or 'production'.
    Defaults to 'development' if not set.
    """
    return os.getenv("ENV", "dev").lower()

def is_dev_env() -> bool:
    """Check if the current environment is development."""
    return get_environment() == "dev"

def is_prod_env() -> bool:
    """Check if the current environment is production."""
    return get_environment() == "prod"

def load_env_vars():
    env = get_environment()
    logger.debug(f"Current environment: {env}")

    if is_dev_env():
        env_file = "../.env"
        if os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Environment variables loaded successfully from {env_file}")
            return
        else:
            logger.warning(f"Development .env file not found at {env_file}")
            # Optionally, you might want to fall back to loading from Azure in dev environment
            # Instead of raising an error, we'll continue to the Azure loading logic

    # For non-dev environments or if dev .env file is not found
    logger.info("Attempting to load environment variables from Azure Blob Storage")
    connection_string = get_default_azure_connection_string()
    container_name = get_default_azure_container_name()
    blob_name = os.getenv("BLOB_NAME")

    if not all([connection_string, container_name, blob_name]):
        logger.error("Required Azure Blob Storage environment variables are not set")
        raise ValueError(
            "Required Azure Blob Storage environment variables are not set"
        )

    blob_content = get_blob_content(connection_string, container_name, blob_name)

    if blob_content:
        with store_content_temporarily(blob_content) as temp_file_name:
            if temp_file_name:
                logger.info(f"Loading environment variables from {temp_file_name}")
                load_dotenv(temp_file_name)
                logger.info(
                    "Environment variables loaded successfully from Azure Blob storage"
                )
            else:
                logger.error("Failed to store blob content temporarily")
    else:
        logger.error("Failed to get blob content from Azure")
        raise RuntimeError("Failed to load environment variables")


if __name__ == "__main__":
    load_env_vars()
