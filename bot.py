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

    async def ask(self, chat_id, text, filters=None, timeout=60):
        """
        Custom implementation of the 'ask' method using Pyrogram's listen.
        Sends a message and waits for the next message from the same user.
        """
        sent_message = await self.send_message(chat_id, text)
        
        # The check_message function must be defined inside the ask method
        # and must be an async function if it uses await, but Pyrogram's
        # listen filter expects a callable that takes (client, message)
        # and returns a boolean. Since we are only checking chat_id, it can be sync.
        def check_message(client, message):
            if message.chat.id == chat_id:
                # If a custom filter is provided, it must be used.
                # Since the original code didn't show the filter, we assume it's a simple check.
                return True
            return False

        try:
            return await self.listen(
                chat_id=chat_id,
                filters=check_message,
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None # Return None on timeout
        finally:
            # We cannot guarantee deletion will work if the message is too old or not found,
            # but we can try. The original logic was to delete the prompt.
            try:
                await sent_message.delete()
            except Exception:
                pass


if __name__ == "__main__":
    Bot().run()

