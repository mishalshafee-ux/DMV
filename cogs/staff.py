from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord.ext import commands

from database import db
from utils.checks import dmv_check
from utils.embeds import base_embed, error_embed, success_embed, Colors


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Staff(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def increment_action(self, user_id: int, action: str) -> None:
        await db.execute("INSERT OR IGNORE INTO staff_stats (user_id, last_active) VALUES (?, ?)", (user_id, utcnow().isoformat()))
        if action == "test":
            await db.execute("UPDATE staff_stats SET tests_done = tests_done + 1, actions_completed = actions_completed + 1, last_active = ? WHERE user_id = ?", (utcnow().isoformat(), user_id))
        elif action == "license":
            await db.execute("UPDATE staff_stats SET licenses_issued = licenses_issued + 1, actions_completed = actions_completed + 1, last_active = ? WHERE user_id = ?", (utcnow().isoformat(), user_id))

    @commands.hybrid_command(name="shiftstart", description="Start DMV shift.")
    @dmv_check()
    async def shiftstart(self, ctx: commands.Context) -> None:
        active = await db.fetchone("SELECT * FROM active_shifts WHERE user_id = ?", (ctx.author.id,))
        if active:
            return await ctx.send(embed=error_embed("You already have an active shift."))
        await db.execute("INSERT INTO active_shifts (user_id, started_at) VALUES (?, ?)", (ctx.author.id, utcnow().isoformat()))
        await db.execute("INSERT OR IGNORE INTO staff_stats (user_id, last_active) VALUES (?, ?)", (ctx.author.id, utcnow().isoformat()))
        await ctx.send(embed=success_embed("Shift Started", "Your DMV shift timer is now running."))

    @commands.hybrid_command(name="shiftend", description="End DMV shift.")
    @dmv_check()
    async def shiftend(self, ctx: commands.Context) -> None:
        active = await db.fetchone("SELECT * FROM active_shifts WHERE user_id = ?", (ctx.author.id,))
        if not active:
            return await ctx.send(embed=error_embed("You do not have an active shift."))
        started = datetime.fromisoformat(active["started_at"])
        duration = (utcnow() - started).total_seconds() / 3600
        await db.execute("DELETE FROM active_shifts WHERE user_id = ?", (ctx.author.id,))
        await db.execute(
            "UPDATE staff_stats SET hours_worked = hours_worked + ?, last_active = ? WHERE user_id = ?",
            (duration, utcnow().isoformat(), ctx.author.id),
        )
        await ctx.send(embed=success_embed("Shift Ended", f"Shift logged: `{duration:.2f}` hours."))

    @commands.hybrid_command(name="activity", description="View staff stats.")
    @dmv_check()
    async def activity(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        row = await db.fetchone("SELECT * FROM staff_stats WHERE user_id = ?", (target.id,))
        if not row:
            return await ctx.send(embed=error_embed("No activity data found."))
        embed = base_embed("Staff Activity", color=Colors.INFO)
        embed.add_field(name="Staff Member", value=target.mention)
        embed.add_field(name="Tests Done", value=str(row["tests_done"]))
        embed.add_field(name="Licenses Issued", value=str(row["licenses_issued"]))
        embed.add_field(name="Hours Worked", value=f"{row['hours_worked']:.2f}")
        embed.add_field(name="Actions Completed", value=str(row["actions_completed"]))
        embed.add_field(name="Last Active", value=row["last_active"] or "N/A", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="Top DMV staff.")
    @dmv_check()
    async def leaderboard(self, ctx: commands.Context) -> None:
        rows = await db.fetchall("SELECT * FROM staff_stats ORDER BY actions_completed DESC, hours_worked DESC LIMIT 10")
        if not rows:
            return await ctx.send(embed=error_embed("No staff data yet."))
        lines = []
        for idx, row in enumerate(rows, start=1):
            user = ctx.guild.get_member(row["user_id"])
            name = user.mention if user else str(row["user_id"])
            lines.append(f"**{idx}.** {name} | Actions: `{row['actions_completed']}` | Hours: `{row['hours_worked']:.2f}`")
        await ctx.send(embed=base_embed("DMV Staff Leaderboard", "\n".join(lines), Colors.SUCCESS))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Staff(bot))
