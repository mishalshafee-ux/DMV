from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from database import db
from utils.embeds import base_embed, Colors


class WebAPICog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="apistatus", description="Show dashboard integration status.")
    async def apistatus(self, interaction: discord.Interaction) -> None:
        total_users = await db.fetchone("SELECT COUNT(*) AS count FROM users")
        active_shifts = await db.fetchone("SELECT COUNT(*) AS count FROM active_shifts")
        open_tickets = await db.fetchone("SELECT COUNT(*) AS count FROM tickets WHERE status = 'open'")
        embed = base_embed("Web API Status", color=Colors.INFO)
        embed.add_field(name="Tracked Users", value=str(total_users["count"]))
        embed.add_field(name="Active Shifts", value=str(active_shifts["count"]))
        embed.add_field(name="Open Tickets", value=str(open_tickets["count"]))
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WebAPICog(bot))
