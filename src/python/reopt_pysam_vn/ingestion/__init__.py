"""Factory data ingestion: generic load normalization and metadata extraction."""

from .loader import FactoryLoadResult, LoadLengthError, ingest_factory_load

__all__ = ["FactoryLoadResult", "LoadLengthError", "ingest_factory_load"]
