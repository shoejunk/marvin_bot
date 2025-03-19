# Home Assistant Integration for Marvin

This document describes how Marvin integrates with Home Assistant to provide smart home control capabilities.

## Overview

Marvin can interact with Home Assistant to:
- Get weather information
- Control smart home devices (lights, switches, etc.)
- Get and set thermostat settings
- Query device states

## Architecture

The integration consists of several components:

1. **Home Assistant Controller** (`home_assistant_controller.py`): Handles direct API communication with Home Assistant
2. **Home Assistant Handler** (`home_assistant_handler.py`): Processes Home Assistant actions and stores results in context
3. **Context Store** (`context_store.py`): Maintains persistent context including Home Assistant query results
4. **Action Processor** (`action_processor.py`): Routes Home Assistant actions to the appropriate handlers

## Key Features

### Context-Based Responses

Rather than directly speaking the results of Home Assistant queries, Marvin now:
1. Stores query results in context
2. Passes this context to the LLM
3. Gets a natural language response based on the results
4. Speaks this response to the user

This provides a more conversational experience compared to robotic responses.

### Supported Actions

The following Home Assistant actions are supported:

| Action | Description | Parameters |
|--------|-------------|------------|
| `get_weather` | Get current weather information | `[entity_id]` (optional) |
| `get_thermostat` | Get thermostat information | `[entity_id]` |
| `set_thermostat` | Set thermostat temperature and mode | `[entity_id, temperature, mode]` |
| `control_entity` | Control any Home Assistant entity | `[entity_id, service, param1_name, param1_value, ...]` |
| `list_climate_devices` | Get a list of all climate devices | None |
| `get_smart_devices` | Get a list of all smart devices | None |

## Configuration

To use the Home Assistant integration, you need to set the following environment variables:

```
HOME_ASSISTANT_URL=http://your-home-assistant-url:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
```

You can create a long-lived access token in your Home Assistant profile.

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

## Testing

You can test the Home Assistant integration using the `test_ha_integration.py` script:

```bash
python test_ha_integration.py
```

This script tests:
- Storing results in context
- Getting context for the LLM
- Getting responses from the LLM based on context
- Communicating with Home Assistant (if credentials are available)
