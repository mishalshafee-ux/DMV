from __future__ import annotations

from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from config import settings
from database import db
from utils.embeds import base_embed, error_embed, success_embed, Colors


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class Bank(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _row(self, user_id: int):
        await db.ensure_user(user_id)
        return await db.fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))

    async def _log_tx(self, user_id: int, kind: str, amount: int, note: str, target_user_id: int | None = None) -> None:
        await db.execute(
            "INSERT INTO transactions (user_id, target_user_id, type, amount, note) VALUES (?, ?, ?, ?, ?)",
            (user_id, target_user_id, kind, amount, note),
        )

    @commands.hybrid_command(name="bank", description="View bank balance.")
    async def bank(self, ctx: commands.Context) -> None:
        row = await self._row(ctx.author.id)
        embed = base_embed("Bank Account", color=Colors.INFO)
        embed.add_field(name="User", value=ctx.author.mention)
        embed.add_field(name="Wallet", value=f"${row['wallet']:,}")
        embed.add_field(name="Bank", value=f"${row['bank']:,}")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="deposit", description="Deposit wallet cash.")
    async def deposit(self, ctx: commands.Context, amount: int) -> None:
        row = await self._row(ctx.author.id)
        if amount <= 0 or amount > row["wallet"]:
            return await ctx.send(embed=error_embed("Invalid deposit amount."))
        if row["bank"] + amount > settings.max_bank:
            return await ctx.send(embed=error_embed("Bank cap reached."))
        await db.execute("UPDATE users SET wallet = wallet - ?, bank = bank + ? WHERE user_id = ?", (amount, amount, ctx.author.id))
        await self._log_tx(ctx.author.id, "deposit", amount, "Wallet to bank")
        await ctx.send(embed=success_embed("Deposit Complete", f"Deposited `${amount:,}`."))

    @commands.hybrid_command(name="withdraw", description="Withdraw bank cash.")
    async def withdraw(self, ctx: commands.Context, amount: int) -> None:
        row = await self._row(ctx.author.id)
        if amount <= 0 or amount > row["bank"]:
            return await ctx.send(embed=error_embed("Invalid withdraw amount."))
        if row["wallet"] + amount > settings.max_wallet:
            return await ctx.send(embed=error_embed("Wallet cap reached."))
        await db.execute("UPDATE users SET wallet = wallet + ?, bank = bank - ? WHERE user_id = ?", (amount, amount, ctx.author.id))
        await self._log_tx(ctx.author.id, "withdraw", amount, "Bank to wallet")
        await ctx.send(embed=success_embed("Withdrawal Complete", f"Withdrew `${amount:,}`."))

    @commands.hybrid_command(name="transfer", description="Transfer bank money.")
    async def transfer(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        if member.bot or amount <= 0 or member.id == ctx.author.id:
            return await ctx.send(embed=error_embed("Invalid transfer target or amount."))
        sender = await self._row(ctx.author.id)
        receiver = await self._row(member.id)
        if sender["bank"] < amount:
            return await ctx.send(embed=error_embed("Insufficient bank balance."))
        if receiver["bank"] + amount > settings.max_bank:
            return await ctx.send(embed=error_embed("Target user would exceed the bank cap."))
        await db.execute("UPDATE users SET bank = bank - ? WHERE user_id = ?", (amount, ctx.author.id))
        await db.execute("UPDATE users SET bank = bank + ? WHERE user_id = ?", (amount, member.id))
        await self._log_tx(ctx.author.id, "bank_transfer_sent", -amount, "Bank transfer sent", member.id)
        await self._log_tx(member.id, "bank_transfer_received", amount, "Bank transfer received", ctx.author.id)
        await ctx.send(embed=success_embed("Transfer Complete", f"Transferred `${amount:,}` to {member.mention}."))

    @commands.hybrid_command(name="interest", description="Claim daily bank interest.")
    async def interest(self, ctx: commands.Context) -> None:
        row = await self._row(ctx.author.id)
        next_time = parse_iso(row["interest_cooldown_until"])
        if next_time and utcnow() < next_time:
            remaining = int((next_time - utcnow()).total_seconds())
            return await ctx.send(embed=error_embed(f"Interest available again in `{remaining // 3600}h {(remaining % 3600) // 60}m`."))
        interest = max(1, int(row["bank"] * settings.bank_interest_rate))
        if interest <= 0:
            return await ctx.send(embed=error_embed("You need money in your bank to earn interest."))
        if row["bank"] + interest > settings.max_bank:
            interest = settings.max_bank - row["bank"]
        await db.execute(
            "UPDATE users SET bank = bank + ?, interest_cooldown_until = ? WHERE user_id = ?",
            (interest, (utcnow() + timedelta(hours=24)).isoformat(), ctx.author.id),
        )
        await self._log_tx(ctx.author.id, "interest", interest, "Daily bank interest")
        await ctx.send(embed=success_embed("Interest Paid", f"You earned `${interest:,}` in bank interest."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Bank(bot))
