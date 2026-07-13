from pathlib import Path


WORKFLOW = Path(".github/workflows/google-sheets-metadata-test.yml")


def test_metadata_workflow_is_manual_and_read_only() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "environment: staging" in workflow
    assert "id-token: write" in workflow
    assert "google-github-actions/auth@v3" in workflow
    assert "includeGridData=false" in workflow
    assert "sheets.properties(sheetId,title,index,sheetType)" in workflow
    assert "rows_read: 0" in workflow
    assert "rows_written: 0" in workflow

    forbidden = (
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "values.append",
        "values.update",
        "batchUpdate",
        "spreadsheets.values",
    )
    for value in forbidden:
        assert value not in workflow


def test_metadata_workflow_does_not_enable_sandbox() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "GOOGLE_SHEETS_SANDBOX_ENABLED=true" not in workflow
    assert "GOOGLE_SHEETS_MODE=sandbox" not in workflow
