import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler # Keep this for explicit handler import
from pyrogram.types import Message # Keep this for explicit type hinting
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
        # Dictionary to hold futures for the ask method
        self.ask_futures = {}

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

    async def _ask_handler(self, client: Client, message: Message):
        """Internal handler for the ask method."""
        user_id = message.from_user.id
        if user_id in self.ask_futures:
            future = self.ask_futures.pop(user_id)
            if not future.done():
                future.set_result(message)

    async def ask(self, chat_id, text, filters=None, timeout=60) -> Message:
        """
        Custom implementation of the 'ask' method using a temporary handler.
        Sends a message and waits for the next message from the same user.
        """
        if chat_id in self.ask_futures:
            # If a previous ask is active, cancel it to prevent conflicts
            self.ask_futures.pop(chat_id).cancel()

        # 1. Send the prompt message
        sent_message = await self.send_message(chat_id, text)
        
        # 2. Create a Future to wait for the response
        future = asyncio.get_event_loop().create_future()
        self.ask_futures[chat_id] = future

        # 3. Add a temporary handler if it's not already there
        # We rely on the fact that the main bot instance is running and has a dispatcher
        if not hasattr(self, '_ask_handler_added'):
            # FIX: Use filters.private directly since it's now imported
            self.add_handler(MessageHandler(self._ask_handler, filters.private))
            setattr(self, '_ask_handler_added', True)

        # 4. Wait for the Future to be set or timeout
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None # Return None on timeout
        finally:
            # 5. Clean up
            if chat_id in self.ask_futures:
                self.ask_futures.pop(chat_id, None)
            try:
                await sent_message.delete()
            except Exception:
                pass


if __name__ == "__main__":
    Bot().run()

