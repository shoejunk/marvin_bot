#!/usr/bin/env python3
"""
action_processor.py - Processes actions extracted from AI responses.
Handles execution of various actions like controlling lights, music, files, etc.
"""

import os
import logging
import json
import asyncio
import subprocess
import datetime
from typing import List, Dict, Any, Optional
from datetime import timedelta

# Import the logger configuration
from logger_config import get_logger
from personalities import get_personality
from settings_manager import get_active_personality
from home_assistant_handler import HomeAssistantHandler
from settings_manager import get_active_personality

# Get a logger for this module
logger = get_logger(__name__)

class ActionProcessor:
    def __init__(self, 
                 spotify_client, 
                 file_ops, 
                 display, 
                 speak_function, 
                 update_history_function,
                 browser=None,
                 voice_processor=None,
                 add_to_speech_queue_function=None):
        """
        Initialize the ActionProcessor with required dependencies.
        
        Args:
            spotify_client: Client for Spotify integration
            file_ops: File operations manager
            display: Display interface for UI updates
            speak_function: Function to speak text responses
            update_history_function: Function to update conversation history
            browser: Browser instance for web browsing (optional)
            voice_processor: VoiceProcessor instance for coordinating wake word settings (optional)
            add_to_speech_queue_function: Function to add text to speech queue (optional)
        """
        self.spotify_client = spotify_client
        self.file_ops = file_ops
        self.display = display
        self.speak = speak_function
        self.update_history = update_history_function
        self.browser = browser
        self.timer_counter = 0
        self.voice_processor = voice_processor
        self.add_to_speech_queue = add_to_speech_queue_function
        
        # Initialize Home Assistant handler
        from home_assistant_handler import HomeAssistantHandler
        self.home_assistant = HomeAssistantHandler()
        
        # Settings management
        self.wake_word_required = True
        
    def set_wake_word_required(self, required: bool):
        """Set whether wake word is required."""
        self.wake_word_required = required
        # Update the voice processor if it exists
        if self.voice_processor:
            self.voice_processor.set_wake_word_required(required)
            
    def get_wake_word_required(self):
        """Get whether wake word is required."""
        return self.wake_word_required
        
    async def process_actions(self, actions: List[Dict[str, Any]], update_setting_function=None):
        """
        Process a list of actions from the AI response.
        
        Args:
            actions: List of action dictionaries with name and parameters
            update_setting_function: Function to update persistent settings (optional)
        """
        active_personality = get_active_personality()
        
        if not actions:
            logger.debug("No actions to process")
            return
            
        for action in actions:
            action_name = action.get('name', '')
            params = action.get('parameters', [])
            
            logger.info(f"Processing action: {action_name} with parameters: {params}")
            
            try:
                # Handle wake word toggle actions
                if action_name == 'wake_word_off':
                    self.set_wake_word_required(False)
                    if update_setting_function:
                        update_setting_function("wake_word_required", False)
                    await self.speak_text("Wake word requirement turned off. You can now speak to me directly.", personality_name=active_personality)
                    logger.info("Wake word requirement turned OFF")
                    
                elif action_name == 'wake_word_on':
                    self.set_wake_word_required(True)
                    if update_setting_function:
                        update_setting_function("wake_word_required", True)
                    await self.speak_text("Wake word requirement turned on. Please start your requests with my name.", personality_name=active_personality)
                    logger.info("Wake word requirement turned ON")
                
                # Handle music control actions
                elif action_name == "play_song":
                    song_name = params[0] if params else ''
                    if song_name:
                        self.spotify_client.play_track(song_name)
                        
                elif action_name == "play_music":
                    song_or_artist = params[0] if params else ''
                    if song_or_artist:
                        self.spotify_client.play_music(song_or_artist)
                        
                elif action_name == "play_playlist":
                    playlist_name = params[0] if params else ''
                    if playlist_name:
                        self.spotify_client.play_playlist(playlist_name)
                        
                elif action_name == "pause_music":
                    self.spotify_client.pause_music()
                    
                elif action_name == "unpause_music" or action_name == "resume_music":
                    self.spotify_client.resume_music()
                    
                elif action_name == "stop_music":
                    self.spotify_client.stop_music()
                    
                elif action_name == "next_track":
                    self.spotify_client.next_track()
                    
                elif action_name == "previous_track":
                    self.spotify_client.previous_track()
                    
                elif action_name == "volume_up":
                    increment = int(params[0]) if params and params[0].isdigit() else 10
                    self.spotify_client.volume_up(increment)
                    
                elif action_name == "volume_down":
                    decrement = int(params[0]) if params and params[0].isdigit() else 10
                    self.spotify_client.volume_down(decrement)
                    
                elif action_name == "adjust_volume":
                    level = params[0] if params else '50'
                    self.spotify_client.adjust_volume(level)
                    
                # Handle system actions
                elif action_name == "reboot":
                    logger.info("Rebooting Marvin...")
                    bat_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_marvin.bat"))
                    logger.info(f"Running batch file: {bat_path}")
                    subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    os._exit(0)
                    
                elif action_name == 'set_timer' or action_name == 'start_timer':
                    duration = params[0] if params else ''
                    if duration:
                        # Replace underscores with spaces if present
                        duration = duration.replace('_', ' ')
                        logger.info(f"Setting timer with cleaned duration: '{duration}'")
                        asyncio.create_task(self.set_timer(duration))
                        
                elif action_name == 'stop_timer':
                    await self.stop_timer()
                    
                elif action_name == 'shut_down':
                    active_personality = get_active_personality()
                    await self.speak_text('Shutting down Marvin', personality_name=active_personality)
                    logger.info('Shutting down Marvin...')
                    # Terminate the application
                    os._exit(0)
                    
                elif action_name == 'get_time':
                    await self._handle_get_time()
                    
                # Handle Home Assistant actions
                elif action_name == 'list_climate_devices':
                    await self._handle_list_climate_devices()
                    
                elif action_name == 'get_smart_devices':
                    await self._handle_get_smart_devices()
                    
                elif action_name == 'get_weather':
                    await self._handle_get_weather(params)
                    
                elif action_name == 'control_entity':
                    await self._handle_control_entity(params)
                    
                # File operation actions
                elif action_name == 'read_file':
                    await self._handle_read_file(params)
                    
                elif action_name == 'write_file':
                    await self._handle_write_file(params)
                    
                elif action_name == 'list_files':
                    await self._handle_list_files(params)
                    
                elif action_name == 'delete_file':
                    await self._handle_delete_file(params)
                    
                elif action_name == 'append_to_file':
                    await self._handle_append_to_file(params)
                    
                elif action_name == 'edit_file':
                    await self._handle_edit_file(params)
                    
                elif action_name == 'create_directory':
                    await self._handle_create_directory(params)
                    
                elif action_name == 'copy_file':
                    await self._handle_copy_file(params)
                    
                elif action_name == 'move_file':
                    await self._handle_move_file(params)
                    
                elif action_name == 'search_files':
                    await self._handle_search_files(params)
                    
                elif action_name == 'dictate':
                    from dictate import handle_dictate
                    dictate_text = params[0] if params else ""
                    handle_dictate(dictate_text)
                    
                elif action_name == 'write_code':
                    await self._handle_write_code(params)
                    
                # Browser use action
                elif action_name == 'browse_internet':
                    await self._handle_browse_internet(params)
                    
                else:
                    logger.warning(f"Unknown action: {action_name}")
                    self.display.add_conversation(f"Unknown action: {action_name}")
            
            except Exception as e:
                logger.error(f"Error processing action: {e}")
                self.display.add_conversation(f"Error processing action: {e}")
        
        return None  # No special signal

    # File operation handlers
    async def _handle_read_file(self, params):
        """Handle reading a file and speaking its contents."""
        active_personality = get_active_personality()
        if not params or len(params) < 1:
            await self.speak_text("I need a filename to read.", personality_name=active_personality)
            return
            
        filename = params[0]
        try:
            content = self.file_ops.read_file(filename)
            if content:
                # Add to conversation display
                self.display.add_conversation(f"Contents of {filename}:\n{content}", speaker='assistant')
                
                # Update history with full results
                self.update_history(f"Contents of {filename}:\n{content}", "")
                
                # Speak a confirmation
                await self.speak_text(f"Here's the content of {filename}", personality_name=active_personality)
            else:
                error_message = f"File {filename} is empty or does not exist."
                self.display.add_conversation(f"❌ {error_message}", speaker='assistant')
                self.update_history(f"❌ {error_message}", "")
                await self.speak_text(error_message, personality_name=active_personality)
        except Exception as e:
            error_message = f"Error reading file {filename}: {e}"
            logger.error(error_message)
            self.display.add_conversation(f"❌ {error_message}", speaker='assistant')
            self.update_history(f"❌ {error_message}", "")
            await self.speak_text(f"I encountered an error reading {filename}.", personality_name=active_personality)

    async def _handle_write_file(self, params):
        """Handle writing content to a file."""
        active_personality = get_active_personality()
        if not params or len(params) < 2:
            await self.speak_text("I need a filename and content to write.", personality_name=active_personality)
            return
            
        filename = params[0]
        content = params[1]
        
        try:
            self.file_ops.write_file(filename, content)
            success_message = f"Successfully wrote to {filename}."
            self.display.add_conversation(success_message, speaker='assistant')
            self.update_history(success_message, "")
            await self.speak_text(success_message, personality_name=active_personality)
        except Exception as e:
            error_message = f"Error writing to file {filename}: {e}"
            logger.error(error_message)
            self.display.add_conversation(f"❌ {error_message}", speaker='assistant')
            self.update_history(f"❌ {error_message}", "")
            await self.speak_text(f"I encountered an error writing to {filename}.", personality_name=active_personality)

    async def _handle_list_files(self, params):
        active_personality = get_active_personality()
        subdirectory = params[0] if params else ""
        files = self.file_ops.list_files(subdirectory)
        if files:
            files_str = ", ".join(files)
            await self.speak_text(f"Files in {subdirectory or 'artifacts directory'}: {files_str}", personality_name=active_personality)
            self.update_history(f"Files in {subdirectory or 'artifacts directory'}: {files_str}", "")
        else:
            await self.speak_text(f"No files found in {subdirectory or 'artifacts directory'}", personality_name=active_personality)
            self.update_history(f"No files found in {subdirectory or 'artifacts directory'}", "")

    async def _handle_delete_file(self, params):
        active_personality = get_active_personality()
        filename = params[0] if params else None
        if filename:
            success = self.file_ops.delete_file(filename)
            if success:
                await self.speak_text(f"Successfully deleted file {filename}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to delete file {filename}", personality_name=active_personality)
        else:
            await self.speak_text("No filename specified for deletion", personality_name=active_personality)

    async def _handle_append_to_file(self, params):
        active_personality = get_active_personality()
        if len(params) >= 2:
            filename = params[0]
            content = params[1]
            # Handle create_if_missing parameter which could be a boolean or string
            if len(params) <= 2:
                create_if_missing = True
            else:
                # Check if it's already a boolean
                if isinstance(params[2], bool):
                    create_if_missing = params[2]
                # If it's a string, convert to boolean
                elif isinstance(params[2], str):
                    create_if_missing = params[2].lower() == 'true'
                else:
                    # Default to True for any other case
                    create_if_missing = True
                    
            success = self.file_ops.append_to_file(filename, content, create_if_missing)
            if success:
                await self.speak_text(f"Successfully appended to file {filename}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to append to file {filename}", personality_name=active_personality)
        else:
            await self.speak_text("Insufficient parameters for appending to a file", personality_name=active_personality)

    async def _handle_edit_file(self, params):
        active_personality = get_active_personality()
        if len(params) >= 3:
            filename = params[0]
            find_text = params[1]
            replace_text = params[2]
            success = self.file_ops.edit_file(filename, find_text, replace_text)
            if success:
                await self.speak_text(f"Successfully edited file {filename}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to edit file {filename}", personality_name=active_personality)
        else:
            await self.speak_text("Insufficient parameters for editing a file", personality_name=active_personality)

    async def _handle_create_directory(self, params):
        active_personality = get_active_personality()
        directory_name = params[0] if params else None
        if directory_name:
            success = self.file_ops.create_directory(directory_name)
            if success:
                await self.speak_text(f"Successfully created directory {directory_name}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to create directory {directory_name}", personality_name=active_personality)
        else:
            await self.speak_text("No directory name specified for creation", personality_name=active_personality)

    async def _handle_copy_file(self, params):
        active_personality = get_active_personality()
        if len(params) >= 2:
            source = params[0]
            destination = params[1]
            success = self.file_ops.copy_file(source, destination)
            if success:
                await self.speak_text(f"Successfully copied file from {source} to {destination}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to copy file from {source} to {destination}", personality_name=active_personality)
        else:
            await self.speak_text("Insufficient parameters for copying a file", personality_name=active_personality)

    async def _handle_move_file(self, params):
        active_personality = get_active_personality()
        if len(params) >= 2:
            source = params[0]
            destination = params[1]
            success = self.file_ops.move_file(source, destination)
            if success:
                await self.speak_text(f"Successfully moved file from {source} to {destination}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to move file from {source} to {destination}", personality_name=active_personality)
        else:
            await self.speak_text("Insufficient parameters for moving a file", personality_name=active_personality)

    async def _handle_search_files(self, params):
        active_personality = get_active_personality()
        if len(params) >= 1:
            search_text = params[0]
            subdirectory = params[1] if len(params) > 1 else ""
            results = self.file_ops.search_files(search_text, subdirectory)
            if results:
                results_str = ", ".join(results)
                await self.speak_text(f"Found {len(results)} files containing '{search_text}': {results_str}", personality_name=active_personality)
                self.update_history(f"Files containing '{search_text}': {results_str}", "")
            else:
                await self.speak_text(f"No files found containing '{search_text}'", personality_name=active_personality)
                self.update_history(f"No files found containing '{search_text}'", "")
        else:
            await self.speak_text("No search text specified", personality_name=active_personality)

    async def _handle_write_code(self, params):
        active_personality = get_active_personality()
        if len(params) >= 2:
            filename = params[0]
            code_content = params[1]
            success = self.file_ops.write_file(filename, code_content, True)
            if success:
                await self.speak_text(f"Successfully wrote code to file {filename}", personality_name=active_personality)
            else:
                await self.speak_text(f"Failed to write code to file {filename}", personality_name=active_personality)
        else:
            await self.speak_text("Insufficient parameters for writing code", personality_name=active_personality)

    async def _handle_browse_internet(self, params):
        active_personality = get_active_personality()
        if not self.browser:
            await self.speak_text("Browser functionality is not available", personality_name=active_personality)
            return
            
        query = params[0] if params else None
        if query:
            self.display.add_conversation(f"Browsing the internet for: {query}", speaker='assistant')
            self.update_history(f"Browsing the internet for: {query}", "")
            try:
                # Set up a custom log handler to capture the browser_use agent's output
                class BrowserUseLogHandler(logging.Handler):
                    def __init__(self):
                        super().__init__()
                        self.result = None
                    
                    def emit(self, record):
                        if record.name == 'browser_use.agent.service' and 'Result:' in record.getMessage():
                            # Extract the result from the log message
                            result_msg = record.getMessage()
                            if '\U0001f4c4 Result:' in result_msg:
                                self.result = result_msg.split('\U0001f4c4 Result:')[1].strip()
                            elif 'Result:' in result_msg:
                                self.result = result_msg.split('Result:')[1].strip()
                
                # Add the custom log handler
                browser_log_handler = BrowserUseLogHandler()
                browser_log_handler.setLevel(logging.INFO)
                logging.getLogger('browser_use').addHandler(browser_log_handler)
                
                # Import required modules
                from browser_use import Agent
                from langchain_openai import ChatOpenAI
                
                # Create and run the browser agent
                await self.browser.close()
                agent = Agent(
                    task=query,
                    llm=ChatOpenAI(model="gpt-4o"),
                    browser=self.browser,
                )
                await agent.run()
                
                # Remove the custom log handler
                logging.getLogger('browser_use').removeHandler(browser_log_handler)
                
                # Check if we captured a result
                if browser_log_handler.result:
                    result_text = browser_log_handler.result
                    
                    # Send the result to the LLM for summarization
                    from llm import get_ai_response
                    summarization_prompt = f"Below are the results from a web search. Please provide a concise summary of these results, while preserving the key information:\n\n{result_text}"
                    summary_response = get_ai_response(summarization_prompt, active_personality)
                    
                    try:
                        # Parse the JSON response for the summary
                        summary_data = json.loads(summary_response)
                        summary_text = summary_data.get("response", "")
                        
                        # Display the full results in the UI
                        self.display.add_conversation(result_text, speaker='assistant')
                        
                        # Update history with full results
                        self.update_history(result_text, "")
                        
                        # Speak the summarized version
                        await self.speak_text(summary_text, personality_name=active_personality)
                    except json.JSONDecodeError:
                        # Fallback if JSON parsing fails
                        logger.error("Failed to parse summary response as JSON")
                        self.display.add_conversation(result_text, speaker='assistant')
                        self.update_history(result_text, "")
                        await self.speak_text("I found some information, but couldn't properly format it.", personality_name=active_personality)
                else:
                    # Default message if we couldn't capture a result
                    self.display.add_conversation("Browser search complete, but couldn't extract specific results.", speaker='assistant')
                    self.update_history("Browser search complete, but couldn't extract specific results.", "")
                    await self.speak_text("Browser search complete, but I couldn't extract specific results.", personality_name=active_personality)
            except Exception as e:
                error_message = f"Error during browser search: {e}"
                logger.error(error_message)
                self.display.add_conversation(f"❌ {error_message}", speaker='assistant')
                self.update_history(f"❌ {error_message}", "")
                await self.speak_text("I encountered an error while browsing the internet.", personality_name=active_personality)
        else:
            await self.speak_text("No search query specified for browsing the internet.", personality_name=active_personality)
            self.display.add_conversation("No search query specified for browsing the internet.", speaker='assistant')
            self.update_history("No search query specified for browsing the internet.", "")

    # Home Assistant handlers
    async def _handle_list_climate_devices(self):
        active_personality = get_active_personality()
        if self.home_assistant:
            await self.home_assistant.handle_action('list_climate_devices', {})
        else:
            await self.speak_text("Home Assistant is not configured.", personality_name=active_personality)
            
    async def _handle_get_smart_devices(self):
        active_personality = get_active_personality()
        if self.home_assistant:
            await self.home_assistant.handle_action('get_smart_devices', {})
        else:
            await self.speak_text("Home Assistant is not configured.", personality_name=active_personality)
            
    async def _handle_get_weather(self, params):
        """Handle getting weather information from Home Assistant.
        
        Args:
            params: List of parameters [entity_id (optional)]
        """
        active_personality = get_active_personality()
        if self.home_assistant:
            # Extract entity_id if provided
            entity_id = params[0] if params and params[0] else None
            
            # Create parameters dictionary
            params_dict = {}
            if entity_id:
                params_dict['entity_id'] = entity_id
                
            # Call Home Assistant handler
            await self.home_assistant.handle_action('get_weather', params_dict)
        else:
            await self.speak_text("Home Assistant is not configured.", personality_name=active_personality)
            
    async def _handle_control_entity(self, params):
        """Handle controlling any entity in Home Assistant.
        
        Args:
            params: List of parameters [entity_id, service, param1_name, param1_value, ...]
        """
        active_personality = get_active_personality()
        if not self.home_assistant:
            await self.speak_text("Home Assistant is not configured.", personality_name=active_personality)
            return
            
        if len(params) < 2:
            await self.speak_text("Not enough parameters for control_entity action. Need at least entity_id and service.", 
                            personality_name=active_personality)
            return
            
        # Extract entity_id and service
        entity_id = params[0]
        service = params[1]
        
        # Create parameters dictionary
        params_dict = {
            'entity_id': entity_id,
            'service': service
        }
        
        # Add any additional parameters (name-value pairs)
        if len(params) > 2:
            # Parameters should be in pairs (name, value)
            for i in range(2, len(params), 2):
                if i + 1 < len(params):  # Make sure we have a value for this parameter
                    param_name = params[i]
                    param_value = params[i + 1]
                    
                    # Try to convert numeric values
                    try:
                        if isinstance(param_value, str) and param_value.replace('.', '', 1).isdigit():
                            if '.' in param_value:
                                param_value = float(param_value)
                            else:
                                param_value = int(param_value)
                    except (ValueError, TypeError):
                        pass  # Keep as string if conversion fails
                        
                    params_dict[param_name] = param_value
        
        # Call Home Assistant handler with timeout protection
        try:
            import asyncio
            # Create a task for the action and wait for it with a timeout
            action_task = asyncio.create_task(self.home_assistant.handle_action('control_entity', params_dict))
            # Wait for 20 seconds max (longer than the handler's internal timeout)
            result = await asyncio.wait_for(action_task, timeout=20)
            
            # Check if the action was successful
            if not result.get('success', False):
                error_message = result.get('message', 'Unknown error')
                logger.error(f"Home Assistant control_entity action failed: {error_message}")
                await self.speak_text(f"I had trouble controlling {entity_id}. {error_message}", 
                                personality_name=active_personality)
        except asyncio.TimeoutError:
            logger.error(f"Timeout while executing Home Assistant control_entity action for {entity_id}")
            await self.speak_text(f"I'm sorry, the request to control {entity_id} timed out. Please try again later.", 
                            personality_name=active_personality)
        except Exception as e:
            logger.error(f"Error executing Home Assistant control_entity action: {str(e)}")
            await self.speak_text(f"I encountered an error while trying to control {entity_id}: {str(e)}", 
                            personality_name=active_personality)
        
    # Timer functions
    async def set_timer(self, duration: str):
        """Set a timer for the specified duration."""
        active_personality = get_active_personality()
        try:
            logger.debug(f"Setting timer with duration: '{duration}'")
            
            # First, check if the duration is already in the format "X unit"
            duration_parts = duration.split()
            logger.debug(f"Duration parts: {duration_parts}")
            
            if len(duration_parts) == 2:
                # Format is already "X unit"
                try:
                    value = int(duration_parts[0])
                    unit_input = duration_parts[1].lower()
                    logger.debug(f"Parsed as two parts: value={value}, unit={unit_input}")
                except ValueError as e:
                    logger.error(f"Error parsing value: {e}")
                    await self.speak_text('Invalid timer format. The value must be a number.', personality_name=active_personality)
                    return
            else:
                # Try to parse the duration as a single value
                # Check if it's just a number (assume seconds)
                try:
                    value = int(duration)
                    unit_input = 'seconds'
                    logger.debug(f"Parsed as single number: {value} {unit_input}")
                except ValueError:
                    # Try to extract number and unit from a string without spaces
                    import re
                    match = re.match(r'(\d+)(\w+)', duration)
                    if match:
                        try:
                            value = int(match.group(1))
                            unit_abbr = match.group(2).lower()
                            unit_input = unit_abbr
                            logger.debug(f"Parsed with regex: value={value}, unit={unit_input}")
                        except ValueError as e:
                            logger.error(f"Error parsing regex match: {e}")
                            await self.speak_text('Invalid timer format. Use format like "5 minutes" or "5m".', personality_name=active_personality)
                            return
                    else:
                        logger.error(f"Could not parse timer format: '{duration}'")
                        await self.speak_text('Invalid timer format. Use format like "5 minutes" or "5m".', personality_name=active_personality)
                        return
            
            # Map any unit format to a standardized format
            unit_map = {
                's': 'second', 'sec': 'second', 'second': 'second', 'seconds': 'second',
                'm': 'minute', 'min': 'minute', 'minute': 'minute', 'minutes': 'minute',
                'h': 'hour', 'hr': 'hour', 'hour': 'hour', 'hours': 'hour'
            }
            
            # Try to map the input unit to a standard unit
            if unit_input in unit_map:
                unit = unit_map[unit_input]
                logger.debug(f"Mapped '{unit_input}' to '{unit}'")
            else:
                logger.error(f"Unknown time unit: '{unit_input}'")
                await self.speak_text(f'Invalid time unit: "{unit_input}". Use seconds, minutes, or hours.', personality_name=active_personality)
                return
                
            # Check if unit is valid (should always be valid after mapping)
            valid_units = ['second', 'minute', 'hour']
            if unit in valid_units:
                # Convert to seconds
                if unit == 'minute':
                    seconds_value = value * 60
                elif unit == 'hour':
                    seconds_value = value * 3600
                else:  # seconds
                    seconds_value = value
                    
                # For display purposes, use the original format
                display_unit = unit + ('s' if value != 1 else '')
                
                logger.debug(f"Setting timer for {value} {display_unit} ({seconds_value} seconds)")
                timer_name = f"timer_{self.timer_counter}"
                self.timer_counter += 1
                self.display.add_timer(timer_name, timedelta(seconds=seconds_value))
                await asyncio.sleep(seconds_value)
                self.display.remove_timer(timer_name)
                
                # Use our helper method to speak the text
                await self.speak_text('Timer complete!', personality_name=active_personality)
            else:
                # This should never happen with our mapping
                logger.error(f"Unexpected error: Unit '{unit}' not in valid_units after mapping")
                await self.speak_text('Invalid time unit. Use seconds, minutes, or hours.', personality_name=active_personality)
        except Exception as e:
            logger.error(f'Error setting timer: {e}', exc_info=True)
            await self.speak_text('Error setting timer.', personality_name=active_personality)

    async def stop_timer(self):
        """Stop all active timers."""
        # Stop all active timers by removing each one from the display
        active_timers = list(self.display.timers.keys())
        for tname in active_timers:
            self.display.remove_timer(tname)
        logger.info('All timers stopped')
        await self.speak_text('All timers stopped.', personality_name=get_active_personality())
        
    async def _handle_get_time(self):
        """Get the current time and speak it to the user."""
        active_personality = get_active_personality()
        try:
            # Get current time
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            time_message = f"The current time is {time_str} on {date_str}."
            
            # Display and speak the time
            self.display.add_conversation(time_message, speaker='assistant')
            
            # Update history with full results
            self.update_history(time_message, "")
            
            # Speak the time using our helper method
            await self.speak_text(time_message, personality_name=active_personality)
            
        except Exception as e:
            error_message = f"Error getting time: {e}"
            logger.error(error_message)
            self.display.add_conversation(f"❌ {error_message}", speaker='assistant')
            self.update_history(f"❌ {error_message}", "")
            await self.speak_text(f"I encountered an error getting the time.", personality_name=active_personality)

    async def speak_text(self, text, personality_name=None):
        """
        Speak text using the speech queue if available, otherwise use direct speech.
        
        Args:
            text: The text to speak
            personality_name: The personality to use for speaking
        """
        if self.add_to_speech_queue:
            await self.add_to_speech_queue(text, personality_name=personality_name)
        else:
            logger.error("No add_to_speech_queue function provided")

    def get_last_user_input(self):
        """Get the last user input from conversation history"""
        try:
            from conversation_history import get_history
            history = get_history()
            for message in reversed(history):
                if message.get('role') == 'user':
                    return message.get('content', '')
            return ''
        except Exception:
            return ''
