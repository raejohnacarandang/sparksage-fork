from __future__ import annotations

import asyncio
import discord
from discord.ext import commands
from discord import app_commands

import providers


class ThreadSummarizer(commands.Cog):
    """Auto-summarize forum threads and regular threads."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _chat(self, messages: list[dict], system_prompt: str) -> str:
        loop = asyncio.get_event_loop()
        result, _ = await loop.run_in_executor(
            None, lambda: providers.chat(messages, system_prompt)
        )
        return result

    async def _collect_thread_messages(self, thread: discord.Thread, limit: int = 100) -> list[str]:
        """Collect messages from a thread."""
        messages = []
        async for msg in thread.history(limit=limit, oldest_first=True):
            if msg.author.bot:
                continue
            content = msg.content.strip()
            if content:
                messages.append(f"{msg.author.display_name}: {content}")
        return messages

    # ── Slash Command ─────────────────────────────────────────

    @app_commands.command(name="summarize-thread", description="Summarize the current thread or forum post")
    @app_commands.describe(limit="Number of messages to include (default: 100)")
    async def summarize_thread(self, interaction: discord.Interaction, limit: int = 100):
        await interaction.response.defer()

        channel = interaction.channel

        # Must be inside a thread
        if not isinstance(channel, discord.Thread):
            await interaction.followup.send(
                "❌ This command only works inside a thread or forum post.",
                ephemeral=True,
            )
            return

        messages = await self._collect_thread_messages(channel, limit=limit)

        if not messages:
            await interaction.followup.send(
                "❌ No messages found in this thread.",
                ephemeral=True,
            )
            return

        conversation = "\n".join(messages)

        async with interaction.channel.typing():
            summary = await self._chat(
                messages=[{
                    "role": "user",
                    "content": f"Summarize this thread conversation. Include: main topic, key points discussed, conclusions or decisions made, and any action items.\n\nThread: {channel.name}\n\n{conversation}"
                }],
                system_prompt="You are an expert at summarizing conversations. Be concise but comprehensive. Use bullet points for key points.",
            )

        embed = discord.Embed(
            title=f"📋 Thread Summary: {channel.name}",
            description=summary,
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Based on {len(messages)} messages • Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    # ── Auto-summarize new forum posts ────────────────────────

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Auto-post a summary prompt when a new forum thread is created."""
        # Only for forum channels
        if not isinstance(thread.parent, discord.ForumChannel):
            return

        # Wait a bit for the first message to be posted
        await asyncio.sleep(2)

        messages = await self._collect_thread_messages(thread, limit=10)
        if not messages:
            return

        # Only summarize if there's enough content
        total_chars = sum(len(m) for m in messages)
        if total_chars < 100:
            return

        conversation = "\n".join(messages)

        try:
            summary = await self._chat(
                messages=[{
                    "role": "user",
                    "content": f"Summarize this forum post in 2-3 sentences. Focus on what the poster is asking or discussing.\n\n{conversation}"
                }],
                system_prompt="You are a helpful assistant. Summarize forum posts briefly.",
            )

            embed = discord.Embed(
                description=f"**📋 Auto-Summary**\n{summary}",
                color=discord.Color.greyple(),
            )
            embed.set_footer(text="Use /summarize-thread anytime for a full summary")
            await thread.send(embed=embed)

        except Exception as e:
            print(f"Auto-summarize failed for thread {thread.name}: {e}")

    # ── Reaction-based thread summary ─────────────────────────

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """React with 📋 on any message to summarize the thread it's in."""
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "📋":
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.Thread):
            return

        messages = await self._collect_thread_messages(channel, limit=100)
        if not messages:
            return

        conversation = "\n".join(messages)

        try:
            summary = await self._chat(
                messages=[{
                    "role": "user",
                    "content": f"Summarize this thread conversation:\n\nThread: {channel.name}\n\n{conversation}"
                }],
                system_prompt="You are an expert at summarizing conversations. Be concise but comprehensive.",
            )

            embed = discord.Embed(
                title=f"📋 Thread Summary: {channel.name}",
                description=summary,
                color=discord.Color.blue(),
            )
            member = channel.guild.get_member(payload.user_id) if channel.guild else None
            embed.set_footer(text=f"Requested by {member.display_name if member else 'User'}")
            await channel.send(embed=embed)

        except Exception as e:
            await channel.send(f"❌ Failed to summarize: {e}", delete_after=10)


async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadSummarizer(bot), override=True)