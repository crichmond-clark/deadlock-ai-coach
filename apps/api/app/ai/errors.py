"""Normalized errors for AI provider and structured analysis failures."""


class AIError(Exception):
    """Base class for AI integration errors."""


class AIProviderConfigurationError(AIError):
    """Raised when an AI provider is missing required configuration."""


class AIProviderError(AIError):
    """Raised when an AI provider returns an unrecoverable error."""


class AIProviderTimeoutError(AIProviderError):
    """Raised when an AI provider request times out."""


class AIProviderInvalidResponseError(AIProviderError):
    """Raised when a provider response cannot be parsed as structured JSON."""


class AISchemaValidationError(AIError):
    """Raised when provider JSON does not match the app-owned output schema."""
