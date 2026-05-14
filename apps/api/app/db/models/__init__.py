"""Database models — re-exports all SQLModel table definitions."""

from app.db.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.db.models.analysis_result import AnalysisResult
from app.db.models.auth_identity import AuthIdentity
from app.db.models.base import SQLModel as BaseModel
from app.db.models.game_asset import GameAsset
from app.db.models.hero_asset import HeroAsset
from app.db.models.replay_parse_artifact import ReplayParseArtifact
from app.db.models.upload import Upload, UploadKind, UploadStatus
from app.db.models.user import User

__all__ = [
    "AnalysisJob",
    "AnalysisJobStatus",
    "AnalysisResult",
    "AuthIdentity",
    "BaseModel",
    "GameAsset",
    "HeroAsset",
    "ReplayParseArtifact",
    "Upload",
    "UploadKind",
    "UploadStatus",
    "User",
]
