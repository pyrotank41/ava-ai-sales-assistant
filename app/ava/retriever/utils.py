import pandas as pd
from loguru import logger
from llama_index.core.schema import TextNode

from app.ava.utils.google_drive_utils import (
    get_objection_handelling_vars,
    get_google_sheets_data,
)


def get_nodes_from_objection_handelling_sheet(collection_name) -> list[TextNode]:

    api_key, sheet_id = get_objection_handelling_vars()
    data = get_google_sheets_data(api_key=api_key, sheet_id=sheet_id)
    df = data[0].data_frame
    if not isinstance(df, pd.DataFrame):
        logger.error("Invalid input. Expected a pandas DataFrame")
        raise TypeError("Invalid input. Expected a pandas DataFrame")

    nodes: list[TextNode] = []
    for row in df.values:
        # Create a TextNode object
        node = TextNode(
            text=row[0],
            metadata={"rebuttal": row[1], "collection_name": collection_name},
        )
        # Add the node to the list
        nodes.append(node)
    return nodes
