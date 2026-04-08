from __future__ import annotations

import discord
from discord.ext import commands

from config import settings
from utils.embeds import base_embed, Colors


class LoggingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_named_channel(self, guild: discord.Guild, channel_name: str) -> discord.TextChannel | None:
        return discord.utils.get(guild.text_channels, name=channel_name)

    async def log_embed(self, guild: discord.Guild, channel_name: str, embed: discord.Embed) -> None:
        channel = await self.get_named_channel(guild, channel_name)
        if channel:
            await channel.send(embed=embed)

    async def log_money(self, guild: discord.Guild, actor: str, target: str, amount: int, reason: str) -> None:
        embed = base_embed("Money Transaction", color=Colors.INFO)
        embed.add_field(name="Actor", value=actor, inline=True)
        embed.add_field(name="Target", value=target, inline=True)
        embed.add_field(name="Amount", value=f"${amount:,}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await self.log_embed(guild, settings.dmv_logs_channel, embed)

    async def log_license(self, guild: discord.Guild, title: str, details: dict[str, str]) -> None:
        embed = base_embed(title, color=Colors.PRIMARY)
        for key, value in details.items():
            embed.add_field(name=key, value=value, inline=False)
        await self.log_embed(guild, settings.dmv_logs_channel, embed)

    async def log_police(self, guild: discord.Guild, title: str, details: dict[str, str]) -> None:
        embed = base_embed(title, color=Colors.WARNING)
        for key, value in details.items():
            embed.add_field(name=key, value=value, inline=False)
        await self.log_embed(guild, settings.police_logs_channel, embed)

    async def log_ticket(self, guild: discord.Guild, title: str, details: dict[str, str]) -> None:
        embed = base_embed(title, color=Colors.INFO)
        for key, value in details.items():
            embed.add_field(name=key, value=value, inline=False)
        await self.log_embed(guild, settings.ticket_logs_channel, embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LoggingCog(bot))
