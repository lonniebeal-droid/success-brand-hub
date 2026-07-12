from .base import DeploymentAdapter


class ElevenLabsDeployment(DeploymentAdapter):
    def __init__(self) -> None:
        super().__init__("elevenlabs", ("JESSE_ELEVENLABS_API_KEY", "JESSE_ELEVENLABS_STAGING_AGENT_ID"))
