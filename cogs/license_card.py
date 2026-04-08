from __future__ import annotations

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.embeds import error_embed
from utils.license_card import generate_license_card


class LicenseCardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="licensecard", description="Generate digital license card.")
    async def licensecard(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        lic = await db.fetchone(
            "SELECT * FROM licenses WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (target.id,),
        )
        if not lic:
            return await ctx.send(embed=error_embed("No active license found for that user."))
        verify_url = f"{settings.web_base_url}/verify-license/{lic['id']}"
        file = generate_license_card(str(target), lic["license_type"], lic["issued_at"][:10], str(lic["id"]), verify_url)
        await ctx.send(content=f"Digital license card for {target.mention}", file=file)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LicenseCardCog(bot))
