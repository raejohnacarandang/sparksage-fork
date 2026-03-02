from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

import db as database

# Keys that are configurable per guild
GUILD_SETTINGS = {
    "SYSTEM_PROMPT": "AI system prompt / personality",
    "WELCOME_ENABLED": "Enable welcome messages (true/false)",
    "WELCOME_CHANNEL_ID": "Welcome channel ID",
    "WELCOME_MESSAGE": "Welcome message template ({user}, {server})",
    "DIGEST_ENABLED": "Enable daily digest (true/false)",
    "DIGEST_CHANNEL_ID": "Digest channel ID",
    "DIGEST_TIME": "Digest time in UTC (HH:MM)",
    "MODERATION_ENABLED": "Enable AI moderation (true/false)",
    "MOD_LOG_CHANNEL_ID": "Mod log channel ID",
    "MODERATION_SENSITIVITY": "Moderation sensitivity (low/medium/high)",
    "MAX_TOKENS": "Max tokens per AI response",
    "BOT_PREFIX": "Bot command prefix",
}


class GuildSettings(commands.Cog):
    """Per-guild configuration management."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    settings_group = app_commands.Group(
        name="settings",
        description="Manage per-server bot settings",
    )

    @settings_group.command(name="set", description="Set a server-specific setting")
    @app_commands.describe(
        key="Setting name",
        value="Setting value",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def settings_set(self, interaction: discord.Interaction, key: str, value: str):
        key = key.upper()
        if key not in GUILD_SETTINGS:
            valid = "\n".join([f"`{k}` — {v}" for k, v in GUILD_SETTINGS.items()])
            await interaction.response.send_message(
                f"❌ Unknown setting `{key}`.\n\n**Available settings:**\n{valid}",
                ephemeral=True,
            )
            return

        await database.set_guild_config(str(interaction.guild_id), key, value)
        await interaction.response.send_message(
            f"✅ `{key}` set to `{value}` for **{interaction.guild.name}**",
            ephemeral=True,
        )

    @settings_group.command(name="get", description="Get a server-specific setting")
    @app_commands.describe(key="Setting name")
    @app_commands.default_permissions(manage_guild=True)
    async def settings_get(self, interaction: discord.Interaction, key: str):
        key = key.upper()
        value = await database.get_guild_config(str(interaction.guild_id), key)
        if value is None:
            await interaction.response.send_message(
                f"⚠️ `{key}` is not set for this server.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"**{key}** = `{value}`", ephemeral=True
        )

    @settings_group.command(name="list", description="List all settings for this server")
    @app_commands.default_permissions(manage_guild=True)
    async def settings_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)
        db = await database.get_db()
        cursor = await db.execute(
            "SELECT key, value FROM guild_config WHERE guild_id = ?", (guild_id,)
        )
        rows = await cursor.fetchall()

        embed = discord.Embed(
            title=f"⚙️ Settings for {interaction.guild.name}",
            color=discord.Color.blue(),
        )

        if not rows:
            embed.description = "No custom settings — using global defaults.\nUse `/settings set` to configure."
        else:
            for row in rows:
                embed.add_field(
                    name=row["key"],
                    value=f"`{row['value']}`",
                    inline=True,
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @settings_group.command(name="reset", description="Reset a setting to global default")
    @app_commands.describe(key="Setting to reset (or 'all' to reset everything)")
    @app_commands.default_permissions(manage_guild=True)
    async def settings_reset(self, interaction: discord.Interaction, key: str):
        if key.lower() == "all":
            await database.reset_guild_config(str(interaction.guild_id))
            await interaction.response.send_message(
                f"✅ All settings reset to global defaults for **{interaction.guild.name}**",
                ephemeral=True,
            )
        else:
            await database.delete_guild_config(str(interaction.guild_id), key.upper())
            await interaction.response.send_message(
                f"✅ `{key.upper()}` reset to global default.",
                ephemeral=True,
            )

    @settings_group.command(name="info", description="Show all available settings")
    async def settings_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ Available Settings",
            description="Use `/settings set <key> <value>` to configure.",
            color=discord.Color.blue(),
        )
        for key, desc in GUILD_SETTINGS.items():
            embed.add_field(name=f"`{key}`", value=desc, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GuildSettings(bot), override=True)