"""Configuration management for the pipeline."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM analysis configuration."""
    model: str = "gpt-4o-mini"
    batch_size: int = 5
    max_retries: int = 3
    truncation: int = 1003
    timeout: int = 30
    
    def __post_init__(self):
        if self.batch_size <= 0:
            raise ValueError('Batch size must be positive')
        if self.timeout <= 0:
            raise ValueError('Timeout must be positive')


@dataclass
class FileConfig:
    """File management configuration."""
    raw_data_filename: str = "raw_data.json"
    lookup_table_filename: str = "lookup_table.json"
    output_dir: str = "."


@dataclass  
class AttachmentConfig:
    """Attachment processing configuration."""
    retries: int = 1
    
    def __post_init__(self):
        if self.retries < 0:
            raise ValueError('Retries cannot be negative')


@dataclass
class Config:
    """Main configuration class."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    files: FileConfig = field(default_factory=FileConfig)
    attachments: AttachmentConfig = field(default_factory=AttachmentConfig)
    
    # API Keys from environment
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    regs_api_key: Optional[str] = field(default_factory=lambda: os.getenv("REGS_API_KEY"))


# Global config instance
config = Config()