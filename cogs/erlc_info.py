cat > cogs/erlc_info.py <<'PY'
from __future__ import annotations

import aiohttp
import discord
from discord.ext import commands

from config import settings
from utils.checks import police_check
from utils.embeds import base_embed, error_embed, Colors

API_BASE = "https://api.policeroleplay.community/v1"

class ERLCInfo(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _headers(self) -> dict[str, str]:
        return {
            "server-key": settings.erlc_server_key,
            "Accept": "application/json",
        }

    async def _get(self, endpoint: str):
        if not settings.erlc_server_key:
            return None, "ERLC_SERVER_KEY is missing in .env"
        url = f"{API_BASE}{endpoint}"
        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=self._headers()) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200:
                        message = data.get("message") or data.get("error") or f"HTTP {resp.status}"
                        return None, message
                    return data, None
        except Exception as exc:
            return None, str(exc)

    @commands.hybrid_command(name="erlcserver", description="View ER:LC server info.")
    @police_check()
    async def erlcserver(self, ctx: commands.Context) -> None:
        data, error = await self._get("/server")
        if error:
            return await ctx.send(embed=error_embed(f"ER:LC API error: {error}"))
        embed = base_embed("ER:LC Server Status", color=Colors.INFO)
        embed.add_field(name="Server Name", value=data.get("Name", "Unknown"), inline=False)
        embed.add_field(name="Join Key", value=data.get("JoinKey", "Hidden/Unavailable"), inline=True)
        embed.add_field(name="Current Players", value=str(data.get("CurrentPlayers", "Unknown")), inline=True)
        embed.add_field(name="Max Players", value=str(data.get("MaxPlayers", "Unknown")), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="erlcplayers", description="List players in ER:LC server.")
    @police_check()
    async def erlcplayers(self, ctx: commands.Context) -> None:
        data, error = await self._get("/server/players")
        if error:
            return await ctx.send(embed=error_embed(f"ER:LC API error: {error}"))
        if not data:
            return await ctx.send(embed=error_embed("No players found or server is offline."))
        lines = []
        for i, player in enumerate(data[:20], start=1):
            lines.append(f"**{i}.** {player.get('Player')} | `{player.get('Team')}`")
        embed = base_embed("ER:LC Players", "\n".join(lines), Colors.INFO)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="erlcmdt", description="Police MDT style ER:LC lookup.")
    @police_check()
    async def erlcmdt(self, ctx: commands.Context, *, username: str) -> None:
        players, error = await self._get("/server/players")
        if error:
            return await ctx.send(embed=error_embed(f"ER:LC API error: {error}"))
        vehicles, _ = await self._get("/server/vehicles")
        vehicles = vehicles or []
        target = None
        for player in players:
            if str(player.get("Player", "")).lower() == username.lower():
                target = player
                break
        if not target:
            return await ctx.send(embed=error_embed(f"`{username}` is not in the ER:LC server right now."))
        owned_vehicles = [v for v in vehicles if str(v.get("Owner", "")).lower() == str(target.get("Player", "")).lower()]
        embed = base_embed("ER:LC MDT Lookup", color=Colors.WARNING)
        embed.add_field(name="Player", value=target.get("Player", "Unknown"), inline=True)
        embed.add_field(name="Team", value=target.get("Team", "Unknown"), inline=True)
        embed.add_field(name="Permission", value=str(target.get("Permission", "Unknown")), inline=True)
        callsign = target.get("Callsign")
        if callsign:
            embed.add_field(name="Callsign", value=str(callsign), inline=True)
        if owned_vehicles:
            vehicle_list = "\n".join(f"- {v.get('Name', 'Unknown')}" for v in owned_vehicles[:10])
        else:
            vehicle_list = "No spawned vehicles found"
        embed.add_field(name="Spawned Vehicles", value=vehicle_list, inline=False)
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ERLCInfo(bot))
PY
