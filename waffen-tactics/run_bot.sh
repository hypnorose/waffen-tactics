#!/bin/bash

# Script to run the Waffen Tactics Discord bot

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Create .env file with: DISCORD_BOT_TOKEN=your_token_here"
    exit 1
fi

echo "🚀 Starting Waffen Tactics Bot..."
bot_venv/bin/python discord_bot.py
