Setup Instructions:
1. Discord application and bot registered on Discord Developer Portal
2. Use Python >= 3.8.3
3. Install all pip packages using pip install -r settings/requirements.txt
4. Change settings/server_settings_prod.py to settings/server_settings.py and update internal values accordingly, especially your Discord Bot API key
5. Add your server using the example file in /settings/servers/guild_id_example_1234567890.py and remove this file. Fill in the details with the relevant values from your Discord server.
6. Optional: update Google API settings in plugins/google_drive_uploader
7. Optional: create Linux service with settings/discord-py-bot.service

Start with: python3 controller.py

# OS specific options:
## Windows:
* FFMPEG installed in PATH
* Pychant stuff may get installed automagically if not, see their docs
* Redis configured on localhost or remotely

## Linux (ubuntu):
* sudo apt install python3-enchant
* sudo apt install ffmpeg
* Redis configured on localhost or remotely


Created by Spencer Austad
