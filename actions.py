# actions.py

# List of valid actions for the voice assistant.
action_strings = [
    # Existing actions
    'turn_on_light', 'turn_off_light', 'play_song', 'play_playlist', 
    'pause_music', 'unpause_music', 'volume_up', 'volume_down', 
    'reboot', 'set_timer', 'stop_timer', 'shut_down', 'stop_music',
    
    # New file operation actions
    'read_file', 'write_file', 'list_files', 'delete_file', 
    'edit_file', 'append_to_file', 'create_directory', 
    'move_file', 'copy_file', 'search_files'
]