"""Index schema for the single knowledge index (technical spec section 5)."""
from __future__ import annotations

from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)

from ..settings import Settings

VECTOR_PROFILE = "hnsw-cosine"
VECTORIZER = "aoai-embed"
SEMANTIC_CONFIG = "default"

_S = SearchFieldDataType.String
_COL_S = SearchFieldDataType.Collection(SearchFieldDataType.String)


def build_index(settings: Settings) -> SearchIndex:
    fields = [
        SearchField(name="id", type=_S, key=True, filterable=True, retrievable=True),
        SearchField(name="doc_type", type=_S, filterable=True, facetable=True),
        SearchField(name="title", type=_S, searchable=True),
        SearchField(name="content", type=_S, searchable=True, analyzer_name="en.lucene"),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=settings.embedding_dimensions,
            vector_search_profile_name=VECTOR_PROFILE,
        ),
        SearchField(name="applies_to", type=_COL_S, filterable=True, facetable=True),
        SearchField(name="sop_id", type=_S, filterable=True, facetable=True, searchable=True),
        SearchField(name="issue_type", type=_S, filterable=True, searchable=True),
        SearchField(name="section", type=_S, searchable=True),
        SearchField(name="error_codes", type=_COL_S, filterable=True, searchable=True),
        SearchField(name="severity", type=_S, filterable=True),
        SearchField(name="asset_id", type=_S, filterable=True, searchable=True),
        SearchField(name="source", type=_S, filterable=True, facetable=True),
        SearchField(name="sop_status", type=_S, filterable=True),
        SearchField(name="revision", type=SearchFieldDataType.Int32, filterable=True),
        SearchField(name="source_tickets", type=_COL_S, filterable=True),
        SearchField(name="previous_content", type=_S, searchable=False, filterable=False),
        SearchField(name="updated_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-config", parameters={"metric": "cosine"})],
        profiles=[VectorSearchProfile(name=VECTOR_PROFILE, algorithm_configuration_name="hnsw-config", vectorizer_name=VECTORIZER)],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name=VECTORIZER,
                # No api_key: the Search service's managed identity authenticates to the embedding deployment.
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url=settings.foundry_openai_endpoint,
                    deployment_name=settings.embedding_deployment,
                    model_name=settings.embedding_deployment,
                ),
            )
        ],
    )

    semantic = SemanticSearch(
        default_configuration_name=SEMANTIC_CONFIG,
        configurations=[
            SemanticConfiguration(
                name=SEMANTIC_CONFIG,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="error_codes"), SemanticField(field_name="issue_type")],
                ),
            )
        ],
    )

    return SearchIndex(name=settings.search_index_name, fields=fields, vector_search=vector_search, semantic_search=semantic)
