# Marvin File Operations

This module adds file management capabilities to Marvin, allowing it to read, write, edit, and manage files in a dedicated `artifacts` folder.

## Features

- **Safe file operations**: All file operations are restricted to the `artifacts` directory for security
- **Comprehensive file management**: Read, write, edit, delete, copy, and move files
- **Directory support**: Create directories and organize files within them
- **Search capability**: Find files containing specific text
- **Voice command integration**: Use Marvin's voice interface to manage files

## Voice Commands

Here are some examples of voice commands you can use with Marvin:

- "Marvin, create a file called notes.txt with today's shopping list"
- "Hey Marvin, read my notes.txt file"
- "Marvin, list all the files in the artifacts folder"
- "Marvin, delete the file called old_notes.txt"
- "Marvin, search for files containing the word 'important'"
- "Marvin, edit my todo.txt file and replace 'buy milk' with 'buy almond milk'"

## Action Format

When using voice commands, Marvin will parse your request and use the appropriate action tags:

- **Read a file**: `<action>read_file:filename</action>`
- **Write to a file**: `<action>write_file:filename,content,overwrite</action>`
- **List files**: `<action>list_files:subdirectory</action>`
- **Delete a file**: `<action>delete_file:filename</action>`
- **Edit a file**: `<action>edit_file:filename,find_text,replace_text</action>`
- **Append to a file**: `<action>append_to_file:filename,content,create_if_missing</action>`
- **Create a directory**: `<action>create_directory:directory_name</action>`
- **Copy a file**: `<action>copy_file:source,destination</action>`
- **Move a file**: `<action>move_file:source,destination</action>`
- **Search files**: `<action>search_files:search_text,subdirectory</action>`

## Testing File Operations

You can test file operations without using voice commands by using the included `test_file_operations.py` script:

```bash
# List all files in the artifacts directory
python test_file_operations.py list

# Create a new file
python test_file_operations.py write test.txt "This is a test file"

# Read the file's contents
python test_file_operations.py read test.txt

# Append to the file
python test_file_operations.py append test.txt " - appended content"

# Edit the file
python test_file_operations.py edit test.txt "test" "sample"

# Search for files containing text
python test_file_operations.py search "sample"

# Create a directory
python test_file_operations.py mkdir notes

# Copy a file
python test_file_operations.py copy test.txt notes/test_copy.txt

# Move/rename a file
python test_file_operations.py move test.txt renamed_test.txt

# Delete a file
python test_file_operations.py delete renamed_test.txt
```

## Implementation Details

The file operations are implemented in the `file_operations.py` module, which provides a `FileOperations` class that handles all file management tasks.

The module ensures that all file operations are contained within the `artifacts` directory by:
- Validating paths to prevent directory traversal attacks
- Normalizing file paths to ensure consistency
- Providing detailed logging for all operations

## Integration with Marvin

The file operations are integrated with Marvin's main processing loop, which parses voice commands, extracts action tags, and routes them to the appropriate handlers in the `FileOperations` class.

When Marvin processes a file operation, it will:
1. Parse any parameters from the action tag
2. Execute the appropriate file operation method
3. Provide vocal feedback about the result of the operation