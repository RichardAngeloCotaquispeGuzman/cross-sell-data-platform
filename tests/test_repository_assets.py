import json
from pathlib import Path

import yaml


def test_json_contracts_and_notebook_are_valid():
    for path in Path("data_contracts/schema").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))

    notebook = json.loads(
        Path("notebooks/exploration.ipynb").read_text(encoding="utf-8")
    )
    assert notebook["nbformat"] == 4
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            compile("".join(cell["source"]), "exploration.ipynb", "exec")


def test_github_workflows_are_valid_yaml():
    workflows = sorted(Path(".github/workflows").glob("*.yml"))
    assert workflows
    for path in workflows:
        assert yaml.safe_load(path.read_text(encoding="utf-8"))


def test_mermaid_sources_have_expected_diagram_types():
    assert Path("architecture/diagrams/pipeline.mmd").read_text().startswith(
        "flowchart"
    )
    assert Path("architecture/diagrams/incremental-flow.mmd").read_text().startswith(
        "sequenceDiagram"
    )
