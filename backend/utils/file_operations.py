"""
File operation utilities for the pipeline.

This module provides standardized file operations with proper error handling
and logging.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from .exceptions import FileOperationError
from .logging_config import PipelineLogger

logger = PipelineLogger.get_logger(__name__)


class FileManager:
    """Centralized file operations manager."""
    
    @staticmethod
    def ensure_directory(path: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to create
            
        Returns:
            Path object for the directory
            
        Raises:
            FileOperationError: If directory creation fails
        """
        try:
            dir_path = Path(path)
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {dir_path}")
            return dir_path
        except Exception as e:
            raise FileOperationError(
                f"Failed to create directory: {path}",
                file_path=str(path),
                operation="mkdir",
                context={"error": str(e)}
            )
    
    @staticmethod
    def load_json(file_path: Union[str, Path], required: bool = True) -> Optional[Dict[str, Any]]:
        """
        Load JSON data from a file.
        
        Args:
            file_path: Path to JSON file
            required: Whether the file is required to exist
            
        Returns:
            Loaded JSON data or None if file doesn't exist and not required
            
        Raises:
            FileOperationError: If file loading fails
        """
        path = Path(file_path)
        
        if not path.exists():
            if required:
                raise FileOperationError(
                    f"Required file not found: {file_path}",
                    file_path=str(file_path),
                    operation="read"
                )
            return None
        
        try:
            with path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug(f"JSON loaded successfully: {file_path}")
            return data
        except json.JSONDecodeError as e:
            raise FileOperationError(
                f"Invalid JSON in file: {file_path}",
                file_path=str(file_path),
                operation="json_decode",
                context={"error": str(e), "line": e.lineno, "column": e.colno}
            )
        except Exception as e:
            raise FileOperationError(
                f"Failed to read file: {file_path}",
                file_path=str(file_path),
                operation="read",
                context={"error": str(e)}
            )
    
    @staticmethod
    def save_json(
        data: Any,
        file_path: Union[str, Path],
        indent: int = 2,
        backup: bool = False
    ) -> None:
        """
        Save data to a JSON file.
        
        Args:
            data: Data to save
            file_path: Path to save file
            indent: JSON indentation
            backup: Whether to create a backup if file exists
            
        Raises:
            FileOperationError: If file saving fails
        """
        path = Path(file_path)
        
        # Create backup if requested and file exists
        if backup and path.exists():
            backup_path = path.with_suffix(f'.{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
            try:
                path.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
        
        # Ensure parent directory exists
        FileManager.ensure_directory(path.parent)
        
        try:
            with path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.debug(f"JSON saved successfully: {file_path}")
        except Exception as e:
            raise FileOperationError(
                f"Failed to save file: {file_path}",
                file_path=str(file_path),
                operation="write",
                context={"error": str(e)}
            )
    
    @staticmethod
    def get_latest_timestamped_dir(base_dir: Union[str, Path], pattern: str = "results_*") -> Optional[Path]:
        """
        Find the most recent timestamped directory.
        
        Args:
            base_dir: Base directory to search in
            pattern: Glob pattern for directories
            
        Returns:
            Path to most recent directory or None if none found
        """
        base_path = Path(base_dir)
        if not base_path.exists():
            return None
        
        try:
            dirs = list(base_path.glob(pattern))
            if not dirs:
                return None
            
            # Sort by creation time (newest first)
            dirs.sort(key=lambda p: p.stat().st_ctime, reverse=True)
            latest = dirs[0]
            logger.debug(f"Latest timestamped directory: {latest}")
            return latest
        except Exception as e:
            logger.warning(f"Error finding latest directory: {e}")
            return None
    
    @staticmethod
    def create_timestamped_dir(base_dir: Union[str, Path], prefix: str = "results") -> Path:
        """
        Create a new timestamped directory.
        
        Args:
            base_dir: Base directory for new directory
            prefix: Directory name prefix
            
        Returns:
            Path to created directory
            
        Raises:
            FileOperationError: If directory creation fails
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = f"{prefix}_{timestamp}"
        dir_path = Path(base_dir) / dir_name
        
        return FileManager.ensure_directory(dir_path)