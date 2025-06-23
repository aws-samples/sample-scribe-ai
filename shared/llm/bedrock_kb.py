import os
import logging
import boto3
import urllib

from shared.config import config
from shared import log

kb = boto3.client("bedrock-agent-runtime")


def get_relevant_docs(query, top_k, scope_name):
    """
    Retrieves relevant documents from a vector store with metadata filtering by scope name.

    Args:
        query: The query to search for
        top_k: Maximum number of results to return
        scope_name: Required scope name to filter results

    Returns:
        List of relevant documents
    """
    # Configure the retrieval request
    retrieval_config = {
        "vectorSearchConfiguration": {
            "numberOfResults": top_k,
        }
    }

    # Apply metadata filter using the provided scope_name
    logging.info(f"Applying metadata filter for scope_name: {scope_name}")

    # Create a metadata filter to match documents with the specified scope_name
    metadata_filter = {
        "equals": {
            "key": "scope_name",
            "value": scope_name
        }
    }

    # Add the filter to the retrieval configuration
    retrieval_config["vectorSearchConfiguration"]["filter"] = metadata_filter

    try:
        response = kb.retrieve(
            knowledgeBaseId=config.knowledge_base_id,
            retrievalConfiguration=retrieval_config,
            retrievalQuery={"text": query}
        )

        result_count = len(response["retrievalResults"])
        logging.info(
            f"KB response found {result_count} results for scope: {scope_name}")
        log.debug(response)

        return response["retrievalResults"]
    except Exception as e:
        logging.error(f"Error retrieving documents: {e}")
        return []


def format_sources(sources):
    """
    Formats source docs in a standard format.

    Return dict example:
    [
        {
            "name": "MyDocument.pdf",
            "url": "https://document-server/MyDocument.pdf"
            "score": .8525
        }
    ]
    """

    result = []
    for source in sources:
        key = ""
        if source["location"]["type"] == "S3":

            # remove s3 bucket prefix for name and dedupe
            parsed = urllib.parse.urlparse(
                source["location"]["s3Location"]["uri"])
            key = parsed.path.lstrip("/")

            # todo: get presigned url
            url = ""

        # dedupe
        if not any(d["name"] == key for d in result):
            result.append({
                "name": key,
                "url": url,
                "score": source["score"],
            })

    return result
