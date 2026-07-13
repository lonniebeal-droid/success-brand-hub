from .base import DeploymentAdapter


class TwilioDeployment(DeploymentAdapter):
    def __init__(self) -> None:
        super().__init__("twilio", ("JESSE_TWILIO_ACCOUNT_SID", "JESSE_TWILIO_AUTH_TOKEN", "JESSE_TWILIO_STAGING_NUMBER"))
