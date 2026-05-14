"""Database models — re-exports all SQLModel table definitions."""

from app.db.models.ai_model_run import AIModelRun, AIModelRunStatus
from app.db.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.db.models.analysis_result import AnalysisResult
from app.db.models.auth_identity import AuthIdentity
from app.db.models.base import SQLModel as BaseModel
from app.db.models.external_match_metadata import ExternalMatchMetadata
from app.db.models.game_asset import GameAsset
from app.db.models.hero_asset import HeroAsset
from app.db.models.knowledge_chunk import KnowledgeChunk
from app.db.models.knowledge_embedding import KnowledgeEmbedding
from app.db.models.knowledge_source import KnowledgeSource
from app.db.models.replay_parse_artifact import ReplayParseArtifact
from app.db.models.upload import Upload, UploadKind, UploadStatus
from app.db.models.user import User

__all__ = [
    "AIModelRun",
    "AIModelRunStatus",
    "AnalysisJob",
    "AnalysisJobStatus",
    "AnalysisResult",
    "AuthIdentity",
    "BaseModel",
    "ExternalMatchMetadata",
    "GameAsset",
    "HeroAsset",
    "KnowledgeChunk",
    "KnowledgeEmbedding",
    "KnowledgeSource",
    "ReplayParseArtifact",
    "Upload",
    "UploadKind",
    "UploadStatus",
    "User",
]
