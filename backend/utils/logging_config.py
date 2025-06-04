"""
Centralized logging configuration for the pipeline.

This module provides a standardized way to set up logging across all pipeline components.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Union
from datetime import datetime


class PipelineLogger:
    """Centralized logger configuration for the pipeline."""
    
    @staticmethod
    def setup_logger(
        name: str,
        output_dir: Optional[Union[str, Path]] = None,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        include_timestamp: bool = True
    ) -> logging.Logger:
        """
        Set up a logger with both file and console handlers.
        
        Args:
            name: Logger name (usually __name__)
            output_dir: Directory for log files
            log_file: Specific log file name (auto-generated if None)
            level: Logging level
            include_timestamp: Whether to include timestamp in log file name
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Clear existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler (if output directory specified)
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            if log_file is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S') if include_timestamp else ''
                log_file = f"{name.replace('.', '_')}_{timestamp}.log" if timestamp else f"{name.replace('.', '_')}.log"
            
            file_path = output_path / log_file
            file_handler = logging.FileHandler(file_path)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"Logging to file: {file_path}")
        
        return logger
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get an existing logger or create a basic one."""
        return logging.getLogger(name)


def setup_pipeline_logging(output_dir: Optional[Union[str, Path]] = None) -> logging.Logger:
    """
    Convenience function to set up the main pipeline logger.
    
    Args:
        output_dir: Directory for log files
        
    Returns:
        Configured logger for the pipeline
    """
    return PipelineLogger.setup_logger(
        name="pipeline",
        output_dir=output_dir,
        log_file="pipeline.log",
        include_timestamp=False
    )