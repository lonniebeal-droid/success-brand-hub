from .base import DeploymentAdapter


class GoogleDeployment(DeploymentAdapter):
    def __init__(self) -> None:
        super().__init__("google-sheets-sandbox", (
            "GCP_PROJECT_ID",
            "GOOGLE_AUTH_MODE",
            "GOOGLE_SHEETS_MODE",
            "GOOGLE_SHEETS_SANDBOX_ENABLED",
            "GOOGLE_SHEETS_SPREADSHEET_ID",
            "GOOGLE_SHEETS_WORKSHEET_NAME",
        ))
