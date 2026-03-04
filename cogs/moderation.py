from __future__ import annotations

import json
import discord
from discord.ext import commands
from discord import app_commands

import providers
import db as database


async def _get_mod_config() -> dict:
    enabled = await database.get_config("MODERATION_ENABLED", "false")
    log_channel_id = await database.get_config("MOD_LOG_CHANNEL_ID", "")
    sensitivity = await database.get_config("MODERATION_SENSITIVITY", "medium")
    return {
        "enabled": enabled.lower() == "true",
        "log_channel_id": log_channel_id,
        "sensitivity": sensitivity,
    }


SENSITIVITY_THRESHOLDS = {
    "low": 0.8,
    "medium": 0.6,
    "high": 0.4,
}

MODERATION_PROMPT = """You are a content moderation assistant. Analyze the following message for:
- Toxicity, hate speech, or harassment
- Spam or excessive self-promotion
- NSFW or explicit content
- Threats or violent content

Respond ONLY with a valid JSON object in this exact format (no other text):
{"flagged": true/false, "reason": "brief reason or none", "severity": "low/medium/high", "score": 0.0-1.0}

Message to analyze:
"""


async def _check_message(content: str) -> dict | None:
    """Run content through AI moderation. Returns result dict or None on failure."""
    try:
        response, _ = providers.chat(
            [{"role": "user", "content": MODERATION_PROMPT + content}],
            "You are a content moderation system. Always respond with valid JSON only.",
        )
        # Strip markdown code blocks if present
        clean = response.strip().strip("```json").strip("```").strip()
        return json.loads(clean)
    except (RuntimeError, json.JSONDecodeError):
        return None


class Moderation(commands.Cog):
    """AI-powered content moderation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        # Skip short messages
        if len(message.content) < 10:
            return

        cfg = await _get_mod_config()
        if not cfg["enabled"] or not cfg["log_channel_id"]:
            return

        result = await _check_message(message.content)
        if not result:
            return

        if not result.get("flagged"):
            return

        # Check sensitivity threshold
        threshold = SENSITIVITY_THRESHOLDS.get(cfg["sensitivity"], 0.6)
        if result.get("score", 0) < threshold:
            return

        # Post to mod log channel
        log_channel = message.guild.get_channel(int(cfg["log_channel_id"]))
        if not log_channel:
            return

        severity = result.get("severity", "medium")
        severity_colors = {
            "low": discord.Color.yellow(),
            "medium": discord.Color.orange(),
            "high": discord.Color.red(),
        }
        severity_emojis = {"low": "🟡", "medium": "🟠", "high": "🔴"}

        embed = discord.Embed(
            title=f"{severity_emojis.get(severity, '🟠')} Flagged Message",
            color=severity_colors.get(severity, discord.Color.orange()),
        )
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Severity", value=severity.upper(), inline=True)
        embed.add_field(name="Reason", value=result.get("reason", "N/A"), inline=False)
        embed.add_field(
            name="Message",
            value=f"```{message.content[:500]}```",
            inline=False,
        )
        embed.add_field(
            name="Jump to Message",
            value=f"[Click here]({message.jump_url})",
            inline=False,
        )
        embed.set_footer(text="⚠️ For review only — no automatic action taken")

        await log_channel.send(embed=embed)

        # Log to analytics
        await database.log_event(
            "moderation",
            guild_id=str(message.guild.id),
            channel_id=str(message.channel.id),
            user_id=str(message.author.id),
            username=message.author.display_name,
        )

    # ── /moderation command group ────────────────────────────

    mod_group = app_commands.Group(
        name="moderation", description="Configure AI content moderation"
    )

    @mod_group.command(name="status", description="Show moderation configuration")
    @app_commands.default_permissions(manage_guild=True)
    async def mod_status(self, interaction: discord.Interaction):
        cfg = await _get_mod_config()
        channel_str = f"<#{cfg['log_channel_id']}>" if cfg["log_channel_id"] else "Not set"

        embed = discord.Embed(title="🛡️ Moderation Configuration", color=discord.Color.orange())
        embed.add_field(name="Enabled", value="✅ Yes" if cfg["enabled"] else "❌ No", inline=True)
        embed.add_field(name="Log Channel", value=channel_str, inline=True)
        embed.add_field(name="Sensitivity", value=cfg["sensitivity"].upper(), inline=True)
        embed.set_footer(text="Moderation flags messages for human review only — no auto-delete")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mod_group.command(name="toggle", description="Enable or disable AI moderation")
    @app_commands.default_permissions(manage_guild=True)
    async def mod_toggle(self, interaction: discord.Interaction):
        cfg = await _get_mod_config()
        new_state = not cfg["enabled"]
        await database.set_config("MODERATION_ENABLED", str(new_state).lower())
        state_str = "✅ enabled" if new_state else "❌ disabled"
        await interaction.response.send_message(f"AI moderation is now {state_str}.")

    @mod_group.command(name="channel", description="Set the mod log channel")
    @app_commands.describe(channel="Channel to post flagged message alerts in")
    @app_commands.default_permissions(manage_guild=True)
    async def mod_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ):
        await database.set_config("MOD_LOG_CHANNEL_ID", str(channel.id))
        await interaction.response.send_message(f"✅ Mod log channel set to {channel.mention}.")

    @mod_group.command(name="sensitivity", description="Set moderation sensitivity level")
    @app_commands.describe(level="low = only obvious violations, high = stricter flagging")
    @app_commands.choices(level=[
        app_commands.Choice(name="Low — obvious violations only", value="low"),
        app_commands.Choice(name="Medium — balanced (default)", value="medium"),
        app_commands.Choice(name="High — stricter, more flags", value="high"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def mod_sensitivity(self, interaction: discord.Interaction, level: str):
        await database.set_config("MODERATION_SENSITIVITY", level)
        await interaction.response.send_message(f"✅ Moderation sensitivity set to **{level.upper()}**.")

    @mod_group.command(name="test", description="Test moderation on a sample message")
    @app_commands.describe(message="Message to test against the moderation system")
    @app_commands.default_permissions(manage_guild=True)
    async def mod_test(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        result = await _check_message(message)
        if not result:
            await interaction.followup.send("❌ Moderation check failed.", ephemeral=True)
            return

        flagged = result.get("flagged", False)
        embed = discord.Embed(
            title="🧪 Moderation Test Result",
            color=discord.Color.red() if flagged else discord.Color.green(),
        )
        embed.add_field(name="Flagged", value="⚠️ Yes" if flagged else "✅ No", inline=True)
        embed.add_field(name="Severity", value=result.get("severity", "N/A").upper(), inline=True)
        embed.add_field(name="Score", value=str(result.get("score", "N/A")), inline=True)
        embed.add_field(name="Reason", value=result.get("reason", "N/A"), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot), override=True)