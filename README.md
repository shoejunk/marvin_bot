# Marvin Bot

Marvin is a voice-activated assistant inspired by the paranoid android from "The Hitchhiker's Guide to the Galaxy." This assistant can perform various tasks through voice commands, including controlling smart home devices, playing music, managing files, setting timers, and even browsing the internet.

## Features

- **Voice Recognition**: Responds to wake words like "Marvin," "Computer," "PC," etc.
- **Smart Home Control**: Integration with Meross smart devices
- **Music Control**: Spotify integration for playing songs and playlists
- **File Operations**: Read, write, edit, and manage files in the artifacts directory
- **Timer Functionality**: Set and manage timers
- **Internet Browsing**: Search the web for information
- **Conversation History**: Maintains context from previous interactions (up to 50 messages)

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg (included in the `bin` directory)
- An OpenAI API key
- Meross account (optional, for smart home control)
- Spotify Developer account (optional, for music playback)

### Setup Instructions

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd marvin_bot
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Copy the `.env_template` file to `.env`:
     ```
     cp .env_template .env
     ```
   - Edit the `.env` file and replace the placeholders with your actual credentials:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `MEROSS_EMAIL` and `MEROSS_PASSWORD`: Your Meross account credentials (optional)
     - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and `SPOTIFY_REDIRECT_URI`: Your Spotify API credentials (optional)

4. **Run Marvin**:
   ```
   python main.py
   ```
   Alternatively, you can use the provided batch file:
   ```
   run_marvin.bat
   ```

## Usage

1. **Wake Words**: Start your command with one of the wake words:
   - "Marvin", "Hey Marvin", "OK Marvin"
   - "Computer", "Hey Computer"
   - "PC", "Hey PC"

2. **Example Commands**:
   - "Marvin, what time is it?"
   - "Marvin, turn on the light"
   - "Marvin, play a song by The Beatles"
   - "Marvin, set a timer for 5 minutes"
   - "Marvin, write a file called notes.txt with content Hello World"
   - "Marvin, browse the internet for the latest news about AI"

## System Tray

Marvin runs in the system tray, allowing you to:
- View the conversation history
- Restart the assistant
- Shut down the assistant

## Troubleshooting

- Check the `marvin_debug.log` file for detailed logs if you encounter any issues.
- Ensure your microphone is properly connected and configured.
- Verify that your API keys in the `.env` file are correct.

## License

See the LICENSE file for details.
