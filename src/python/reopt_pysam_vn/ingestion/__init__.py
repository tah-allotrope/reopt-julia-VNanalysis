"""Factory data ingestion: generic load normalization and metadata extraction."""

from .loader import FactoryLoadResult, LoadLengthError, ingest_factory_load
from .metadata import (
    ArchetypeResult,
    LoadMetadata,
    TOUClassification,
    classify_industry_archetype,
    classify_tou_consumption,
    extract_load_metadata,
)

__all__ = [
    "ArchetypeResult",
    "FactoryLoadResult",
    "LoadLengthError",
    "LoadMetadata",
    "TOUClassification",
    "classify_industry_archetype",
    "classify_tou_consumption",
    "extract_load_metadata",
    "ingest_factory_load",
]
