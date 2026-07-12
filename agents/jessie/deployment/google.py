from .base import DeploymentAdapter


class GoogleDeployment(DeploymentAdapter):
    def __init__(self) -> None:
        super().__init__("google", ("JESSE_GOOGLE_CREDENTIALS_JSON", "JESSE_GOOGLE_STAGING_CALENDAR_ID", "JESSE_GOOGLE_STAGING_SHEET_ID"))
