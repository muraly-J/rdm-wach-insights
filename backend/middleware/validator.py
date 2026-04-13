"""
middleware/validator.py
───────────────────────
The safety layer between LLM output and InfluxDB.

Responsibilities:
  1. Validate device IDs exist in the WACH allowed list
  2. Validate metric is in the MVP whitelist
  3. Validate time_range is one of the 4 allowed values
  4. Validate query_type / top_n consistency
  5. Return structured ValidationResult (never raises — caller decides how to handle)
"""

from dataclasses import dataclass, field

from models.schemas import (
    ALLOWED_DEVICES,
    ALLOWED_METRICS,
    ALLOWED_TIME_RANGES,
    QueryType,
    StructuredQuery,
)


@dataclass
class ValidationResult:
    is_valid:  bool
    errors:    list[str] = field(default_factory=list)
    warnings:  list[str] = field(default_factory=list)

    # Human-readable message to surface to the user when invalid
    @property
    def user_message(self) -> str:
        if self.is_valid:
            return "Query is valid."
        parts = []
        for err in self.errors:
            parts.append(err)
        return " ".join(parts)


def validate_query(query: StructuredQuery) -> ValidationResult:
    """
    Runs all validation checks on a StructuredQuery.
    Returns a ValidationResult — never raises an exception.
    """
    errors:   list[str] = []
    warnings: list[str] = []

    # ── 1. Metric whitelist ────────────────────────────────────────────────────
    if query.metric not in ALLOWED_METRICS:
        errors.append(
            f"'{query.metric}' is not a supported metric. "
            f"Available metrics: {', '.join(ALLOWED_METRICS)}."
        )

    # ── 2. Time range whitelist ────────────────────────────────────────────────
    if query.time_range not in ALLOWED_TIME_RANGES:
        errors.append(
            f"'{query.time_range}' is not a supported time range. "
            f"Supported ranges: {', '.join(ALLOWED_TIME_RANGES.keys())}."
        )

    # ── 3. Device ID validation ────────────────────────────────────────────────
    unknown_devices = [d for d in query.device_ids if d not in ALLOWED_DEVICES]
    if unknown_devices:
        errors.append(
            f"The following device(s) were not found in the WACH ward: "
            f"{', '.join(unknown_devices)}. "
            f"Please check the device ID and try again."
        )

    # ── 4. Query-type consistency checks ──────────────────────────────────────
    if query.query_type == QueryType.time_series:
        # Allow empty device_ids for ward/floor grouping (resolved server-side)
        if len(query.device_ids) > 5:
            warnings.append(
                f"Querying {len(query.device_ids)} devices at once may be slow. "
                "Consider limiting to 5 or fewer."
            )

    if query.query_type == QueryType.ranking:
        # For ranking, empty device_ids means "all devices" (valid)
        if query.top_n is None:
            # Default silently — not an error
            warnings.append("top_n not specified; defaulting to 10.")
        elif query.top_n < 1 or query.top_n > 50:
            errors.append(
                f"top_n must be between 1 and 50. Got: {query.top_n}."
            )

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_raw_dict(raw: dict) -> tuple[StructuredQuery | None, ValidationResult]:
    """
    Convenience wrapper: parse a raw dict (LLM output) into a StructuredQuery,
    then validate it. Returns (query, result) — query is None if parsing failed.
    """
    try:
        query = StructuredQuery(**raw)
    except Exception as e:
        result = ValidationResult(
            is_valid=False,
            errors=[f"Query could not be parsed: {str(e)}"],
        )
        return None, result

    result = validate_query(query)
    return query, result

def validate_structured_query(query: StructuredQuery) -> str | None:
    """
    FastAPI route helper: takes a StructuredQuery, returns error string or None.
    """
    result = validate_query(query)
    return None if result.is_valid else result.user_message
