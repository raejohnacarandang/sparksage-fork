from __future__ import annotations

import asyncio
import base64
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands

from openai import OpenAI
import config


def _get_gemini_client() -> OpenAI | None:
    """Get Gemini client for vision tasks."""
    if not config.GEMINI_API_KEY:
        return None
    return OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=config.GEMINI_API_KEY,
    )


async def _download_image_base64(url: str) -> tuple[str, str]:
    """Download image and return (base64_data, media_type)."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content_type = resp.headers.get("Content-Type", "image/png").split(";")[0]
            data = await resp.read()
            return base64.b64encode(data).decode("utf-8"), content_type


def _analyze_image_sync(image_b64: str, media_type: str, prompt: str) -> str:
    """Call Gemini Vision synchronously."""
    client = _get_gemini_client()
    if not client:
        raise RuntimeError("Gemini API key not configured. Add GEMINI_API_KEY to .env")

    response = client.chat.completions.create(
        model="models/gemini-2.0-flash-lite",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_b64}"
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content


class ImageAnalysis(commands.Cog):
    """Analyze images using Gemini Vision."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _analyze(self, image_url: str, prompt: str) -> str:
        """Download image and analyze with Gemini Vision."""
        image_b64, media_type = await _download_image_base64(image_url)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: _analyze_image_sync(image_b64, media_type, prompt)
        )

    @app_commands.command(name="analyze", description="Analyze an image using Gemini Vision AI")
    @app_commands.describe(
        image="Upload an image to analyze",
        prompt="What do you want to know about the image? (optional)",
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        prompt: str = "Describe this image in detail. Include any text, objects, people, colors, and context you can see.",
    ):
        await interaction.response.defer()

        # Validate file type
        if not image.content_type or not image.content_type.startswith("image/"):
            await interaction.followup.send(
                "❌ Please upload a valid image file (PNG, JPG, GIF, WEBP).",
                ephemeral=True,
            )
            return

        # Check file size (max 10MB)
        if image.size > 10 * 1024 * 1024:
            await interaction.followup.send(
                "❌ Image is too large. Please upload an image smaller than 10MB.",
                ephemeral=True,
            )
            return

        try:
            print(f"[analyze] Downloading image: {image.url}")
            result = await self._analyze(image.url, prompt)
            print(f"[analyze] Got result: {result[:100]}")

            embed = discord.Embed(
                title="🔎 Image Analysis",
                description=result,
                color=discord.Color.blue(),
            )
            embed.set_thumbnail(url=image.url)
            embed.add_field(name="Prompt", value=prompt[:200], inline=False)
            embed.set_footer(text=f"Powered by Gemini Vision • Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)

        except RuntimeError as e:
            print(f"[analyze] RuntimeError: {e}")
            await interaction.followup.send(f"⚙️ {e}", ephemeral=True)
        except Exception as e:
            print(f"[analyze] ERROR: {type(e).__name__}: {e}")
            await interaction.followup.send(f"❌ Analysis failed: {type(e).__name__}: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """React with 🔎 on a message with an image to auto-analyze it."""
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) != "🔎":
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Find image attachment
        image = next(
            (a for a in message.attachments if a.content_type and a.content_type.startswith("image/")),
            None,
        )

        if not image:
            await channel.send(
                f"<@{payload.user_id}> ⚠️ No image found in that message.",
                delete_after=5,
            )
            return

        async with channel.typing():
            try:
                print(f"[analyze reaction] Analyzing image: {image.url}")
                result = await self._analyze(
                    image.url,
                    "Describe this image in detail. Include any text, objects, colors, and context.",
                )
                embed = discord.Embed(
                    title="🔎 Image Analysis",
                    description=result,
                    color=discord.Color.blue(),
                )
                embed.set_thumbnail(url=image.url)
                member = message.guild.get_member(payload.user_id) if message.guild else None
                embed.set_footer(text=f"Requested by {member.display_name if member else 'User'} • Powered by Gemini Vision")
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[analyze reaction] ERROR: {type(e).__name__}: {e}")
                await channel.send(f"❌ Analysis failed: {type(e).__name__}: {e}", delete_after=10)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImageAnalysis(bot), override=True)
