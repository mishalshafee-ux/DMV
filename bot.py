from __future__ import annotations

import asyncio
import threading

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.embeds import error_embed


INITIAL_EXTENSIONS = [
    "cogs.logging",
    "cogs.economy",
    "cogs.bank",
    "cogs.staff",
    "cogs.dmv",
    "cogs.police",
    "cogs.mdt",
    "cogs.verification",
    "cogs.applications",
    "cogs.tickets",
    "cogs.license_card",
    "cogs.web_api",
]


class DMVBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix=settings.prefix, intents=intents)

    async def setup_hook(self) -> None:
        await db.init()
        for ext in INITIAL_EXTENSIONS:
            await self.load_extension(ext)
        if settings.guild_id:
            guild = discord.Object(id=settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} ({self.user.id})")

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(embed=error_embed(f"Cooldown active. Try again in `{error.retry_after:.1f}` seconds."))
        if isinstance(error, commands.CheckFailure):
            return await ctx.send(embed=error_embed("You do not have permission to use that command."))
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(embed=error_embed("Missing required argument."))
        raise error


def run_web_server() -> None:
    from waitress import serve
    from web.app import create_app

    app = create_app()
    serve(app, host=settings.web_host, port=settings.web_port)


def main() -> None:
    if not settings.token:
        raise RuntimeError("DISCORD_TOKEN is missing from .env")

    if settings.run_web_with_bot:
        threading.Thread(target=run_web_server, daemon=True).start()

    bot = DMVBot()
    bot.run(settings.token)


if __name__ == "__main__":
    main()
