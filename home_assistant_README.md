# Home Assistant Integration for Marvin

This integration allows Marvin to control your smart home devices through Home Assistant, including your Resideo Honeywell AC and other compatible devices.

## Setup Instructions

### 1. Install Dependencies

The integration uses the `homeassistant-api` Python library. It has been added to the `requirements.txt` file, so you can install it by running:

```bash
pip install -r requirements.txt
```

### 2. Configure Home Assistant Settings

You need to update your `.env` file with your Home Assistant information:

1. Open your `.env` file
2. Add the following configuration (if it doesn't exist already):

```
HOME_ASSISTANT_URL="http://your_home_assistant_ip:8123/api"
HOME_ASSISTANT_TOKEN="your_long_lived_access_token"
```

Replace:
- `your_home_assistant_ip` with the IP address of your Home Assistant instance
- `your_long_lived_access_token` with a token generated from Home Assistant

### 3. Generate a Long-Lived Access Token

To generate a long-lived access token in Home Assistant:

1. Log in to your Home Assistant instance
2. Click on your profile (bottom left corner)
3. Scroll down to the "Long-Lived Access Tokens" section
4. Click "Create Token"
5. Give it a name (e.g., "Marvin Bot")
6. Copy the generated token and add it to your `.env` file

## Available Voice Commands

Once configured, you can use the following voice commands with Marvin:

### Thermostat Control

- "Set the thermostat to 72 degrees"
- "Turn off the thermostat"
- "What's the current temperature?"
- "Set the AC to cool mode"
- "Set the heater to heat mode"

### Device Information

- "List all climate devices"
- "Show me my smart devices"
- "What's the status of the living room thermostat?"
- "What thermostats do I have?"
- "What smart home devices are in my house?"

## Supported Actions

The following Home Assistant actions are supported:

| Action | Description | Parameters |
|--------|-------------|------------|
| `get_weather` | Get current weather information | `[entity_id]` (optional) |
| `get_thermostat` | Get thermostat information | `[entity_id]` |
| `set_thermostat` | Set thermostat temperature and mode | `[entity_id, temperature, mode]` |
| `control_entity` | Control any Home Assistant entity | `[entity_id, service, param1_name, param1_value, ...]` |
| `list_climate_devices` | Get a list of all climate devices | None |
| `get_smart_devices` | Get a list of all smart devices | None |

## Example Flows

### Weather Query

1. User asks: "What's the weather like today?"
2. Marvin detects this is a weather query and calls the `get_weather` action
3. The result is stored in context
4. Marvin generates a natural language response based on the weather data
5. The response is spoken to the user

### Thermostat Control

1. User asks: "Set the thermostat to 72 degrees"
2. Marvin calls the `set_thermostat` action
3. The result is stored in context
4. Marvin generates a confirmation response
5. The response is spoken to the user

### List Climate Devices

1. User asks: "What thermostats do I have?"
2. Marvin calls the `list_climate_devices` action
3. The result is stored in context
4. Marvin generates a response summarizing the available climate devices
5. The response is spoken to the user

### Get Smart Devices

1. User asks: "What smart devices do I have?"
2. Marvin calls the `get_smart_devices` action
3. The result is stored in context
4. Marvin generates a response summarizing the available smart devices by category
5. The response is spoken to the user

## Troubleshooting

If you encounter issues with the Home Assistant integration:

1. Check that your Home Assistant instance is running and accessible
2. Verify that the URL and token in your `.env` file are correct
3. Check the Marvin logs for any error messages
4. Make sure your Home Assistant API is accessible from the device running Marvin

## Technical Details

The integration consists of several main components:

1. `home_assistant_controller.py` - Core controller for interacting with the Home Assistant API
2. `home_assistant_handler.py` - Handler for processing Home Assistant actions
3. `context_store.py` - Manages persistent context including Home Assistant query results
4. Integration with `action_processor.py` - Allows Marvin to execute Home Assistant commands

### Context-Based Response System

Rather than directly speaking the results of Home Assistant queries, Marvin now:
1. Stores query results in context using the `update_home_assistant_query_result` function
2. Passes this context to the LLM using the `get_context_for_llm` function
3. Gets a natural language response based on the results
4. Speaks this response to the user

This provides a more conversational experience compared to robotic responses. For example, instead of saying "Temperature is 72 degrees, mode is cool", Marvin might say "Your living room is currently at a comfortable 72 degrees with the AC running in cool mode."

The integration uses the REST API provided by Home Assistant to control devices and retrieve state information.
