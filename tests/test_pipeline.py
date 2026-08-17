from unittest.mock import MagicMock

import pandas as pd
import pytest

import pipeline.main as pipeline_main
from pipeline.config import Settings


def test_pipeline_failure_does_not_advance_watermark(monkeypatch, tmp_path):
    settings = Settings(database_url="postgresql://private", output_dir=tmp_path)
    engine = MagicMock()
    update_watermark = MagicMock()

    monkeypatch.setattr(
        pipeline_main.Settings,
        "from_env",
        classmethod(lambda cls, env_file=None: settings),
    )
    monkeypatch.setattr(pipeline_main, "create_neon_engine", lambda current: engine)
    monkeypatch.setattr(pipeline_main, "read_watermark", lambda current, cfg: None)
    monkeypatch.setattr(
        pipeline_main,
        "extract_dimensions",
        lambda current, cfg: {"clientes": pd.DataFrame({"id": [1]})},
    )
    monkeypatch.setattr(
        pipeline_main,
        "extract_sales",
        lambda current, cfg, watermark: pd.DataFrame(
            {
                "nu_factura": ["F1"],
                "nu_item_factura": [1],
                "ts_movimiento": ["2026-08-17T10:00:00"],
            }
        ),
    )
    monkeypatch.setattr(
        pipeline_main,
        "_write_frames",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated load failure")
        ),
    )
    monkeypatch.setattr(pipeline_main, "update_watermark", update_watermark)

    with pytest.raises(RuntimeError, match="simulated load failure"):
        pipeline_main.run(["--destination", "local"])

    update_watermark.assert_not_called()
    engine.dispose.assert_called_once_with()
