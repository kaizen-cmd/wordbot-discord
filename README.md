# Wordchain bot Discord

A Discord bot that facilitates a word chain game across multiple servers. This repository contains the source code for the bot, including database interactions, Discord bot interactions, and additional utilities.

## Project Structure

- **MultiServerWordChainDB.py** - Handles SQL interactions.
- **WordChainClient.py** - Manages Discord bot interactions using `discord.py`.
- **app.py** - Combines instances of the database and bot clients.
- **main.py** - Entry point of the bot.
- **elements.py** - UI elements sent by the bot.
- **insights.py** - Generates server ranking insights.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/kaizen-cmd/wordbot-discors.git
   cd multiserver-wordchain-bot
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add the following:
   ```ini
   SLAV_USER_ID=462682564281499659
   SUPPORT_SERVER_ID=1234116258186657872
   SUPPORT_SERVER_LOG_CHANNEL_ID=1234117670996148246
   BOT_TOKEN=<create_your_own>
   BOT_ID=<create_your_own>
   ```

   - You can obtain `BOT_ID` and `BOT_TOKEN` from [Discord Developer Portal](https://discord.com/developers/applications).

## Running the Bot

Run the following command to start the bot:
```sh
python main.py
```

## Contributing

Contributions are welcome! Please open an issue or a pull request if you find any improvements or bug fixes.

## License

This project is licensed under the MIT License. See `LICENSE` for more details.
