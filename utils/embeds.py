from __future__ import annotations

from datetime import datetime, timezone

import discord


class Colors:
    PRIMARY = discord.Color.blurple()
    SUCCESS = discord.Color.green()
    ERROR = discord.Color.red()
    WARNING = discord.Color.orange()
    INFO = discord.Color.gold()


def base_embed(title: str, description: str = "", color: discord.Color = Colors.PRIMARY) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text="DMV Roleplay System")
    return embed


def error_embed(message: str) -> discord.Embed:
    return base_embed("Error", message, Colors.ERROR)


def success_embed(title: str, message: str) -> discord.Embed:
    return base_embed(title, message, Colors.SUCCESS)
