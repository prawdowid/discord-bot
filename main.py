from dotenv import load_dotenv
import discord
import os

load_dotenv()

class Prawdoid(discord.Client):
    def __init__(self, intents=discord.Intents.default()):
        super().__init__(intents=intents)
    
    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if self.user.mentioned_in(message):
            await message.reply('Hello!')

token = os.getenv("TOKEN")

bot = Prawdoid()
bot.run(token)