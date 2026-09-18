"""KDF exceptions."""


class KDFException(Exception):
    """Base exception for all KDF errors."""
    pass


class ConfigurationError(KDFException):
    """Configuration validation error."""
    pass


class ConnectionError(KDFException):
    """Connection error."""
    pass


class ValidationError(KDFException):
    """Validation error."""
    pass


class SkillExecutionError(KDFException):
    """Skill execution error."""
    pass


class SchemaError(KDFException):
    """Schema-related error."""
    pass


class MetadataError(KDFException):
    """Metadata operation error."""
    pass


class RegistryError(KDFException):
    """Registry operation error."""
    pass
