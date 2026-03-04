from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
import db as database


async def _get_onboarding_config() -> dict:
    enabled = await database.get_config("WELCOME_ENABLED", "true")
    channel_id = await database.get_config("WELCOME_CHANNEL_ID", "")
    message = await database.get_config(
        "WELCOME_MESSAGE",
        "👋 Welcome to **{server}**, {user}! Feel free to ask me anything by mentioning me or using `/ask`.",
    )
    return {
        "enabled": enabled.lower() == "true",
        "channel_id": channel_id,
        "message": message,
    }


class Onboarding(commands.Cog):
    """New member onboarding and welcome flow."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = await _get_onboarding_config()
        if not cfg["enabled"]:
            return

        welcome_text = cfg["message"].replace("{user}", member.mention).replace(
            "{server}", member.guild.name
        )

        # --- Build welcome embed ---
        embed = discord.Embed(
            title=f"👋 Welcome to {member.guild.name}!",
            description=welcome_text,
            color=discord.Color.gold(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        # Server rules summary
        rules_channel = discord.utils.find(
            lambda c: "rule" in c.name.lower(), member.guild.text_channels
        )
        if rules_channel:
            embed.add_field(
                name="📜 Server Rules",
                value=f"Please read our rules in {rules_channel.mention}",
                inline=False,
            )

        # Links to key channels
        key_channels = []
        for keyword in ["general", "announcements", "intro", "help"]:
            ch = discord.utils.find(
                lambda c, kw=keyword: kw in c.name.lower(), member.guild.text_channels
            )
            if ch:
                key_channels.append(f"• {ch.mention}")
        if key_channels:
            embed.add_field(
                name="🔗 Key Channels",
                value="\n".join(key_channels[:4]),
                inline=False,
            )

        # Option to ask SparkSage
        embed.add_field(
            name="🤖 Need Help?",
            value="You can ask SparkSage anything! Just use `/ask` or mention me in any channel.",
            inline=False,
        )

        embed.set_footer(text="Powered by SparkSage 🤖")

        # Try configured welcome channel first
        channel = None
        if cfg["channel_id"]:
            try:
                channel = member.guild.get_channel(int(cfg["channel_id"]))
            except (ValueError, TypeError):
                pass

        # Fall back to system channel
        if not channel:
            channel = member.guild.system_channel

        if channel:
            await channel.send(embed=embed)
        else:
            # DM as last resort
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs disabled

    # ── /onboarding command group ──────────────────────────────────
    onboarding_group = app_commands.Group(
        name="onboarding", description="Configure the member welcome system"
    )

    @onboarding_group.command(name="status", description="Show current onboarding configuration")
    @app_commands.default_permissions(manage_guild=True)
    async def onboarding_status(self, interaction: discord.Interaction):
        cfg = await _get_onboarding_config()
        channel_id = cfg["channel_id"]
        channel_str = f"<#{channel_id}>" if channel_id else "System channel / DM fallback"

        embed = discord.Embed(title="🎉 Onboarding Configuration", color=discord.Color.gold())
        embed.add_field(name="Enabled", value="✅ Yes" if cfg["enabled"] else "❌ No", inline=True)
        embed.add_field(name="Welcome Channel", value=channel_str, inline=True)
        embed.add_field(name="Welcome Message", value=f"```{cfg['message'][:200]}```", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @onboarding_group.command(name="enable", description="Enable welcome messages")
    @app_commands.default_permissions(manage_guild=True)
    async def onboarding_enable(self, interaction: discord.Interaction):
        await database.set_config("WELCOME_ENABLED", "true")
        await interaction.response.send_message("✅ Onboarding welcome messages **enabled**.", ephemeral=True)

    @onboarding_group.command(name="disable", description="Disable welcome messages")
    @app_commands.default_permissions(manage_guild=True)
    async def onboarding_disable(self, interaction: discord.Interaction):
        await database.set_config("WELCOME_ENABLED", "false")
        await interaction.response.send_message("🔕 Onboarding welcome messages **disabled**.", ephemeral=True)

    @onboarding_group.command(name="setchannel", description="Set the welcome channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to post welcome messages in")
    async def onboarding_setchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await database.set_config("WELCOME_CHANNEL_ID", str(channel.id))
        await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}.", ephemeral=True)

    @onboarding_group.command(name="setmessage", description="Set the welcome message")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(message="Use {user} and {server} as placeholders")
    async def onboarding_setmessage(self, interaction: discord.Interaction, message: str):
        await database.set_config("WELCOME_MESSAGE", message)
        await interaction.response.send_message(f"✅ Welcome message updated:\n> {message}", ephemeral=True)

    @onboarding_group.command(name="test", description="Test the welcome message for yourself")
    @app_commands.default_permissions(manage_guild=True)
    async def onboarding_test(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        await self.on_member_join(interaction.user)
        await interaction.followup.send("✅ Test welcome message sent!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))