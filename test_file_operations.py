#!/usr/bin/env python3
"""
test_file_operations.py - A simple script to test Marvin's file operations functionality.
This allows testing file operations without requiring voice commands.
"""

import os
import logging
import argparse
from file_operations import FileOperations

# Configure logging
logger = logging.getLogger(__name__)

# Only add handlers if they don't exist already
if not logger.handlers:
    try:
        # Set the logging level
        logger.setLevel(logging.INFO)
        
        # Create a stream handler for console output
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        
        # Try to add file handler only if we can access the file
        log_file = "marvin.log"
        if not os.path.exists(log_file) or os.access(log_file, os.W_OK):
            file_handler = logging.FileHandler(log_file, delay=True)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up complete logging for {__name__}: {e}")

def main():
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Test Marvin\'s file operations functionality')
    
    # Set up subcommands for each file operation
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List files command
    list_parser = subparsers.add_parser('list', help='List files in a directory')
    list_parser.add_argument('--dir', type=str, default='', help='Subdirectory to list')
    
    # Read file command
    read_parser = subparsers.add_parser('read', help='Read a file')
    read_parser.add_argument('filename', type=str, help='File to read')
    
    # Write file command
    write_parser = subparsers.add_parser('write', help='Write to a file')
    write_parser.add_argument('filename', type=str, help='File to write to')
    write_parser.add_argument('content', type=str, help='Content to write')
    write_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing file')
    
    # Append file command
    append_parser = subparsers.add_parser('append', help='Append to a file')
    append_parser.add_argument('filename', type=str, help='File to append to')
    append_parser.add_argument('content', type=str, help='Content to append')
    append_parser.add_argument('--create', action='store_true', help='Create file if missing')
    
    # Edit file command
    edit_parser = subparsers.add_parser('edit', help='Edit a file')
    edit_parser.add_argument('filename', type=str, help='File to edit')
    edit_parser.add_argument('find', type=str, help='Text to find')
    edit_parser.add_argument('replace', type=str, help='Text to replace with')
    
    # Delete file command
    delete_parser = subparsers.add_parser('delete', help='Delete a file')
    delete_parser.add_argument('filename', type=str, help='File to delete')
    
    # Create directory command
    mkdir_parser = subparsers.add_parser('mkdir', help='Create a directory')
    mkdir_parser.add_argument('directory', type=str, help='Directory to create')
    
    # Copy file command
    copy_parser = subparsers.add_parser('copy', help='Copy a file')
    copy_parser.add_argument('source', type=str, help='Source file')
    copy_parser.add_argument('destination', type=str, help='Destination file')
    
    # Move file command
    move_parser = subparsers.add_parser('move', help='Move a file')
    move_parser.add_argument('source', type=str, help='Source file')
    move_parser.add_argument('destination', type=str, help='Destination file')
    
    # Search files command
    search_parser = subparsers.add_parser('search', help='Search files for text')
    search_parser.add_argument('text', type=str, help='Text to search for')
    search_parser.add_argument('--dir', type=str, default='', help='Subdirectory to search in')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize FileOperations
    file_ops = FileOperations()
    
    # Display the artifacts directory
    logger.info(f"Using artifacts directory: {file_ops.artifacts_dir}")
    
    # Execute command based on arguments
    if args.command == 'list':
        files = file_ops.list_files(args.dir)
        if files:
            logger.info(f"Files in directory '{args.dir or 'artifacts'}':")
            for file in files:
                logger.info(f"  - {file}")
        else:
            logger.info(f"No files found in directory '{args.dir or 'artifacts'}'")
    
    elif args.command == 'read':
        content = file_ops.read_file(args.filename)
        if content is not None:
            logger.info(f"Content of '{args.filename}':")
            print("\n---FILE CONTENT BEGIN---")
            print(content)
            print("---FILE CONTENT END---\n")
        else:
            logger.error(f"Could not read file '{args.filename}'")
    
    elif args.command == 'write':
        success = file_ops.write_file(args.filename, args.content, args.overwrite)
        if success:
            logger.info(f"Successfully wrote to file '{args.filename}'")
        else:
            logger.error(f"Failed to write to file '{args.filename}'")
    
    elif args.command == 'append':
        success = file_ops.append_to_file(args.filename, args.content, args.create)
        if success:
            logger.info(f"Successfully appended to file '{args.filename}'")
        else:
            logger.error(f"Failed to append to file '{args.filename}'")
    
    elif args.command == 'edit':
        success = file_ops.edit_file(args.filename, args.find, args.replace)
        if success:
            logger.info(f"Successfully edited file '{args.filename}'")
        else:
            logger.error(f"Failed to edit file '{args.filename}'")
    
    elif args.command == 'delete':
        success = file_ops.delete_file(args.filename)
        if success:
            logger.info(f"Successfully deleted file '{args.filename}'")
        else:
            logger.error(f"Failed to delete file '{args.filename}'")
    
    elif args.command == 'mkdir':
        success = file_ops.create_directory(args.directory)
        if success:
            logger.info(f"Successfully created directory '{args.directory}'")
        else:
            logger.error(f"Failed to create directory '{args.directory}'")
    
    elif args.command == 'copy':
        success = file_ops.copy_file(args.source, args.destination)
        if success:
            logger.info(f"Successfully copied '{args.source}' to '{args.destination}'")
        else:
            logger.error(f"Failed to copy '{args.source}' to '{args.destination}'")
    
    elif args.command == 'move':
        success = file_ops.move_file(args.source, args.destination)
        if success:
            logger.info(f"Successfully moved '{args.source}' to '{args.destination}'")
        else:
            logger.error(f"Failed to move '{args.source}' to '{args.destination}'")
    
    elif args.command == 'search':
        results = file_ops.search_files(args.text, args.dir)
        if results:
            logger.info(f"Files containing '{args.text}':")
            for file in results:
                logger.info(f"  - {file}")
        else:
            logger.info(f"No files containing '{args.text}' found")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()