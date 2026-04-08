from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.checks import dmv_check
from utils.embeds import base_embed, error_embed, success_embed, Colors


LICENSE_TYPES = {"learner permit", "driver license", "commercial license"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DMV(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _latest_active_license(self, user_id: int):
        return await db.fetchone(
            "SELECT * FROM licenses WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (user_id,),
        )

    async def _update_staff(self, examiner_id: int, action: str) -> None:
        staff = self.bot.get_cog("Staff")
        if staff:
            await staff.increment_action(examiner_id, action)

    @commands.hybrid_command(name="issue", description="Issue DMV license.")
    @dmv_check()
    async def issue(self, ctx: commands.Context, member: discord.Member, *, license_type: str) -> None:
        if license_type.lower() not in LICENSE_TYPES:
            return await ctx.send(embed=error_embed("License type must be Learner Permit, Driver License, or Commercial License."))
        await db.execute(
            "INSERT INTO licenses (user_id, license_type, status, issued_at, examiner_id) VALUES (?, ?, 'active', ?, ?)",
            (member.id, license_type.title(), utcnow().isoformat(), ctx.author.id),
        )
        await self._update_staff(ctx.author.id, "license")
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_license(ctx.guild, "License Issued", {
                "User": member.mention,
                "Type": license_type.title(),
                "Examiner": ctx.author.mention,
                "Status": "Active",
            })
        await ctx.send(embed=success_embed("License Issued", f"{member.mention} received a **{license_type.title()}**."))

    @commands.hybrid_command(name="revoke", description="Revoke active license.")
    @dmv_check()
    async def revoke(self, ctx: commands.Context, member: discord.Member) -> None:
        lic = await self._latest_active_license(member.id)
        if not lic:
            return await ctx.send(embed=error_embed("That user has no active license."))
        await db.execute(
            "UPDATE licenses SET status = 'revoked', revoked_at = ?, revoked_by = ? WHERE id = ?",
            (utcnow().isoformat(), ctx.author.id, lic["id"]),
        )
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_license(ctx.guild, "License Revoked", {
                "User": member.mention,
                "Type": lic["license_type"],
                "Revoked By": ctx.author.mention,
            })
        await ctx.send(embed=success_embed("License Revoked", f"Revoked **{lic['license_type']}** from {member.mention}."))

    @commands.hybrid_command(name="licenses", description="View user licenses.")
    async def licenses(self, ctx: commands.Context, member: discord.Member | None = None) -> None:
        target = member or ctx.author
        rows = await db.fetchall("SELECT * FROM licenses WHERE user_id = ? ORDER BY id DESC", (target.id,))
        if not rows:
            return await ctx.send(embed=error_embed("No license records found."))
        lines = [
            f"`#{row['id']}` **{row['license_type']}** | `{row['status']}` | issued `{row['issued_at'][:10]}`"
            for row in rows[:10]
        ]
        await ctx.send(embed=base_embed(f"License Records: {target}", "\n".join(lines), Colors.INFO))

    @commands.hybrid_command(name="starttest", description="Start a driving test.")
    @dmv_check()
    async def starttest(self, ctx: commands.Context, member: discord.Member) -> None:
        await db.execute(
            "INSERT INTO tests (user_id, examiner_id, started_at, status) VALUES (?, ?, ?, 'started')",
            (member.id, ctx.author.id, utcnow().isoformat()),
        )
        await ctx.send(embed=success_embed("Driving Test Started", f"Started a test for {member.mention}."))

    @commands.hybrid_command(name="pass", description="Pass a driving test.")
    @dmv_check()
    async def pass_test(self, ctx: commands.Context, member: discord.Member) -> None:
        test = await db.fetchone(
            "SELECT * FROM tests WHERE user_id = ? AND status = 'started' ORDER BY id DESC LIMIT 1",
            (member.id,),
        )
        if not test:
            return await ctx.send(embed=error_embed("No active test found for that user."))
        await db.execute(
            "UPDATE tests SET status = 'passed', ended_at = ? WHERE id = ?",
            (utcnow().isoformat(), test["id"]),
        )
        await self._update_staff(ctx.author.id, "test")
        role = discord.utils.get(ctx.guild.roles, name=settings.verified_role)
        if role and isinstance(member, discord.Member):
            try:
                await member.add_roles(role, reason="Passed DMV test")
            except discord.HTTPException:
                pass
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_license(ctx.guild, "Driving Test Passed", {
                "User": member.mention,
                "Examiner": ctx.author.mention,
                "Result": "Passed",
            })
        await ctx.send(embed=success_embed("Test Passed", f"{member.mention} passed the driving test."))

    @commands.hybrid_command(name="fail", description="Fail a driving test.")
    @dmv_check()
    async def fail_test(self, ctx: commands.Context, member: discord.Member, *, reason: str) -> None:
        test = await db.fetchone(
            "SELECT * FROM tests WHERE user_id = ? AND status = 'started' ORDER BY id DESC LIMIT 1",
            (member.id,),
        )
        if not test:
            return await ctx.send(embed=error_embed("No active test found for that user."))
        await db.execute(
            "UPDATE tests SET status = 'failed', reason = ?, ended_at = ? WHERE id = ?",
            (reason, utcnow().isoformat(), test["id"]),
        )
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_license(ctx.guild, "Driving Test Failed", {
                "User": member.mention,
                "Examiner": ctx.author.mention,
                "Reason": reason,
            })
        await ctx.send(embed=success_embed("Test Failed", f"{member.mention} failed the test. Reason: {reason}"))

    @commands.hybrid_command(name="booktest", description="Book a driving test.")
    async def booktest(self, ctx: commands.Context) -> None:
        existing = await db.fetchone(
            "SELECT * FROM bookings WHERE user_id = ? AND status = 'queued'",
            (ctx.author.id,),
        )
        if existing:
            return await ctx.send(embed=error_embed("You already have a queued booking."))
        await db.execute(
            "INSERT INTO bookings (user_id, requested_at, status) VALUES (?, ?, 'queued')",
            (ctx.author.id, utcnow().isoformat()),
        )
        await ctx.send(embed=success_embed("Booking Created", "You were added to the DMV booking queue."))

    @commands.hybrid_command(name="queue", description="View DMV booking queue.")
    @dmv_check()
    async def queue(self, ctx: commands.Context) -> None:
        rows = await db.fetchall("SELECT * FROM bookings WHERE status = 'queued' ORDER BY id ASC")
        if not rows:
            return await ctx.send(embed=error_embed("The booking queue is empty."))
        lines = []
        for row in rows:
            user = ctx.guild.get_member(row["user_id"])
            lines.append(f"`#{row['id']}` {user.mention if user else row['user_id']} | requested `{row['requested_at'][:16]}`")
        await ctx.send(embed=base_embed("DMV Booking Queue", "\n".join(lines), Colors.INFO))

    @commands.hybrid_command(name="checklicense", description="Check license status.")
    async def checklicense(self, ctx: commands.Context, member: discord.Member) -> None:
        lic = await self._latest_active_license(member.id)
        if not lic:
            return await ctx.send(embed=error_embed(f"{member.mention} has no valid license."))
        embed = base_embed("License Status", color=Colors.SUCCESS)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Type", value=lic["license_type"])
        embed.add_field(name="Issued", value=lic["issued_at"][:10])
        embed.add_field(name="Status", value=lic["status"])
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DMV(bot))
