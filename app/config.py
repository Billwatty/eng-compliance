"""Runtime configuration, read from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    model: str
    extraction_effort: str
    rule_draft_effort: str
    use_fallbacks: bool
    auto_link_threshold: float
    whatsapp_verify_token: str
    whatsapp_app_secret: str
    whatsapp_access_token: str
    whatsapp_graph_version: str

    @property
    def db_path(self) -> Path:
        return self.data_dir / "compliance.db"

    @property
    def vault_dir(self) -> Path:
        return self.data_dir / "vault"


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("VBC_DATA_DIR", BASE_DIR / "var"))
    return Settings(
        data_dir=data_dir,
        model=os.environ.get("VBC_MODEL", "claude-opus-5-5"),
        extraction_effort=os.environ.get("VBC_EXTRACTION_EFFORT", "medium"),
        rule_draft_effort=os.environ.get("VBC_RULE_DRAFT_EFFORT", "high"),
        use_fallbacks=os.environ.get("VBC_USE_FALLBACKS", "1") == "1",
        auto_link_threshold=float(os.environ.get("VBC_AUTO_LINK_THRESHOLD", "0.9")),
        whatsapp_verify_token=os.environ.get("WHATSAPP_VERIFY_TOKEN", ""),
        whatsapp_app_secret=os.environ.get("WHATSAPP_APP_SECRET", ""),
        whatsapp_access_token=os.environ.get("WHATSAPP_ACCESS_TOKEN", ""),
        whatsapp_graph_version=os.environ.get("WHATSAPP_GRAPH_VERSION", "v21.0"),
    )
