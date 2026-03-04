import asyncio
import threading
import os
import uvicorn


def start_api_server():
    try:
        from api.main import create_app
        app = create_app()
        port = int(os.getenv("DASHBOARD_PORT", "8000"))
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except Exception as e:
        print(f"Failed to start API server: {e}")


def main():
    import config
    import providers

    available = providers.get_available_providers()

    print("=" * 50)
    print("  SparkSage — Bot + Dashboard Launcher")
    print("=" * 50)

    # Start FastAPI in a background thread.
    # uvicorn runs its own event loop inside that thread.
    # api/main.py lifespan handles db.init_db() on uvicorn's loop independently.
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    print(f"  API server starting on http://localhost:{port}")

    if not config.DISCORD_TOKEN:
        print("  WARNING: DISCORD_TOKEN not set — bot will not start.")
        try:
            api_thread.join()
        except KeyboardInterrupt:
            print("\nShutting down...")
        return

    if not available:
        print("  WARNING: No AI providers configured. Add at least one API key.")

    print(f"  Primary provider: {config.AI_PROVIDER}")
    print(f"  Fallback chain: {' -> '.join(available) if available else 'none'}")
    print("=" * 50)

    from bot import bot

    async def start_bot():
        import db
        # Reset the pool so it is always created fresh on THIS loop,
        # never reusing a pool that was created on uvicorn's background loop.
        await db.reset_pool()
        await db.init_db()
        await db.sync_env_to_db()

        for cog in ["cogs.faq", "cogs.review"]:
            try:
                await bot.load_extension(cog)
                print(f"Loaded cog: {cog}")
            except Exception as e:
                print(f"Failed to load {cog}: {e}")

        async def _sync_after_ready():
            await bot.wait_until_ready()
            try:
                synced = await bot.tree.sync()
                print(f"Slash commands synced: {len(synced)}")
                for cmd in synced:
                    print(f"  - /{cmd.name}")
            except Exception as e:
                print(f"Failed to sync slash commands: {e}")

        asyncio.create_task(_sync_after_ready())
        await bot.start(config.DISCORD_TOKEN)

    # Explicitly create a new event loop instead of relying on asyncio.run()
    # or get_event_loop(), both of which behave unpredictably on Python 3.13
    # Windows after a previous loop has been created and closed.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_bot())
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        loop.close()


if __name__ == "__main__":
    main()