from __future__ import annotations

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.checks import police_check
from utils.embeds import base_embed, error_embed, success_embed, Colors


class Police(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def get_active_license(self, user_id: int):
        return await db.fetchone(
            "SELECT * FROM licenses WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

    @commands.hybrid_command(name="nolicensefine", description="Auto fine a user with no valid license.")
    @police_check()
    async def nolicensefine(self, ctx: commands.Context, member: discord.Member) -> None:
        lic = await self.get_active_license(member.id)
        if lic:
            return await ctx.send(embed=error_embed(f"{member.mention} has a valid **{lic['license_type']}**."))
        economy = self.bot.get_cog("Economy")
        if not economy:
            return await ctx.send(embed=error_embed("Economy system is unavailable."))
        await economy.adjust_wallet(member.id, -settings.no_license_fine)
        await db.execute(
            "INSERT INTO fines (user_id, issued_by, amount, reason, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (member.id, ctx.author.id, settings.no_license_fine, "Operating without license"),
        )
        await ctx.send(embed=success_embed("Fine Issued", f"{member.mention} was fined `${settings.no_license_fine:,}`."))

    @commands.hybrid_command(name="record", description="View fines and criminal records.")
    @police_check()
    async def record(self, ctx: commands.Context, member: discord.Member) -> None:
        fines = await db.fetchall(
            "SELECT * FROM fines WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (member.id,),
        )
        records = await db.fetchall(
            "SELECT * FROM criminal_records WHERE user_id = ? ORDER BY id DESC LIMIT 5",
            (member.id,),
        )
        lic = await self.get_active_license(member.id)

        fine_lines = [f"- `${row['amount']:,}` | {row['reason']} | {row['created_at'][:16]}" for row in fines]
        record_lines = [f"- {row['reason']} | {row['created_at'][:16]}" for row in records]

        if not fine_lines:
            fine_lines = ["- None"]
        if not record_lines:
            record_lines = ["- None"]

        description = "\n".join([
            f"**License:** {lic['license_type']} ({lic['status']})" if lic else "**License:** None",
            "",
            "**Recent Fines:**",
            *fine_lines,
            "",
            "**Criminal Records:**",
            *record_lines,
        ])

        await ctx.send(embed=base_embed(f"Police Record: {member}", description, Colors.WARNING))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Police(bot))
