from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands, tasks
from discord import app_commands

import db as database

SCHEDULE_TABLE = """
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message TEXT NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    created_by TEXT,
    sent INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
async def init_schedule_table():
    pool = await database.get_pool()
    async with pool.acquire() as db:
        await db.execute(SCHEDULE_TABLE)


class Schedule(commands.Cog):
    """Schedule announcements to be posted at a specific time."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_scheduled.start()

    def cog_unload(self):
        self.check_scheduled.cancel()

    @tasks.loop(seconds=30)
    async def check_scheduled(self):
        """Check every 30 seconds for messages to send."""
        try:
            db = await database.get_db()
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            cursor = await db.execute(
                "SELECT * FROM scheduled_messages WHERE sent = 0 AND scheduled_time <= ?",
                (now,),
            )
            rows = await cursor.fetchall()

            for row in rows:
                row = dict(row)
                channel = self.bot.get_channel(int(row["channel_id"]))
                if channel:
                    try:
                        embed = discord.Embed(
                            description=row["message"],
                            color=discord.Color.blue(),
                        )
                        embed.set_footer(text="📅 Scheduled announcement")
                        await channel.send(embed=embed)
                    except Exception as e:
                        print(f"Failed to send scheduled message {row['id']}: {e}")

                # Mark as sent regardless
                await db.execute(
                    "UPDATE scheduled_messages SET sent = 1 WHERE id = ?",
                    (row["id"],),
                )
            await db.commit()
        except Exception as e:
            print(f"Schedule check error: {e}")

    @check_scheduled.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    # ── Commands ─────────────────────────────────────────────

    schedule_group = app_commands.Group(
        name="schedule", description="Schedule announcements"
    )

    @schedule_group.command(name="add", description="Schedule a message to be posted at a specific time")
    @app_commands.describe(
        message="The message to post",
        channel="Channel to post in",
        time="Date and time in UTC (format: YYYY-MM-DD HH:MM, e.g. 2025-12-31 09:00)",
    )
    @app_commands.default_permissions(manage_guild=True)
    async def schedule_add(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel,
        time: str,
    ):
        await interaction.response.defer()

        # Validate time format
        try:
            scheduled_dt = datetime.strptime(time, "%Y-%m-%d %H:%M")
            if scheduled_dt < datetime.utcnow():
                await interaction.followup.send("❌ Scheduled time must be in the future.")
                return
        except ValueError:
            await interaction.followup.send(
                "❌ Invalid time format. Use: `YYYY-MM-DD HH:MM` (e.g. `2025-12-31 09:00`)"
            )
            return

        db = await database.get_db()
        cursor = await db.execute(
            """INSERT INTO scheduled_messages (guild_id, channel_id, message, scheduled_time, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(interaction.guild_id),
                str(channel.id),
                message,
                time,
                str(interaction.user.id),
            ),
        )
        await db.commit()
        msg_id = cursor.lastrowid

        embed = discord.Embed(
            title="✅ Message Scheduled",
            color=discord.Color.green(),
        )
        embed.add_field(name="ID", value=f"`#{msg_id}`", inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Time (UTC)", value=f"`{time}`", inline=True)
        embed.add_field(name="Message", value=message[:500], inline=False)
        await interaction.followup.send(embed=embed)

    @schedule_group.command(name="list", description="List all scheduled messages")
    @app_commands.default_permissions(manage_guild=True)
    async def schedule_list(self, interaction: discord.Interaction):
        await interaction.response.defer()

        db = await database.get_db()
        cursor = await db.execute(
            "SELECT * FROM scheduled_messages WHERE guild_id = ? AND sent = 0 ORDER BY scheduled_time ASC",
            (str(interaction.guild_id),),
        )
        rows = await cursor.fetchall()

        if not rows:
            await interaction.followup.send("📭 No scheduled messages.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📅 Scheduled Messages",
            color=discord.Color.blue(),
        )
        for row in rows[:10]:
            row = dict(row)
            channel = interaction.guild.get_channel(int(row["channel_id"]))
            ch_name = channel.mention if channel else f"<#{row['channel_id']}>"
            embed.add_field(
                name=f"#{row['id']} — {row['scheduled_time']} UTC",
                value=f"**Channel:** {ch_name}\n**Message:** {row['message'][:100]}",
                inline=False,
            )
        await interaction.followup.send(embed=embed)

    @schedule_group.command(name="cancel", description="Cancel a scheduled message")
    @app_commands.describe(id="The ID of the scheduled message to cancel")
    @app_commands.default_permissions(manage_guild=True)
    async def schedule_cancel(self, interaction: discord.Interaction, id: int):
        db = await database.get_db()
        cursor = await db.execute(
            "SELECT * FROM scheduled_messages WHERE id = ? AND guild_id = ? AND sent = 0",
            (id, str(interaction.guild_id)),
        )
        row = await cursor.fetchone()

        if not row:
            await interaction.response.send_message(
                f"❌ Scheduled message `#{id}` not found or already sent.", ephemeral=True
            )
            return

        await db.execute(
            "DELETE FROM scheduled_messages WHERE id = ?", (id,)
        )
        await db.commit()
        await interaction.response.send_message(
            f"✅ Scheduled message `#{id}` cancelled.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await init_schedule_table()
    await bot.add_cog(Schedule(bot), override=True)