from datetime import datetime
from typing import Optional
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core import StorageContext
from llama_index.core import Settings
from llama_index.core.schema import NodeWithScore

import qdrant_client
from loguru import logger

from ava.retriever.base_retriever import BaseRetriever
from ava.embeddings.aoai_ada_002 import get_embedding_model
from ava.retriever.utils import get_nodes_from_objection_handelling_sheet

class ObjectionHandelingRetriever(BaseRetriever):

    def __init__(
        self,
        engine: Optional[BaseRetriever] = None,
        collection_name: Optional[str] = "objection_handelling",
        similarity_top_k:int = 3
    ) -> None:
        self.collection_name = collection_name
        self.engine = engine

        collection_name = "objection_handelling"
        
        nodes = get_nodes_from_objection_handelling_sheet(
            collection_name=collection_name
        )

        vector_db_client = qdrant_client.QdrantClient(location=":memory:")
        self.vector_store = QdrantVectorStore(
            client=vector_db_client, collection_name=collection_name
        )

        Settings.embed_model = get_embedding_model()
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        index = VectorStoreIndex(nodes=nodes, storage_context=self.storage_context)
        self.engine = index.as_retriever(similarity_top_k=similarity_top_k)

    def get_collection_name(self) -> str:
        """
        Returns the name of the collection associated with the retriever.

        Raises:
            ValueError: If the engine is not initialized.

        Returns:
            str: The name of the collection.
        """
        if not self.engine:
            logger.error("Engine not initialized")
            raise ValueError("Engine not initialized")
        return self.collection_name

    def retrieve(self, query: str) -> list[NodeWithScore]:
        """
        Retrieves nodes based on the given query.

        Args:
            query (str): The query string to search for.

        Returns:
            list[NodeWithScore]: A list of nodes with their corresponding scores.
        """
        if not self.engine:
            logger.error("Engine not initialized")
            raise ValueError("Engine not initialized")
        if not isinstance(query, str):
            logger.error("Invalid input. Expected a string")
            raise TypeError("Invalid input. Expected a string")
        return self.engine.retrieve(query)


if __name__ == "__main__":

    from dotenv import load_dotenv

    load_dotenv()
    retriever = ObjectionHandelingRetriever(similarity_top_k=5)

    while True:
        user_query = input("Enter a query: ")
        start_time = datetime.now()
        results = retriever.retrieve(user_query)
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()
        logger.info(f"retrieved {len(results)} nodes in {elapsed_time:.2f}")
        # if logger.level("DEBUG"), print the results
        if logger.level("DEBUG"):
            for result in results:
                logger.debug(f"{result.id_}\n objection: {result.text}\n rebuttal: {result.metadata['rebuttal']}\n collection_name: {result.metadata['collection_name']}\n score: {result.score}\n")
                logger.trace(result.metadata)
                

        logger.info(retriever.collection_name)
