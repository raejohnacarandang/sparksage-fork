from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

import config
import providers
import db as database

REVIEW_SYSTEM_PROMPT = """You are a senior software engineer conducting a thorough code review.
Analyze the provided code and respond with the following sections using markdown:

## 🐛 Bugs & Errors
List any bugs, logic errors, or potential exceptions.

## ✨ Style & Best Practices
Comment on naming, formatting, readability, and language conventions.

## ⚡ Performance
Highlight any inefficiencies, unnecessary operations, or better algorithms.

## 🔒 Security
Flag any security vulnerabilities, injection risks, or unsafe patterns.

## ✅ Suggestions
Provide a short improved version or key recommendations.

Be specific, constructive, and concise. Use code blocks with language tags where helpful."""


class CodeReview(commands.Cog):
    """Code review commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="review",
        description="Get an AI code review for a snippet of code",
    )
    @app_commands.describe(
        code="Paste your code here",
        language="Programming language (optional, e.g. python, javascript)",
    )
    async def review(
        self,
        interaction: discord.Interaction,
        code: str,
        language: str = "",
    ):
        await interaction.response.defer()

        lang_hint = f"Language: {language}\n\n" if language else ""
        user_message = f"{lang_hint}Please review this code:\n\n```{language}\n{code}\n```"

        messages = [{"role": "user", "content": user_message}]

        try:
            response, provider_name = providers.chat(messages, REVIEW_SYSTEM_PROMPT)
        except RuntimeError as e:
            await interaction.followup.send(f"❌ All providers failed: {e}")
            return

        # Store in conversation history tagged as code review
        await database.add_message(
            str(interaction.channel_id),
            "user",
            f"[CODE REVIEW] {interaction.user.display_name}: {code[:200]}...",
        )
        await database.add_message(
            str(interaction.channel_id),
            "assistant",
            response,
            provider=provider_name,
        )

        await database.log_event(
            "command",
            guild_id=str(interaction.guild_id) if interaction.guild_id else None,
            channel_id=str(interaction.channel_id),
            user_id=str(interaction.user.id),
            username=interaction.user.display_name,
            provider=provider_name,
        )

        provider_label = config.PROVIDERS.get(provider_name, {}).get("name", provider_name)
        footer = f"\n-# 🔍 Code review powered by {provider_label}"

        # Send in chunks respecting Discord's 2000-char limit
        chunks = []
        current = f"**Code Review** for `{language or 'your snippet'}`:\n\n"
        for line in response.splitlines(keepends=True):
            if len(current) + len(line) > 1900:
                chunks.append(current)
                current = ""
            current += line
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                chunk += footer
            await interaction.followup.send(chunk)


async def setup(bot: commands.Bot):
    await bot.add_cog(CodeReview(bot), override=True)