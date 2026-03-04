from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

import providers
import db as database

TRANSLATE_SYSTEM_PROMPT = """You are a professional translator. 
Translate the given text accurately and naturally.
Respond with ONLY the translated text — no explanations, no notes, no original text."""

DETECT_PROMPT = """Detect the language of the following text and translate it to English.
Respond in this exact format:
LANGUAGE: <detected language>
TRANSLATION: <english translation>

If the text is already in English, respond:
LANGUAGE: English
TRANSLATION: <original text>"""


async def _translate(text: str, target_language: str) -> tuple[str, str]:
    """Translate text to target language. Returns (translated, provider_name)."""
    prompt = f"Translate the following text to {target_language}:\n\n{text}"
    response, provider_name = providers.chat(
        [{"role": "user", "content": prompt}],
        TRANSLATE_SYSTEM_PROMPT,
    )
    return response, provider_name


async def _detect_and_translate(text: str) -> dict | None:
    """Detect language and translate to English. Returns dict or None."""
    try:
        response, _ = providers.chat(
            [{"role": "user", "content": DETECT_PROMPT + "\n\n" + text}],
            "You are a language detection and translation assistant.",
        )
        lines = response.strip().splitlines()
        parsed = {}
        for line in lines:
            if ":" in line:
                key, _, val = line.partition(":")
                parsed[key.strip()] = val.strip()
        if "LANGUAGE" in parsed and "TRANSLATION" in parsed:
            return parsed
    except RuntimeError:
        pass
    return None


class Translate(commands.Cog):
    """Translation commands with optional auto-translate channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="translate", description="Translate text to another language")
    @app_commands.describe(
        text="The text to translate",
        language="Target language (e.g. Filipino, Spanish, Japanese, French)",
    )
    async def translate(self, interaction: discord.Interaction, text: str, language: str):
        await interaction.response.defer()

        try:
            response, provider_name = await _translate(text, language)
        except RuntimeError as e:
            await interaction.followup.send(f"❌ Translation failed: {e}")
            return

        import config
        provider_label = config.PROVIDERS.get(provider_name, {}).get("name", provider_name)

        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Original", value=f"```{text[:500]}```", inline=False)
        embed.add_field(name=f"→ {language}", value=f"```{response[:500]}```", inline=False)
        embed.set_footer(text=f"Translated by SparkSage · Powered by {provider_label}")
        await interaction.followup.send(embed=embed)

        await database.log_event(
            "command",
            guild_id=str(interaction.guild_id) if interaction.guild_id else None,
            channel_id=str(interaction.channel_id),
            user_id=str(interaction.user.id),
            username=interaction.user.display_name,
            provider=provider_name,
        )

    # ── Auto-translate commands ──────────────────────────────

    translate_group = app_commands.Group(
        name="autotranslate", description="Configure auto-translation for channels"
    )

    @translate_group.command(name="enable", description="Enable auto-translation in this channel")
    @app_commands.describe(language="Language to translate messages into (default: English)")
    @app_commands.default_permissions(manage_guild=True)
    async def autotranslate_enable(
        self, interaction: discord.Interaction, language: str = "English"
    ):
        await database.set_config(f"AUTOTRANSLATE_{interaction.channel_id}", language)
        await interaction.response.send_message(
            f"✅ Auto-translation enabled in {interaction.channel.mention} → **{language}**"
        )

    @translate_group.command(name="disable", description="Disable auto-translation in this channel")
    @app_commands.default_permissions(manage_guild=True)
    async def autotranslate_disable(self, interaction: discord.Interaction):
        db = await database.get_db()
        await db.execute(
            "DELETE FROM config WHERE key = ?",
            (f"AUTOTRANSLATE_{interaction.channel_id}",),
        )
        await db.commit()
        await interaction.response.send_message(
            f"✅ Auto-translation disabled in {interaction.channel.mention}."
        )

    @translate_group.command(name="status", description="Check auto-translation status for this channel")
    async def autotranslate_status(self, interaction: discord.Interaction):
        lang = await database.get_config(f"AUTOTRANSLATE_{interaction.channel_id}")
        if lang:
            await interaction.response.send_message(
                f"🌐 Auto-translation is **enabled** in this channel → **{lang}**",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "Auto-translation is **disabled** in this channel.", ephemeral=True
            )

    # ── Auto-translate listener ──────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild or len(message.content) < 5:
            return

        target_lang = await database.get_config(f"AUTOTRANSLATE_{message.channel.id}")
        if not target_lang:
            return

        result = await _detect_and_translate(message.content)
        if not result:
            return

        detected = result.get("LANGUAGE", "Unknown")

        # Skip if already in target language
        if detected.lower() == target_lang.lower():
            return

        translation = result.get("TRANSLATION", "")
        if not translation or translation == message.content:
            return

        embed = discord.Embed(
            description=translation,
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"🌐 Auto-translated from {detected} → {target_lang}")
        await message.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Translate(bot), override=True)