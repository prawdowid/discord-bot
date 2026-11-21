from dotenv import load_dotenv
import discord
import os

load_dotenv()

class Prawdoid(discord.Client):
    def __init__(self, intents=discord.Intents.default()):
        super().__init__(intents=intents)

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def on_message(self, message):
        if message.author == self.user:
            return
        if self.user.mentioned_in(message):
            # Link route
            if "https://" in message.content or "http://" in message.content:
                await message.channel.send("I see you mentioned me with a link!")
            # Image or Video route
            elif message.attachments:
                if any(attachment.content_type.startswith("image/") for attachment in message.attachments):
                    await message.channel.send("I see you mentioned me with an image!")
                elif any(attachment.content_type.startswith("video/") for attachment in message.attachments):
                    await message.channel.send("I see you mentioned me with a video!")
                else:
                    await message.channel.send("I can't recognize the type of attachment you sent!")
            # Text route
            else:
                await message.channel.send("I see you mentioned me with a message!")

token = os.getenv("TOKEN")

bot = Prawdoid()
bot.run(token)
