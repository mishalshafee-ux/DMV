from __future__ import annotations

import discord
from discord.ext import commands

from config import settings


def member_has_named_role(member: discord.Member, allowed: list[str]) -> bool:
    names = {role.name.lower() for role in member.roles}
    return any(role.lower() in names for role in allowed)


def is_admin_member(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or member_has_named_role(member, settings.admin_roles)


def is_dmv_member(member: discord.Member) -> bool:
    return is_admin_member(member) or member_has_named_role(member, settings.dmv_staff_roles)


def is_police_member(member: discord.Member) -> bool:
    return is_admin_member(member) or member_has_named_role(member, settings.police_roles)


def admin_check():
    async def predicate(ctx: commands.Context) -> bool:
        return isinstance(ctx.author, discord.Member) and is_admin_member(ctx.author)
    return commands.check(predicate)


def dmv_check():
    async def predicate(ctx: commands.Context) -> bool:
        return isinstance(ctx.author, discord.Member) and is_dmv_member(ctx.author)
    return commands.check(predicate)


def police_check():
    async def predicate(ctx: commands.Context) -> bool:
        return isinstance(ctx.author, discord.Member) and is_police_member(ctx.author)
    return commands.check(predicate)
