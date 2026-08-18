from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from pipeline.config import Settings
from pipeline.extract.api import fetch_holidays
from pipeline.extract.database import max_sales_watermark, update_watermark


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return [
            {
                "date": "2026-07-28",
                "localName": "Fiestas Patrias",
                "name": "Independence Day",
                "countryCode": "PE",
                "global": True,
                "counties": None,
            }
        ]


class FakeSession:
    def __init__(self):
        self.calls = 0

    def get(self, url, timeout):
        assert url.endswith("/2026/PE")
        assert timeout == 20
        self.calls += 1
        return FakeResponse()


def test_holiday_api_uses_cache(tmp_path: Path):
    settings = Settings(database_url="")
    session = FakeSession()

    first = fetch_holidays([2026], settings, cache_dir=tmp_path, session=session)
    second = fetch_holidays([2026], settings, cache_dir=tmp_path, session=session)

    assert session.calls == 1
    assert first.equals(second)
    assert first.loc[0, "name"] == "Independence Day"


def test_settings_loads_project_environment(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("PROJECT_ENV", raising=False)
    env_file = tmp_path / "pipeline.env"
    env_file.write_text("PROJECT_ENV=QA\n", encoding="utf-8")

    settings = Settings.from_env(env_file)

    assert settings.project_env == "qa"


def test_settings_rejects_empty_project_environment():
    with pytest.raises(ValueError, match="PROJECT_ENV"):
        Settings(database_url="", project_env="")


def test_candidate_watermark_uses_latest_timestamp():
    sales = pd.DataFrame(
        {
            "ts_movimiento": [
                "2026-01-01T10:00:00",
                "2026-01-03T12:30:00",
                "2026-01-02T09:00:00",
            ]
        }
    )
    assert max_sales_watermark(sales) == datetime(2026, 1, 3, 12, 30)


def test_azure_requires_connection_string():
    with pytest.raises(ValueError, match="AZURE_STORAGE_CONNECTION_STRING"):
        Settings(database_url="", destination="azure")


def test_azurite_uses_free_local_default():
    settings = Settings(database_url="", destination="azurite")
    assert settings.azure_storage_connection_string == ""


def test_equal_watermark_with_mixed_timezones_is_a_valid_noop():
    candidate = datetime(2026, 1, 3, 12, 30)
    stored = datetime(2026, 1, 3, 12, 30, tzinfo=timezone.utc)
    settings = Settings(database_url="")
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    update_result = MagicMock(rowcount=0)
    select_result = MagicMock()
    select_result.scalar_one_or_none.return_value = stored
    connection.execute.side_effect = [update_result, select_result]

    update_watermark(engine, settings, candidate)

    assert connection.execute.call_count == 2
