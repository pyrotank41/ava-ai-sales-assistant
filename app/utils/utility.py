from contextlib import contextmanager
import os
import tempfile

from loguru import logger


@contextmanager
def store_content_temporarily(content):
    if content is None:
        yield None
        return

    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode="wb") as temp_file:
            temp_file.write(content)
            temp_file_name = temp_file.name
        logger.info(f"Content stored temporarily in {temp_file_name}")
        yield temp_file_name
    except Exception as e:
        logger.error(f"An error occurred while storing content temporarily: {str(e)}")
        logger.info("Full error details:")
        logger.exception(e)
        yield None
    finally:
        if temp_file and os.path.exists(temp_file_name):
            os.unlink(temp_file_name)
            logger.info(f"Temporary file {temp_file_name} has been deleted")
