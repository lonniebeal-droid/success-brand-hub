from .base import DeploymentAdapter


class N8NDeployment(DeploymentAdapter):
    def __init__(self) -> None:
        super().__init__("n8n", ("JESSE_N8N_BASE_URL", "JESSE_N8N_API_KEY", "JESSE_N8N_STAGING_WORKFLOW_ID"))
