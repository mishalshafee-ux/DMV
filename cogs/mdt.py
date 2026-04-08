from __future__ import annotations

import discord
from discord.ext import commands

from database import db
from utils.checks import police_check
from utils.embeds import base_embed, success_embed, error_embed, Colors


class MDT(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="mdt", description="Full MDT profile lookup.")
    @police_check()
    async def mdt(self, ctx: commands.Context, member: discord.Member) -> None:
        user = await db.fetchone("SELECT * FROM users WHERE user_id = ?", (member.id,))
        license_row = await db.fetchone("SELECT * FROM licenses WHERE user_id = ? ORDER BY id DESC LIMIT 1", (member.id,))
        fine_count = await db.fetchone("SELECT COUNT(*) AS count FROM fines WHERE user_id = ?", (member.id,))
        record_count = await db.fetchone("SELECT COUNT(*) AS count FROM criminal_records WHERE user_id = ?", (member.id,))
        embed = base_embed("Police MDT Lookup", color=Colors.WARNING)
        embed.add_field(name="Citizen", value=f"{member} ({member.id})", inline=False)
        embed.add_field(name="Wallet", value=f"${user['wallet']:,}" if user else "$0")
        embed.add_field(name="Bank", value=f"${user['bank']:,}" if user else "$0")
        embed.add_field(name="Latest License", value=license_row["license_type"] if license_row else "None")
        embed.add_field(name="License Status", value=license_row["status"] if license_row else "N/A")
        embed.add_field(name="Fines", value=str(fine_count["count"]))
        embed.add_field(name="Criminal Records", value=str(record_count["count"]))
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="addrecord", description="Add criminal record entry.")
    @police_check()
    async def addrecord(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        await db.execute(
            "INSERT INTO criminal_records (user_id, officer_id, reason, created_at) VALUES (?, ?, ?, datetime('now'))",
            (member.id, ctx.author.id, reason),
        )
        await ctx.send(embed=success_embed("Record Added", f"Added a record for {member.mention}: {reason}"))

    @commands.hybrid_command(name="records", description="Alias for MDT history view.")
    @police_check()
    async def records(self, ctx: commands.Context, member: discord.Member) -> None:
        rows = await db.fetchall("SELECT * FROM criminal_records WHERE user_id = ? ORDER BY id DESC LIMIT 10", (member.id,))
        if not rows:
            return await ctx.send(embed=error_embed("No criminal records found."))
        lines = [f"`#{row['id']}` {row['reason']} | {row['created_at'][:16]}" for row in rows]
        await ctx.send(embed=base_embed(f"Criminal Records: {member}", "\n".join(lines), Colors.WARNING))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MDT(bot))
