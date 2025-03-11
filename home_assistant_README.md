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

## Troubleshooting

If you encounter issues with the Home Assistant integration:

1. Check that your Home Assistant instance is running and accessible
2. Verify that the URL and token in your `.env` file are correct
3. Check the Marvin logs for any error messages
4. Make sure your Home Assistant API is accessible from the device running Marvin

## Technical Details

The integration consists of three main components:

1. `home_assistant.py` - Core controller for interacting with the Home Assistant API
2. `home_assistant_handler.py` - Handler for processing Home Assistant actions
3. Integration with `action_processor.py` - Allows Marvin to execute Home Assistant commands

The integration uses the REST API provided by Home Assistant to control devices and retrieve state information.
