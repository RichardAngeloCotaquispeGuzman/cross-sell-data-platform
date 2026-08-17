"""Free public-holiday API extraction with retries and local cache."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.config import Settings


def build_retrying_session(max_retries: int) -> requests.Session:
    retry = Retry(
        total=max_retries,
        connect=max_retries,
        read=max_retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def _cache_path(cache_dir: Path, country_code: str, year: int) -> Path:
    return cache_dir / f"holidays_{country_code.upper()}_{year}.json"


def _fetch_year(
    year: int,
    settings: Settings,
    session: requests.Session,
    cache_dir: Path | None,
) -> list[dict]:
    cache_file = (
        _cache_path(cache_dir, settings.holiday_country_code, year)
        if cache_dir
        else None
    )
    if cache_file and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    url = (
        f"{settings.holiday_api_url.rstrip('/')}/{year}/"
        f"{settings.holiday_country_code.upper()}"
    )
    response = session.get(url, timeout=settings.api_timeout_sec)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("Holiday API response must be a list")

    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return payload


def fetch_holidays(
    years: Iterable[int],
    settings: Settings,
    *,
    cache_dir: Path | None = None,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch unique years and return a normalized holiday DataFrame."""
    client = session or build_retrying_session(settings.api_max_retries)
    records: list[dict] = []
    for year in sorted(set(int(value) for value in years)):
        records.extend(_fetch_year(year, settings, client, cache_dir))

    columns = ["date", "localName", "name", "countryCode", "global", "counties"]
    if not records:
        return pd.DataFrame(columns=columns)

    holidays = pd.DataFrame.from_records(records)
    missing = {"date", "name"} - set(holidays.columns)
    if missing:
        raise ValueError(f"Holiday API response missing fields: {sorted(missing)}")
    holidays["date"] = pd.to_datetime(holidays["date"], errors="raise").dt.date
    return holidays.reindex(columns=columns).drop_duplicates(subset=["date", "name"])
