"""Environment-based configuration. No secrets: authentication is always Microsoft Entra."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Both the repo and the container use <root>/src/knowledge_enrichment, <root>/data, <root>/config.
APP_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=APP_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    ke_env: str = "dev"

    foundry_project_endpoint: str = "https://ai-foundry-common-ihub.services.ai.azure.com/api/projects/ihub-project-common"
    foundry_openai_endpoint: str = "https://ai-foundry-common-ihub.openai.azure.com"
    model_deployment: str = "gpt-5.4"
    embedding_deployment: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    search_endpoint: str = "https://ai-search-vector-001.search.windows.net"
    search_index_name: str = "ke-dev-knowledge"
    advisor_agent_name: str = "sop-advisor-dev"
    search_connection_name: str = "ke-search-entra"
    foundry_project_resource_id: str = ""
    search_resource_id: str = ""
    search_location: str = "switzerlandnorth"

    enrich_existing_sops: bool = True
    enrich_require_approval: bool = False
    match_min_confidence: float = 0.6
    new_issue_min_confidence: float = 0.7
    assess_min_confidence: float = 0.7
    enrich_duplicate_cosine: float = 0.92

    ke_audit_api_enabled: bool = True
    rate_limit_per_minute: int = 30
    max_issue_chars: int = 2000
    max_fix_chars: int = 4000

    agent_timeout_s: int = 90
    model_timeout_s: int = 60

    data_dir: Path = Field(default=APP_ROOT / "data")
    config_dir: Path = Field(default=APP_ROOT / "config")
    runtime_dir: Path = Field(default=APP_ROOT / "runtime")
    ui_dist_dir: Path = Field(default=APP_ROOT / "ui-dist")

    applicationinsights_connection_string: str = ""

    @property
    def sops_dir(self) -> Path:
        return self.data_dir / "sops"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def cognitive_scope(self) -> str:
        return "https://cognitiveservices.azure.com/.default"


@lru_cache
def get_settings() -> Settings:
    return Settings()
