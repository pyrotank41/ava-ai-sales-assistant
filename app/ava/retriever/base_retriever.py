from abc import ABC, abstractmethod
from llama_index.core.schema import NodeWithScore

class BaseRetriever(ABC):

    @abstractmethod
    def get_collection_name(self) -> str:
        """
        Returns the name of the collection associated with the retriever.

        :return: The name of the collection.
        :rtype: str
        """
    

    @abstractmethod
    def retrieve(self, query: str) -> list[NodeWithScore]:
        """
        Retrieves a list of nodes with scores based on the given query.

        Args:
            query (str): The query string.

        Returns:
            list[NodeWithScore]: A list of nodes with scores.
        """
        
