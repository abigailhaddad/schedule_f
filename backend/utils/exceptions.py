"""
Custom exception classes for the pipeline.

This module defines specific exception types to improve error handling
and provide better context for debugging.
"""

from typing import Optional, Any


class PipelineError(Exception):
    """Base exception for all pipeline-related errors."""
    
    def __init__(self, message: str, context: Optional[dict] = None):
        super().__init__(message)
        self.context = context or {}


class ConfigurationError(PipelineError):
    """Raised when there's an issue with configuration."""
    pass


class DataProcessingError(PipelineError):
    """Raised when there's an error processing data."""
    
    def __init__(self, message: str, item_id: Optional[str] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.item_id = item_id


class LLMAnalysisError(PipelineError):
    """Raised when LLM analysis fails."""
    
    def __init__(self, message: str, comment_id: Optional[str] = None, attempt: Optional[int] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.comment_id = comment_id
        self.attempt = attempt


class TimeoutError(PipelineError):
    """Raised when an operation times out."""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.timeout_duration = timeout_duration


class FileOperationError(PipelineError):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: Optional[str] = None, operation: Optional[str] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.file_path = file_path
        self.operation = operation


class ValidationError(PipelineError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.field = field
        self.value = value


class AttachmentError(PipelineError):
    """Raised when attachment processing fails."""
    
    def __init__(self, message: str, attachment_url: Optional[str] = None, context: Optional[dict] = None):
        super().__init__(message, context)
        self.attachment_url = attachment_url