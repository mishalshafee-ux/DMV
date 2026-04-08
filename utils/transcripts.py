from __future__ import annotations

import io

import discord


async def build_transcript(channel: discord.TextChannel) -> discord.File:
    lines: list[str] = [f"Transcript for #{channel.name}", "=" * 60]
    async for message in channel.history(limit=None, oldest_first=True):
        content = message.clean_content or "[embed/attachment]"
        lines.append(f"[{message.created_at.isoformat()}] {message.author} ({message.author.id}): {content}")
    data = "\n".join(lines).encode("utf-8")
    return discord.File(io.BytesIO(data), filename=f"{channel.name}-transcript.txt")
