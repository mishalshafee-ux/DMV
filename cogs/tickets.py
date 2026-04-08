from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from database import db
from utils.embeds import base_embed, error_embed, success_embed, Colors
from utils.transcripts import build_transcript


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class TicketPanelView(discord.ui.View):
    def __init__(self, cog: "TicketsCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.secondary, custom_id="ticket_general")
    async def general(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog.create_ticket(interaction, "general-support")

    @discord.ui.button(label="DMV Help", style=discord.ButtonStyle.primary, custom_id="ticket_dmv")
    async def dmv_help(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog.create_ticket(interaction, "dmv-help")

    @discord.ui.button(label="License Issues", style=discord.ButtonStyle.success, custom_id="ticket_license")
    async def license_issues(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog.create_ticket(interaction, "license-issues")


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.panel_view = TicketPanelView(self)

    async def cog_load(self) -> None:
        self.bot.add_view(self.panel_view)

    async def create_ticket(self, interaction: discord.Interaction, category_name: str) -> None:
        existing = await db.fetchone(
            "SELECT * FROM tickets WHERE guild_id = ? AND owner_id = ? AND status = 'open'",
            (interaction.guild.id, interaction.user.id),
        )
        if existing:
            return await interaction.response.send_message(embed=error_embed("You already have an open ticket."), ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, name=settings.ticket_category)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        for role_name in settings.ticket_staff_roles:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}".lower().replace(" ", "-"),
            category=category,
            overwrites=overwrites,
            reason="Ticket created from panel",
        )
        await db.execute(
            "INSERT INTO tickets (channel_id, guild_id, owner_id, category, created_at) VALUES (?, ?, ?, ?, ?)",
            (channel.id, interaction.guild.id, interaction.user.id, category_name, utcnow()),
        )
        ticket = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ?", (channel.id,))
        await db.execute("INSERT INTO ticket_members (ticket_id, user_id) VALUES (?, ?)", (ticket["id"], interaction.user.id))
        await interaction.response.send_message(embed=success_embed("Ticket Created", f"Your ticket is {channel.mention}"), ephemeral=True)
        await channel.send(embed=base_embed("Ticket Opened", f"Owner: {interaction.user.mention}\nType: **{category_name}**", Colors.INFO))

    @app_commands.command(name="ticketpanel", description="Send the ticket panel.")
    async def ticketpanel(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Administrator permission required."), ephemeral=True)
        await interaction.response.send_message("Ticket panel posted.", ephemeral=True)
        await interaction.channel.send(embed=base_embed("Support Tickets", "Choose the ticket you need below.", Colors.PRIMARY), view=self.panel_view)

    @commands.hybrid_command(name="close", description="Close current ticket.")
    async def close(self, ctx: commands.Context) -> None:
        ticket = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'", (ctx.channel.id,))
        if not ticket:
            return await ctx.send(embed=error_embed("This is not an active ticket channel."))
        transcript = await build_transcript(ctx.channel)
        log_channel = discord.utils.get(ctx.guild.text_channels, name=settings.ticket_logs_channel)
        if log_channel:
            await log_channel.send(
                embed=base_embed("Ticket Closed", f"Channel: {ctx.channel.name}\nOwner ID: {ticket['owner_id']}", Colors.WARNING),
                file=transcript,
            )
        await db.execute("UPDATE tickets SET status = 'closed', closed_at = ? WHERE id = ?", (utcnow(), ticket["id"]))
        await ctx.send(embed=success_embed("Ticket Closed", "This ticket will be deleted in 5 seconds."))
        await ctx.channel.delete(delay=5)

    @commands.hybrid_command(name="adduser", description="Add user to ticket.")
    async def adduser(self, ctx: commands.Context, member: discord.Member) -> None:
        ticket = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'", (ctx.channel.id,))
        if not ticket:
            return await ctx.send(embed=error_embed("This is not an active ticket channel."))
        await ctx.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
        await db.execute("INSERT OR IGNORE INTO ticket_members (ticket_id, user_id) VALUES (?, ?)", (ticket["id"], member.id))
        await ctx.send(embed=success_embed("Member Added", f"{member.mention} can now access this ticket."))

    @commands.hybrid_command(name="removeuser", description="Remove user from ticket.")
    async def removeuser(self, ctx: commands.Context, member: discord.Member) -> None:
        ticket = await db.fetchone("SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'", (ctx.channel.id,))
        if not ticket:
            return await ctx.send(embed=error_embed("This is not an active ticket channel."))
        await ctx.channel.set_permissions(member, overwrite=None)
        await db.execute("DELETE FROM ticket_members WHERE ticket_id = ? AND user_id = ?", (ticket["id"], member.id))
        await ctx.send(embed=success_embed("Member Removed", f"{member.mention} was removed from this ticket."))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicketsCog(bot))
