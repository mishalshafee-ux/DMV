from __future__ import annotations

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from database import db
from utils.embeds import base_embed, error_embed, success_embed, Colors


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class DMVApplicationModal(discord.ui.Modal, title="DMV Staff Application"):
    why = discord.ui.TextInput(label="Why do you want to join DMV?", style=discord.TextStyle.paragraph, max_length=400)
    experience = discord.ui.TextInput(label="Relevant experience?", style=discord.TextStyle.paragraph, max_length=400)
    availability = discord.ui.TextInput(label="Availability?", style=discord.TextStyle.short, max_length=100)

    def __init__(self, cog: "ApplicationsCog") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await db.execute(
            "INSERT INTO applications (user_id, username, why_join, experience, availability, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (interaction.user.id, str(interaction.user), self.why.value, self.experience.value, self.availability.value, utcnow()),
        )
        row = await db.fetchone("SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC LIMIT 1", (interaction.user.id,))
        channel = discord.utils.get(interaction.guild.text_channels, name=settings.applications_channel)
        if channel:
            embed = base_embed("New DMV Application", color=Colors.INFO)
            embed.add_field(name="Applicant", value=interaction.user.mention, inline=False)
            embed.add_field(name="Why Join", value=self.why.value, inline=False)
            embed.add_field(name="Experience", value=self.experience.value, inline=False)
            embed.add_field(name="Availability", value=self.availability.value, inline=False)
            embed.add_field(name="Application ID", value=str(row["id"]), inline=False)
            await channel.send(
                embed=embed,
                view=ApplicationReviewView(self.cog, row["id"], interaction.user.id),
            )
        await interaction.response.send_message(embed=success_embed("Application Submitted", "Your DMV application was sent to staff."), ephemeral=True)


class ApplicationPanelView(discord.ui.View):
    def __init__(self, cog: "ApplicationsCog") -> None:
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="Apply", style=discord.ButtonStyle.primary, custom_id="dmv_apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(DMVApplicationModal(self.cog))


class ApplicationReviewView(discord.ui.View):
    def __init__(self, cog: "ApplicationsCog", application_id: int, user_id: int) -> None:
        super().__init__(timeout=None)
        self.cog = cog
        self.application_id = application_id
        self.user_id = user_id

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, custom_id="apply_accept_dynamic")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Administrator permission required."), ephemeral=True)
        await db.execute("UPDATE applications SET status = 'accepted', reviewer_id = ? WHERE id = ?", (interaction.user.id, self.application_id))
        member = interaction.guild.get_member(self.user_id)
        role = discord.utils.get(interaction.guild.roles, name=settings.applicant_role)
        if member and role:
            await member.add_roles(role, reason="DMV application accepted")
        await interaction.response.send_message(embed=success_embed("Application Accepted", f"Application `{self.application_id}` accepted."), ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id="apply_deny_dynamic")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Administrator permission required."), ephemeral=True)
        await db.execute("UPDATE applications SET status = 'denied', reviewer_id = ? WHERE id = ?", (interaction.user.id, self.application_id))
        await interaction.response.send_message(embed=success_embed("Application Denied", f"Application `{self.application_id}` denied."), ephemeral=True)


class ApplicationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.panel_view = ApplicationPanelView(self)

    async def cog_load(self) -> None:
        self.bot.add_view(self.panel_view)

    @app_commands.command(name="applydmv", description="Send the DMV application panel.")
    async def applydmv(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Administrator permission required."), ephemeral=True)
        embed = base_embed("DMV Staff Applications", "Press **Apply** to submit your application.", Colors.PRIMARY)
        await interaction.response.send_message("Application panel posted.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=self.panel_view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ApplicationsCog(bot))
