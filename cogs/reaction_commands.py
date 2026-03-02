from __future__ import annotations

import asyncio
import discord
from discord.ext import commands

import providers

# Reaction → action mapping
REACTION_ACTIONS = {
    "📝": "summarize",
    "🔍": "explain",
    "🌐": "translate",
}


class ReactionCommands(commands.Cog):
    """Handle reaction-based commands on messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _chat(self, messages: list[dict], system_prompt: str) -> tuple[str, str]:
        """Run sync providers.chat() in a thread pool to avoid blocking the bot."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: providers.chat(messages, system_prompt)
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return

        emoji = str(payload.emoji)
        if emoji not in REACTION_ACTIONS:
            return

        # Fetch channel and message
        channel = self.bot.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Skip empty messages
        content = message.content.strip()
        if not content:
            await channel.send(
                f"<@{payload.user_id}> ⚠️ That message has no text to process.",
                delete_after=5,
            )
            return

        action = REACTION_ACTIONS[emoji]

        async with channel.typing():
            try:
                if action == "summarize":
                    result, _ = await self._chat(
                        messages=[{"role": "user", "content": f"Summarize this message in 2-3 sentences:\n\n{content}"}],
                        system_prompt="You are a helpful assistant. Provide concise summaries.",
                    )
                    title = "📝 Summary"
                elif action == "explain":
                    result, _ = await self._chat(
                        messages=[{"role": "user", "content": f"Explain this message clearly and simply:\n\n{content}"}],
                        system_prompt="You are a helpful assistant. Explain things clearly.",
                    )
                    title = "🔍 Explanation"
                elif action == "translate":
                    result, _ = await self._chat(
                        messages=[{"role": "user", "content": f"Detect the language and translate this to English. If it's already English, translate to Filipino:\n\n{content}"}],
                        system_prompt="You are a translation assistant.",
                    )
                    title = "🌐 Translation"
                else:
                    return

                embed = discord.Embed(
                    title=title,
                    description=result,
                    color=discord.Color.blue(),
                )
                member = message.guild.get_member(payload.user_id) if message.guild else None
                embed.set_footer(
                    text=f"Requested by {member.display_name if member else 'User'} • React with {emoji}"
                )
                embed.add_field(
                    name="Original message",
                    value=f"[Jump to message]({message.jump_url})",
                    inline=False,
                )
                await channel.send(embed=embed)

            except Exception as e:
                await channel.send(
                    f"<@{payload.user_id}> ❌ Failed to process: {e}",
                    delete_after=10,
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionCommands(bot), override=True)