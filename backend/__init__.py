"""
Backend package for Schedule F comment analysis pipeline.

This package provides tools for fetching, analyzing, and processing 
public comments on federal regulations.
"""

from .config import config, Config, LLMConfig, FileConfig, AttachmentConfig
from .utils import (
    CommentAnalyzer,
    FileManager,
    PipelineLogger,
    setup_pipeline_logging,
    PipelineError,
    ConfigurationError,
    DataProcessingError,
    LLMAnalysisError,
)

__version__ = "1.0.0"
__all__ = [
    # Configuration
    "config",
    "Config",
    "LLMConfig", 
    "FileConfig",
    "AttachmentConfig",
    
    # Core utilities
    "CommentAnalyzer",
    "FileManager", 
    "PipelineLogger",
    "setup_pipeline_logging",
    
    # Exceptions
    "PipelineError",
    "ConfigurationError",
    "DataProcessingError", 
    "LLMAnalysisError",
]