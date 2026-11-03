"""Data validation: schema checks, duplicate detection, quality stats."""
from fmcg.validation.schema_validator import validate_records, validate_single_record

__all__ = ["validate_records", "validate_single_record"]
