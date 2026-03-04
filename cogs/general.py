from __future__ import annotations

import time
import discord
from discord.ext import commands
from discord import app_commands

import config
import providers
import db as database
from utils.rate_limiter import check_rate_limit


class General(commands.Cog):
    """General bot commands: /ask, /clear, /summarize, /provider."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /ask ──────────────────────────────────────────────────────

    @app_commands.command(name="ask", description="Ask SparkSage a question")
    @app_commands.describe(question="Your question for SparkSage")
    async def ask(self, interaction: discord.Interaction, question: str):
        from bot import ask_ai

        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild_id) if interaction.guild_id else None

        rate_error = check_rate_limit(user_id, guild_id)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            await database.log_event(
                "rate_limited",
                guild_id=guild_id,
                channel_id=str(interaction.channel_id),
                user_id=user_id,
            )
            return

        await interaction.response.defer()

        start = time.monotonic()
        response, provider_name = await ask_ai(
            interaction.channel_id, interaction.user.display_name, question
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        provider_label = config.PROVIDERS.get(provider_name, {}).get("name", provider_name)
        footer = f"\n-# Powered by {provider_label}"

        for i in range(0, len(response), 1900):
            chunk = response[i : i + 1900]
            if i + 1900 >= len(response):
                chunk += footer
            await interaction.followup.send(chunk)

        input_tokens = max(1, len(question) // 4)
        output_tokens = max(1, len(response) // 4)
        total_tokens = input_tokens + output_tokens

        await database.log_event(
            "command",
            guild_id=guild_id,
            channel_id=str(interaction.channel_id),
            user_id=user_id,
            username=interaction.user.display_name,
            provider=provider_name,
            tokens_used=total_tokens,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # ── /clear ────────────────────────────────────────────────────

    @app_commands.command(
        name="clear", description="Clear SparkSage's conversation memory for this channel"
    )
    async def clear(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        rate_error = check_rate_limit(user_id, guild_id)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            await database.log_event("rate_limited", guild_id=guild_id, channel_id=str(interaction.channel_id), user_id=user_id)
            return

        await database.clear_messages(str(interaction.channel_id))
        await interaction.response.send_message("✅ Conversation history cleared!")

        await database.log_event(
            "clear",
            guild_id=guild_id,
            channel_id=str(interaction.channel_id),
            user_id=user_id,
            username=interaction.user.display_name,
        )

    # ── /summarize ────────────────────────────────────────────────

    @app_commands.command(
        name="summarize", description="Summarize the recent conversation in this channel"
    )
    async def summarize(self, interaction: discord.Interaction):
        from bot import ask_ai, get_history

        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        rate_error = check_rate_limit(user_id, guild_id)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            await database.log_event("rate_limited", guild_id=guild_id, channel_id=str(interaction.channel_id), user_id=user_id)
            return

        await interaction.response.defer()

        history = await get_history(interaction.channel_id)
        if not history:
            await interaction.followup.send("No conversation history to summarize.")
            return

        summary_prompt = (
            "Please summarize the key points from this conversation so far "
            "in a concise bullet-point format."
        )

        start = time.monotonic()
        response, provider_name = await ask_ai(
            interaction.channel_id, interaction.user.display_name, summary_prompt
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        await interaction.followup.send(f"**Conversation Summary:**\n{response}")

        input_tokens = max(1, len(summary_prompt) // 4)
        output_tokens = max(1, len(response) // 4)

        await database.log_event(
            "summarize",
            guild_id=guild_id,
            channel_id=str(interaction.channel_id),
            user_id=user_id,
            username=interaction.user.display_name,
            provider=provider_name,
            tokens_used=input_tokens + output_tokens,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    # ── /provider ─────────────────────────────────────────────────

    @app_commands.command(
        name="provider", description="Show which AI provider SparkSage is currently using"
    )
    async def provider(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild_id) if interaction.guild_id else None
        rate_error = check_rate_limit(user_id, guild_id)
        if rate_error:
            await interaction.response.send_message(rate_error, ephemeral=True)
            await database.log_event("rate_limited", guild_id=guild_id, channel_id=str(interaction.channel_id), user_id=user_id)
            return

        primary = config.AI_PROVIDER
        provider_info = config.PROVIDERS.get(primary, {})
        available = providers.get_available_providers()

        msg = (
            f"**Current Provider:** {provider_info.get('name', primary)}\n"
            f"**Model:** `{provider_info.get('model', '?')}`\n"
            f"**Free:** {'Yes' if provider_info.get('free') else 'No (paid)'}\n"
            f"**Fallback Chain:** {' → '.join(available)}"
        )
        await interaction.response.send_message(msg)

        await database.log_event(
            "provider_check",
            guild_id=guild_id,
            channel_id=str(interaction.channel_id),
            user_id=user_id,
            username=interaction.user.display_name,
            provider=primary,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))