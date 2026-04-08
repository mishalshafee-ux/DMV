from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from utils.embeds import base_embed, error_embed, success_embed, Colors


class VerifyModal(discord.ui.Modal, title="Server Verification"):
    answer = discord.ui.TextInput(label="Verification Answer", placeholder="Enter the correct answer")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.answer.value.strip().lower() != settings.verify_answer.strip().lower():
            return await interaction.response.send_message(embed=error_embed("Incorrect verification answer."), ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(embed=error_embed("Member lookup failed."), ephemeral=True)
        unverified = discord.utils.get(interaction.guild.roles, name=settings.unverified_role)
        verified = discord.utils.get(interaction.guild.roles, name=settings.verified_role)
        try:
            if unverified:
                await interaction.user.remove_roles(unverified, reason="Verification complete")
            if verified:
                await interaction.user.add_roles(verified, reason="Verification complete")
        except discord.HTTPException:
            return await interaction.response.send_message(embed=error_embed("I could not update your roles."), ephemeral=True)
        await interaction.response.send_message(embed=success_embed("Verified", "You now have access to the server."), ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(VerifyModal())


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.view = VerifyView()

    async def cog_load(self) -> None:
        self.bot.add_view(self.view)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        role = discord.utils.get(member.guild.roles, name=settings.unverified_role)
        if role:
            try:
                await member.add_roles(role, reason="Auto assign unverified")
            except discord.HTTPException:
                pass
        channel = discord.utils.get(member.guild.text_channels, name=settings.welcome_channel)
        if channel:
            embed = base_embed(
                "Welcome to the DMV Roleplay Server",
                f"Please verify to access the server.\n\n**Rules:**\n1. Respect staff\n2. No exploit abuse\n3. Use DMV systems properly\n\n**Question:** {settings.verify_question}",
                Colors.INFO,
            )
            await channel.send(content=member.mention, embed=embed, view=self.view)

    @app_commands.command(name="sendverification", description="Send the verification panel.")
    async def sendverification(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(embed=error_embed("Administrator permission required."), ephemeral=True)
        embed = base_embed("Verification Panel", f"Click below to verify.\n\n**Question:** {settings.verify_question}", Colors.SUCCESS)
        await interaction.response.send_message("Verification panel sent.", ephemeral=True)
        await interaction.channel.send(embed=embed, view=self.view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Verification(bot))
