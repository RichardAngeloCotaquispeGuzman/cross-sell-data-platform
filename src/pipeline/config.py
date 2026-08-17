"""External configuration for the cross-selling pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

_ALLOWED_DESTINATIONS = {"local", "azurite", "azure"}

def _load_environment(env_file: str | Path | None) -> None:
    if env_file is None:
        load_dotenv()
        return
    lines = Path(env_file).read_text(encoding="utf-8").splitlines()
    assignments = "\n".join(
        line for line in lines if "=" in line and line.split("=", 1)[0].isidentifier()
    )
    for key, value in dotenv_values(stream=StringIO(assignments)).items():
        if value is not None:
            os.environ.setdefault(key, value)


def _as_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _as_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    """Validated runtime settings loaded from environment variables."""

    database_url: str = field(repr=False)
    source_schema: str = "source"
    control_schema: str = "control"
    pipeline_name: str = "cross_sell_pipeline"
    log_level: str = "INFO"
    holiday_api_url: str = "https://date.nager.at/api/v3/PublicHolidays"
    holiday_country_code: str = "PE"
    api_timeout_sec: int = 20
    api_max_retries: int = 3
    destination: str = "local"
    output_dir: Path = Path("out")
    azure_storage_container: str = "lakehouse"
    azure_storage_connection_string: str = field(default="", repr=False)
    min_pair_invoices: int = 2
    min_support: float = 0.0001
    min_confidence: float = 0.01
    min_lift: float = 1.0
    max_recommendations_per_customer: int = 10

    def __post_init__(self) -> None:
        if self.destination not in _ALLOWED_DESTINATIONS:
            choices = ", ".join(sorted(_ALLOWED_DESTINATIONS))
            raise ValueError(f"DESTINATION must be one of: {choices}")
        if self.api_timeout_sec <= 0 or self.api_max_retries <= 0:
            raise ValueError("API timeout and retries must be positive")
        if self.destination == "azure" and not self.azure_storage_connection_string:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is required for Azure"
            )

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Settings":
        """Load settings without ever logging or exposing secret values."""
        _load_environment(env_file)
        return cls(
            database_url=(os.getenv("DATABASE_URL") or os.getenv("NEON_DATABASE_URL", "")),
            source_schema=os.getenv("SOURCE_SCHEMA", "source"),
            control_schema=os.getenv("CONTROL_SCHEMA", "control"),
            pipeline_name=os.getenv("PIPELINE_NAME", "cross_sell_pipeline"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            holiday_api_url=os.getenv(
                "HOLIDAY_API_URL", "https://date.nager.at/api/v3/PublicHolidays"
            ),
            holiday_country_code=os.getenv("HOLIDAY_COUNTRY_CODE", "PE"),
            api_timeout_sec=_as_int("API_TIMEOUT_SEC", 20),
            api_max_retries=_as_int("API_MAX_RETRIES", 3),
            destination=os.getenv("DESTINATION", "local").lower(),
            output_dir=Path(os.getenv("OUTPUT_DIR", "./out")),
            azure_storage_container=os.getenv("AZURE_STORAGE_CONTAINER", "lakehouse"),
            azure_storage_connection_string=os.getenv(
                "AZURE_STORAGE_CONNECTION_STRING", ""
            ),
            min_pair_invoices=_as_int("MIN_PAIR_INVOICES", 2),
            min_support=_as_float("MIN_SUPPORT", 0.0001),
            min_confidence=_as_float("MIN_CONFIDENCE", 0.01),
            min_lift=_as_float("MIN_LIFT", 1.0),
            max_recommendations_per_customer=_as_int(
                "MAX_RECOMMENDATIONS_PER_CUSTOMER", 10
            ),
        )

    def require_database_url(self) -> str:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required to extract from Neon")
        return self.database_url
