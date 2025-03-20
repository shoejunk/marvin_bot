# actions.py

# List of valid actions for the voice assistant.
action_strings = [
    'play_song', 'play_playlist', 
    'pause_music', 'unpause_music', 'resume_music', 'volume_up', 'volume_down', 
    'reboot', 'set_timer', 'start_timer', 'stop_timer', 'pause_timer', 'resume_timer', 'shut_down', 'stop_music',
    'read_file', 'write_file', 'list_files', 'delete_file', 
    'edit_file', 'append_to_file', 'create_directory', 
    'move_file', 'copy_file', 'search_files', 'get_time',
    'dictate', 'write_code', 'browse_internet', 'wake_word_off', 'wake_word_on',
    'play_music', 'next_track', 'previous_track', 'adjust_volume', 'change_personality',
    'list_climate_devices', 'get_smart_devices', 'get_weather', 'control_entity',
    'get_thermostat', 'set_thermostat', 'open_app', 'list_apps'
]

# List of actions that should be muted in the reply
mute_reply_actions = [
    "get_time",
    "pause_timer",
    "resume_timer",
    "read_file",
    "write_file",
    "list_files",
    "delete_file",
    "edit_file",
    "append_to_file",
    "create_directory",
    "move_file",
    "copy_file",
    "search_files",
    "browse_internet",
    "wake_word_off",
    "wake_word_on",
    "change_personality",
    "open_app",
    "list_apps"
]
