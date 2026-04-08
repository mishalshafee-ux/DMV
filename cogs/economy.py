from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.checks import admin_check
from utils.embeds import base_embed, error_embed, success_embed, Colors


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Economy(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        await db.init()

    async def get_user_row(self, user_id: int):
        await db.ensure_user(user_id)
        return await db.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    async def adjust_wallet(self, user_id: int, amount: int) -> None:
        await db.ensure_user(user_id)
        row = await self.get_user_row(user_id)
        new_amount = max(0, min(settings.max_wallet, row["wallet"] + amount))
        await db.execute("UPDATE users SET wallet = ? WHERE user_id = ?", (new_amount, user_id))

    async def add_tx(self, user_id: int, tx_type: str, amount: int, note: str, target_user_id: int | None = None) -> None:
        await db.execute(
            "INSERT INTO transactions (user_id, target_user_id, type, amount, note) VALUES (?, ?, ?, ?, ?)",
            (user_id, target_user_id, tx_type, amount, note),
        )

    @commands.hybrid_command(name="balance", description="Check wallet balance.")
    async def balance(self, ctx: commands.Context) -> None:
        row = await self.get_user_row(ctx.author.id)
        embed = base_embed("Wallet Balance", color=Colors.INFO)
        embed.add_field(name="User", value=ctx.author.mention)
        embed.add_field(name="Cash", value=f"${row['wallet']:,}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="work", description="Work a DMV side job for cash.")
    async def work(self, ctx: commands.Context) -> None:
        row = await self.get_user_row(ctx.author.id)
        next_time = parse_iso(row["work_cooldown_until"])
        if next_time and utcnow() < next_time:
            seconds = int((next_time - utcnow()).total_seconds())
            return await ctx.send(embed=error_embed(f"You can work again in `{seconds // 60}m {seconds % 60}s`."))
        reward = random.randint(settings.work_reward_min, settings.work_reward_max)
        cd_minutes = random.randint(10, 30)
        await self.adjust_wallet(ctx.author.id, reward)
        await db.execute(
            "UPDATE users SET work_cooldown_until = ? WHERE user_id = ?",
            ((utcnow() + timedelta(minutes=cd_minutes)).isoformat(), ctx.author.id),
        )
        await self.add_tx(ctx.author.id, "work", reward, "Completed work shift")
        await ctx.send(embed=success_embed("Shift Complete", f"You earned `${reward:,}`. Cooldown: `{cd_minutes}` minutes."))

    @commands.hybrid_command(name="collect", description="Claim daily reward.")
    async def collect(self, ctx: commands.Context) -> None:
        row = await self.get_user_row(ctx.author.id)
        next_time = parse_iso(row["daily_cooldown_until"])
        if next_time and utcnow() < next_time:
            seconds = int((next_time - utcnow()).total_seconds())
            hours, rem = divmod(seconds, 3600)
            mins = rem // 60
            return await ctx.send(embed=error_embed(f"Daily reward resets in `{hours}h {mins}m`."))
        reward = random.randint(settings.daily_reward_min, settings.daily_reward_max)
        await self.adjust_wallet(ctx.author.id, reward)
        await db.execute(
            "UPDATE users SET daily_cooldown_until = ? WHERE user_id = ?",
            ((utcnow() + timedelta(hours=24)).isoformat(), ctx.author.id),
        )
        await self.add_tx(ctx.author.id, "daily", reward, "Daily collect")
        await ctx.send(embed=success_embed("Daily Reward", f"You collected `${reward:,}` in DMV cash."))

    @commands.hybrid_command(name="pay", description="Pay from wallet.")
    async def pay(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        if amount <= 0 or member.bot or member.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Use a valid user and amount."))
        sender = await self.get_user_row(ctx.author.id)
        if sender["wallet"] < amount:
            return await ctx.send(embed=error_embed("You do not have enough wallet cash."))
        receiver = await self.get_user_row(member.id)
        if receiver["wallet"] + amount > settings.max_wallet:
            return await ctx.send(embed=error_embed("That user would exceed the wallet cap."))
        await self.adjust_wallet(ctx.author.id, -amount)
        await self.adjust_wallet(member.id, amount)
        await self.add_tx(ctx.author.id, "pay_sent", -amount, "Wallet payment", member.id)
        await self.add_tx(member.id, "pay_received", amount, "Wallet payment", ctx.author.id)
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_money(ctx.guild, str(ctx.author), str(member), amount, "Wallet payment")
        await ctx.send(embed=success_embed("Payment Sent", f"You paid {member.mention} `${amount:,}`."))

    @commands.hybrid_command(name="fine", description="Fine a user.")
    async def fine(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        if amount <= 0:
            return await ctx.send(embed=error_embed("Amount must be greater than 0."))
        if not any(check(ctx) for check in []):
            pass
        from utils.checks import is_dmv_member, is_police_member, is_admin_member
        if not isinstance(ctx.author, discord.Member) or not (is_dmv_member(ctx.author) or is_police_member(ctx.author) or is_admin_member(ctx.author)):
            return await ctx.send(embed=error_embed("Only DMV staff, police, or admins can fine users."))
        await self.adjust_wallet(member.id, -amount)
        await db.execute(
            "INSERT INTO fines (user_id, issued_by, amount, reason, created_at) VALUES (?, ?, ?, ?, ?)",
            (member.id, ctx.author.id, amount, "Manual fine", utcnow().isoformat()),
        )
        await self.add_tx(member.id, "fine", -amount, f"Fine issued by {ctx.author}", ctx.author.id)
        logger = self.bot.get_cog("LoggingCog")
        if logger:
            await logger.log_money(ctx.guild, str(ctx.author), str(member), amount, "Fine")
        await ctx.send(embed=success_embed("Fine Issued", f"{member.mention} was fined `${amount:,}`."))

    @commands.hybrid_command(name="addmoney", description="Admin wallet add.")
    @admin_check()
    async def addmoney(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        await self.adjust_wallet(member.id, amount)
        await self.add_tx(member.id, "admin_add", amount, f"Added by {ctx.author}", ctx.author.id)
        await ctx.send(embed=success_embed("Wallet Updated", f"Added `${amount:,}` to {member.mention}."))

    @commands.hybrid_command(name="removemoney", description="Admin wallet remove.")
    @admin_check()
    async def removemoney(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        await self.adjust_wallet(member.id, -amount)
        await self.add_tx(member.id, "admin_remove", -amount, f"Removed by {ctx.author}", ctx.author.id)
        await ctx.send(embed=success_embed("Wallet Updated", f"Removed `${amount:,}` from {member.mention}."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
