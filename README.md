# discord-bot

A Discord bot for the Prawdowid project

## Setup

Run these commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Setup the bot token in .env (optionally `BACKEND_URL`, default `http://localhost:3000`), start the backend, and then run the program.

Mention the bot with text, a link or an image attachment (video is not supported) and it will call the backend's `/verify` endpoint and reply with the result.

```bash
python main.py
```

Don't forget to invite the bot to your server or DM him.