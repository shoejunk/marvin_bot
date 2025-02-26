#!/usr/bin/env python3
"""
file_operations.py - Provides file reading, writing, and editing functionality for Marvin.
All file operations are restricted to a dedicated 'artifacts' folder for security.
"""

import os
import logging
import time
import shutil
from typing import List, Optional, Dict, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileOperations:
    def __init__(self, base_dir: str = None):
        """
        Initialize the FileOperations class with the artifacts directory.
        
        Args:
            base_dir (str, optional): Base directory for the artifacts folder. 
                                     If None, uses the script's directory.
        """
        # Determine the base directory
        if base_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Define and create the artifacts directory if it doesn't exist
        self.artifacts_dir = os.path.join(base_dir, "artifacts")
        self._ensure_artifacts_dir()
        
        logger.info(f"FileOperations initialized with artifacts directory: {self.artifacts_dir}")

    def _ensure_artifacts_dir(self) -> None:
        """Ensure the artifacts directory exists."""
        if not os.path.exists(self.artifacts_dir):
            os.makedirs(self.artifacts_dir)
            logger.info(f"Created artifacts directory at {self.artifacts_dir}")

    def _validate_path(self, filename: str) -> str:
        """
        Validate that the filename doesn't contain path traversal attempts.
        Returns the full path if valid, raises an exception otherwise.
        
        Args:
            filename (str): The filename to validate
            
        Returns:
            str: The full validated path
            
        Raises:
            ValueError: If the path attempts to escape the artifacts directory
        """
        # Remove any path separators from the beginning and normalize
        clean_filename = os.path.normpath(filename.lstrip('/\\'))
        
        # Prevent any directory traversal
        if '..' in clean_filename or clean_filename.startswith('/') or clean_filename.startswith('\\'):
            raise ValueError(f"Invalid filename: {filename}. Path traversal not allowed.")
        
        # Get the full path
        full_path = os.path.join(self.artifacts_dir, clean_filename)
        
        # Ensure the path is still within the artifacts directory
        if not os.path.abspath(full_path).startswith(os.path.abspath(self.artifacts_dir)):
            raise ValueError(f"Invalid path: {full_path}. Must be within artifacts directory.")
            
        return full_path

    def list_files(self, subdirectory: str = "") -> List[str]:
        """
        List all files in the artifacts directory or a subdirectory.
        
        Args:
            subdirectory (str, optional): Subdirectory within artifacts to list
            
        Returns:
            List[str]: List of filenames
        """
        dir_path = self.artifacts_dir
        if subdirectory:
            dir_path = self._validate_path(subdirectory)
            if not os.path.isdir(dir_path):
                logger.warning(f"Directory does not exist: {subdirectory}")
                return []
        
        try:
            files = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    # Return paths relative to artifacts directory
                    rel_path = os.path.relpath(item_path, self.artifacts_dir)
                    files.append(rel_path)
            return files
        except Exception as e:
            logger.error(f"Error listing files in {dir_path}: {str(e)}")
            return []

    def read_file(self, filename: str) -> Optional[str]:
        """
        Read the contents of a file in the artifacts directory.
        
        Args:
            filename (str): Name of the file to read
            
        Returns:
            Optional[str]: File contents as a string, or None if the file doesn't exist
        """
        try:
            full_path = self._validate_path(filename)
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {filename}")
                return None
                
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
                logger.info(f"Read file: {filename} ({len(content)} bytes)")
                return content
        except Exception as e:
            logger.error(f"Error reading file {filename}: {str(e)}")
            return None

    def write_file(self, filename: str, content: str, overwrite: bool = True) -> bool:
        """
        Write content to a file in the artifacts directory.
        
        Args:
            filename (str): Name of the file to write
            content (str): Content to write to the file
            overwrite (bool, optional): Whether to overwrite existing files
            
        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            full_path = self._validate_path(filename)
            
            # Create any necessary directories
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Check if file exists and overwrite flag
            if os.path.exists(full_path) and not overwrite:
                logger.warning(f"File exists and overwrite is False: {filename}")
                return False
                
            with open(full_path, 'w', encoding='utf-8') as file:
                file.write(content)
                logger.info(f"Wrote {len(content)} bytes to file: {filename}")
                return True
        except Exception as e:
            logger.error(f"Error writing to file {filename}: {str(e)}")
            return False

    def append_to_file(self, filename: str, content: str, create_if_missing: bool = True) -> bool:
        """
        Append content to a file in the artifacts directory.
        
        Args:
            filename (str): Name of the file to append to
            content (str): Content to append
            create_if_missing (bool, optional): Whether to create the file if it doesn't exist
            
        Returns:
            bool: True if append was successful, False otherwise
        """
        try:
            full_path = self._validate_path(filename)
            
            # Check if file exists
            if not os.path.exists(full_path):
                if create_if_missing:
                    # Create any necessary directories
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                else:
                    logger.warning(f"File does not exist and create_if_missing is False: {filename}")
                    return False
                    
            with open(full_path, 'a', encoding='utf-8') as file:
                file.write(content)
                logger.info(f"Appended {len(content)} bytes to file: {filename}")
                return True
        except Exception as e:
            logger.error(f"Error appending to file {filename}: {str(e)}")
            return False

    def edit_file(self, filename: str, find_text: str, replace_text: str) -> bool:
        """
        Edit a file by replacing all occurrences of find_text with replace_text.
        
        Args:
            filename (str): Name of the file to edit
            find_text (str): Text to find
            replace_text (str): Text to replace it with
            
        Returns:
            bool: True if the edit was successful, False otherwise
        """
        try:
            content = self.read_file(filename)
            if content is None:
                return False
                
            new_content = content.replace(find_text, replace_text)
            if content == new_content:
                logger.info(f"No changes made to file: {filename}")
                return True  # No changes needed, but not a failure
                
            return self.write_file(filename, new_content)
        except Exception as e:
            logger.error(f"Error editing file {filename}: {str(e)}")
            return False

    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from the artifacts directory.
        
        Args:
            filename (str): Name of the file to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            full_path = self._validate_path(filename)
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {filename}")
                return False
                
            os.remove(full_path)
            logger.info(f"Deleted file: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return False

    def create_directory(self, directory: str) -> bool:
        """
        Create a directory within the artifacts directory.
        
        Args:
            directory (str): Directory to create
            
        Returns:
            bool: True if creation was successful, False otherwise
        """
        try:
            full_path = self._validate_path(directory)
            os.makedirs(full_path, exist_ok=True)
            logger.info(f"Created directory: {directory}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {str(e)}")
            return False

    def copy_file(self, source: str, destination: str) -> bool:
        """
        Copy a file within the artifacts directory.
        
        Args:
            source (str): Source filename
            destination (str): Destination filename
            
        Returns:
            bool: True if copy was successful, False otherwise
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)
            
            if not os.path.exists(source_path):
                logger.warning(f"Source file does not exist: {source}")
                return False
                
            # Create destination directory if needed
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
            shutil.copy2(source_path, dest_path)
            logger.info(f"Copied file from {source} to {destination}")
            return True
        except Exception as e:
            logger.error(f"Error copying file from {source} to {destination}: {str(e)}")
            return False

    def move_file(self, source: str, destination: str) -> bool:
        """
        Move a file within the artifacts directory.
        
        Args:
            source (str): Source filename
            destination (str): Destination filename
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        try:
            source_path = self._validate_path(source)
            dest_path = self._validate_path(destination)
            
            if not os.path.exists(source_path):
                logger.warning(f"Source file does not exist: {source}")
                return False
                
            # Create destination directory if needed
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
            shutil.move(source_path, dest_path)
            logger.info(f"Moved file from {source} to {destination}")
            return True
        except Exception as e:
            logger.error(f"Error moving file from {source} to {destination}: {str(e)}")
            return False

    def get_file_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            filename (str): Name of the file
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with file info or None if file doesn't exist
        """
        try:
            full_path = self._validate_path(filename)
            
            if not os.path.exists(full_path):
                logger.warning(f"File does not exist: {filename}")
                return None
                
            stat_info = os.stat(full_path)
            
            return {
                'name': os.path.basename(full_path),
                'path': os.path.relpath(full_path, self.artifacts_dir),
                'size': stat_info.st_size,
                'created': time.ctime(stat_info.st_ctime),
                'modified': time.ctime(stat_info.st_mtime),
                'is_directory': os.path.isdir(full_path)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {filename}: {str(e)}")
            return None

    def search_files(self, search_text: str, subdirectory: str = "") -> List[str]:
        """
        Search for files containing the given text.
        
        Args:
            search_text (str): Text to search for
            subdirectory (str, optional): Subdirectory to search in
            
        Returns:
            List[str]: List of filenames containing the search text
        """
        results = []
        
        try:
            search_dir = self.artifacts_dir
            if subdirectory:
                search_dir = self._validate_path(subdirectory)
                if not os.path.isdir(search_dir):
                    logger.warning(f"Search directory does not exist: {subdirectory}")
                    return []
            
            for file in self.list_files(subdirectory):
                content = self.read_file(file)
                if content and search_text in content:
                    results.append(file)
                    
            logger.info(f"Found {len(results)} files containing '{search_text}'")
            return results
        except Exception as e:
            logger.error(f"Error searching for '{search_text}': {str(e)}")
            return []