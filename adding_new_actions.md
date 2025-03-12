# Adding a New Action to Marvin Bot

This guide provides concise instructions for adding a new action to Marvin.

## Step 1: Add the action to `actions.py`
Add your new action name to the `action_strings` list:
```python
action_strings = [
    # existing actions...
    'your_new_action'
]
```

## Step 2: Update `action_processor.py`
1. Add a handler in the `process_actions` method:
```python
elif action_name == 'your_new_action':
    await self._handle_your_new_action(params)
```

2. Implement the handler method:
```python
async def _handle_your_new_action(self, params):
    """Handle your new action.
    
    Args:
        params: List of parameters for the action
    """
    # Your implementation here
    # Example:
    param1 = params[0] if params else None
    await self.speak(f"Performing new action with {param1}")
```

## Step 3: Update `personalities.py`
Add instructions for using the action to `BASE_INSTRUCTIONS`:
```python
"\n\nYou can use the new action:"
"\n- {\"name\": \"your_new_action\", \"parameters\": [\"param1\", \"param2\"]} - Description of what the action does"
"\n  * Example: When user asks to do something, use {\"name\": \"your_new_action\", \"parameters\": [\"example_value\"]}"
```

## Step 4: For Home Assistant Integration
If your action uses Home Assistant:

1. Add methods to `home_assistant.py` to interact with Home Assistant API
2. Add handler methods to `home_assistant_handler.py` to process the action
3. Update the `handle_action` method in `home_assistant_handler.py` to route to your handler
