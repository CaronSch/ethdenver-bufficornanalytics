from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

from helpers.interfaces import Network


DEFAULT_REQUEST_TIMEOUT = 60


class ElasticsearchFactory:
    """
    A factory that generates Elasticsearch clients for different networks.

    Follow https://www.anyblockanalytics.com/docs/elastic/
    to read more about the available endpoints and data types.
    """

    def __init__(self, api: str):
        self.elasticsearch_url = f'https://tech%40anyblockanalytics.com:{api}@api.anyblock.tools'
        self._client_cache: dict[str, Elasticsearch] = {}

    def get_dsl_client(self, network: Network) -> Search:
        """Return an initialized Elasticsearch DSL client."""
        return Search(using=self.get_client(network))

    def get_client(self, network: Network) -> Elasticsearch:
        """Return an initialized Elasticsearch client."""
        if not self.elasticsearch_url:
            raise RuntimeError("ELASTICSEARCH_URL is not defined")
        if network.key not in self._client_cache:
            es_url = self.get_endpoint(network)
            self._client_cache[network.key] = Elasticsearch(
                hosts=[es_url], timeout=DEFAULT_REQUEST_TIMEOUT
            )
        return self._client_cache[network.key]

    def get_endpoint(self, network: Network) -> str:
        """Return the URL for the Elasticsearch endpoint."""
        url = self.elasticsearch_url.rstrip("/")
        return f"{url}/{network.technology}/{network.blockchain}/{network.network}/es/"
