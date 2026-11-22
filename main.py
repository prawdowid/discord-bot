from dotenv import load_dotenv
import aiohttp
import base64
import discord
import os
import re

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000").rstrip("/")
REQUEST_TIMEOUT_S = 120
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_CLAIMS_SHOWN = 5
MAX_SOURCES_PER_CLAIM = 2

URL_RE = re.compile(r"https?://[^\s<>]+")

VERDICTS = {
    "confirmed": ("Potwierdzone", discord.Color.green()),
    "false": ("Fałszywe", discord.Color.red()),
    "misleading": ("Wprowadzające w błąd", discord.Color.orange()),
    "insufficient_evidence": ("Brak wystarczających dowodów", discord.Color.light_grey()),
    "not_verifiable": ("Nie podlega weryfikacji", discord.Color.light_grey()),
}


def truncate(text, limit):
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_embed(data):
    overall = data.get("overallVerdict")
    claims = data.get("claims") or []
    if not overall and len(claims) == 1:
        overall = claims[0].get("verdict")
    label, color = VERDICTS.get(overall, ("Wynik sprawdzenia", discord.Color.blurple()))

    embed = discord.Embed(
        title=label,
        description=truncate(data.get("summary") or "", 2000),
        color=color,
    )

    for claim in claims[:MAX_CLAIMS_SHOWN]:
        claim_label, _ = VERDICTS.get(claim.get("verdict"), ("?", None))
        confidence = claim.get("confidence")
        header = claim_label
        if isinstance(confidence, (int, float)):
            header += f" ({round(confidence * 100)}%)"
        lines = [claim.get("reasoning") or ""]
        for evidence in (claim.get("evidence") or [])[:MAX_SOURCES_PER_CLAIM]:
            url = evidence.get("url")
            if url:
                name = evidence.get("publisher") or evidence.get("title") or url
                lines.append(f"• [{truncate(name, 60)}]({url})")
        embed.add_field(
            name=truncate(claim.get("claim") or "Twierdzenie", 250),
            value=truncate(f"**{header}**\n" + "\n".join(line for line in lines if line), 1024),
            inline=False,
        )

    if len(claims) > MAX_CLAIMS_SHOWN:
        embed.add_field(name="…", value=f"Pominięto {len(claims) - MAX_CLAIMS_SHOWN} kolejnych twierdzeń.", inline=False)

    limitations = data.get("limitations") or []
    if limitations:
        embed.add_field(name="Ograniczenia", value=truncate("\n".join(f"• {item}" for item in limitations), 1024), inline=False)

    embed.set_footer(text=truncate(data.get("disclaimer") or "", 2048))
    return embed


class Prawdoid(discord.Client):
    def __init__(self, intents=discord.Intents.default()):
        super().__init__(intents=intents)
        self.http_session = None

    async def setup_hook(self):
        self.http_session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S))

    async def close(self):
        if self.http_session:
            await self.http_session.close()
        await super().close()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

    async def verify(self, payload):
        async with self.http_session.post(f"{BACKEND_URL}/verify", json={**payload, "channel": "discord"}) as response:
            try:
                data = await response.json()
            except (aiohttp.ContentTypeError, ValueError):
                data = None
            return response.status, data

    async def on_message(self, message):
        if message.author == self.user:
            return
        if not self.user.mentioned_in(message):
            return

        content = message.content
        for mention in (f"<@{self.user.id}>", f"<@!{self.user.id}>"):
            content = content.replace(mention, "")
        content = content.strip()

        try:
            payload = await self.build_payload(message, content)
        except ValueError as error:
            await message.reply(str(error), mention_author=False)
            return

        async with message.channel.typing():
            try:
                status, data = await self.verify(payload)
            except (aiohttp.ClientError, TimeoutError) as error:
                print(f"Backend request failed: {error!r}")
                await message.reply("Nie udało się połączyć z serwerem weryfikacji. Spróbuj ponownie później.", mention_author=False)
                return

        if not isinstance(data, dict) or "summary" not in data:
            await message.reply(f"Serwer weryfikacji zwrócił błąd (HTTP {status}).", mention_author=False)
            return

        if data.get("status") in ("error", "needs_clarification", "out_of_scope") or status >= 400:
            await message.reply(truncate(data["summary"], 2000), mention_author=False)
            return

        await message.reply(embed=build_embed(data), mention_author=False)

    async def build_payload(self, message, content):
        # Link route
        match = URL_RE.search(content)
        if match:
            return {"url": match.group(0)}

        # Image route (video and other attachments are not supported)
        if message.attachments:
            image = next((a for a in message.attachments if (a.content_type or "").startswith("image/")), None)
            if image is None:
                raise ValueError("Obsługuję tylko tekst, linki i zdjęcia.")
            if image.size > MAX_IMAGE_BYTES:
                raise ValueError("Zdjęcie jest za duże (limit 8 MB).")
            data = await image.read()
            return {"image": base64.b64encode(data).decode("ascii")}

        # Text route
        if not content:
            raise ValueError("Oznacz mnie razem z tekstem, linkiem lub zdjęciem do sprawdzenia.")
        return {"text": content}


token = os.getenv("TOKEN")

bot = Prawdoid()
bot.run(token)
