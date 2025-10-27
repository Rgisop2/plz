import asyncio
import logging
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL

logging.basicConfig(level=logging.INFO)

class Bot(Client):
    def __init__(self):
        super().__init__(
            "vj_link_changer_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=50,
            sleep_threshold=10,
        )
        self.LOGGER = logging.getLogger(__name__)

    async def start(self):
        await super().start()
        me = await self.get_me()
        self.username = '@' + me.username
        self.LOGGER.info(f"Bot @{me.username} started!")

        # Resume all rotations on startup
        from plugins.link_changer import link_changer
        await link_changer.resume_all_rotations(self)

    async def stop(self, *args):
        await super().stop()
        self.LOGGER.info("Bot stopped.")

    async def log(self, text):
        """Send a log message to the log channel."""
        if LOG_CHANNEL:
            try:
                await self.send_message(
                    chat_id=LOG_CHANNEL,
                    text=text,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                self.LOGGER.warning(f"Could not log to channel: {e}")

if __name__ == "__main__":
    Bot().run()

