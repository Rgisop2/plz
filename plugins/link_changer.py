# Link Auto-Changer Core Functionality
import asyncio
import random
import string
import time
import logging
from pyrogram import Client
from pyrogram.errors import FloodWait, UsernameOccupied
from plugins.database import db
from bot import Bot # Import the Bot class for type hinting/reference

class LinkChanger:
    def __init__(self):
        # Key: (user_id, channel_id), Value: asyncio.Task
        self.active_tasks = {}
        self.LOGGER = logging.getLogger(__name__)
        self.bot_client = None # Will be set in resume_all_rotations

    def generate_random_suffix(self):
        """Generate random 2 characters (letters or digits)"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=2))



    async def _log_update(self, channel_id, new_username, user_id, interval):
        """Send a success log message to the log channel."""
        user_name, _ = await db.get_user_info(user_id)
        text = f"""
        🔄 <b>Link changed successfully!</b>
        
        <b>Channel ID:</b> <code>{channel_id}</code>
        <b>New Username:</b> <code>@{new_username}</code>
        <b>User ID:</b> <code>{user_id}</code> ({user_name})
        <b>Interval:</b> {interval}s
        """
        await self.bot_client.log(text)

    async def _log_error(self, channel_id, user_id, error_message):
        """Send an error log message to the log channel."""
        user_name, _ = await db.get_user_info(user_id)
        text = f"""
        ⚠️ <b>Error changing link!</b>
        
        <b>Channel ID:</b> <code>{channel_id}</code>
        <b>User ID:</b> <code>{user_id}</code> ({user_name})
        <b>Reason:</b> {error_message}
        """
        await self.bot_client.log(text)

    async def change_channel_link(self, user_id, channel_id, base_username):
        """Change the channel's public link with random suffix using the user's session."""
        user_session = await db.get_session(user_id)
        if not user_session:
            return False, "User session not found"

        from config import API_ID, API_HASH
        client = Client(
            f"user_{user_id}_session", # Unique name for each session
            session_string=user_session,
            api_id=API_ID,
            api_hash=API_HASH,
            in_memory=True # Keep in memory to avoid session file conflicts
        )
        await client.start()

        try:
            max_attempts = 5
            for attempt in range(max_attempts):
                new_suffix = self.generate_random_suffix()
                new_username = f"{base_username}{new_suffix}"
                
                try:
                    await client.set_chat_username(channel_id, new_username)
                    await db.update_last_changed(channel_id, time.time())
                    return True, new_username
                
                except UsernameOccupied:
                    # Username taken, try another
                    self.LOGGER.info(f"Username @{new_username} occupied for {channel_id}. Trying again.")
                    continue
                
                except FloodWait as e:
                    await self._log_error(channel_id, user_id, f"FloodWait: {e.value}s")
                    # Re-raise to be handled by the rotation loop
                    raise e 
                
                except Exception as e:
                    # Other errors (e.g., not admin, not enough rights)
                    return False, str(e)
            
            return False, "Could not find available username after 5 attempts"

        finally:
            await client.stop()

    async def rotation_loop(self, user_id, channel_id, base_username, interval):
        """The main loop for a single channel rotation."""
        try:
            while True:
                try:
                    success, result = await self.change_channel_link(user_id, channel_id, base_username)
                    
                    if success:
                        new_username = result
                        self.LOGGER.info(f"Link changed for channel {channel_id} (User: {user_id}): @{new_username}")
                        await self._log_update(channel_id, new_username, user_id, interval)
                        
                    else:
                        self.LOGGER.warning(f"Failed to change link for channel {channel_id} (User: {user_id}): {result}")
                        await self._log_error(channel_id, user_id, result)

                    await asyncio.sleep(interval)

                except asyncio.CancelledError:
                    self.LOGGER.info(f"Rotation for {channel_id} (User: {user_id}) cancelled.")
                    break
                
                except FloodWait as e:
                    self.LOGGER.warning(f"FloodWait encountered for {channel_id}. Waiting for {e.value}s.")
                    # Wait for the required time plus a small buffer
                    await asyncio.sleep(e.value + 5) 
                    # Continue the loop to try again immediately after the wait
                    
                except Exception as e:
                    self.LOGGER.error(f"Critical error in rotation loop for {channel_id}: {e}")
                    await self._log_error(channel_id, user_id, f"Critical Error: {type(e).__name__} - {str(e)}")
                    # Wait for the interval before trying again
                    await asyncio.sleep(interval)
        
        finally:
            # Clean up the task from the active_tasks dictionary upon completion/cancellation
            task_key = (user_id, channel_id)
            if task_key in self.active_tasks:
                del self.active_tasks[task_key]
            await db.stop_channel(channel_id) # Mark as stopped in DB

    async def start_channel_rotation(self, user_id, channel_id, base_username, interval):
        """Start automatic link rotation for a channel."""
        task_key = (user_id, channel_id)
        
        if task_key in self.active_tasks:
            return False, "Channel rotation already active"
        
        user_session = await db.get_session(user_id)
        if not user_session:
            return False, "User session not found. Please /login."

        task = asyncio.create_task(
            self.rotation_loop(user_id, channel_id, base_username, interval),
            name=f"rotation_{user_id}_{channel_id}"
        )
        self.active_tasks[task_key] = task
        self.LOGGER.info(f"Started rotation task for {channel_id} (User: {user_id})")
        return True, "Channel rotation started"

    async def stop_channel_rotation(self, user_id, channel_id):
        """Stop automatic link rotation for a channel."""
        task_key = (user_id, channel_id)
        
        if task_key not in self.active_tasks:
            return False, "Channel rotation not active for this user."
        
        try:
            self.active_tasks[task_key].cancel()
            # The task will be removed from active_tasks in the rotation_loop's finally block
            await db.stop_channel(channel_id)
            return True, "Channel rotation stopped"
        except Exception as e:
            self.LOGGER.error(f"Error stopping task for {channel_id}: {e}")
            return False, str(e)

    async def resume_all_rotations(self, bot_client):
        """Resume all active channels on bot startup."""
        self.bot_client = bot_client # Store the bot instance for logging
        self.LOGGER.info("Resuming all active channel rotations...")
        try:
            channels = await db.get_all_active_channels()
            for channel in channels:
                user_id = channel['user_id']
                channel_id = channel['channel_id']
                base_username = channel['base_username']
                interval = channel['interval']
                
                success, result = await self.start_channel_rotation(
                    user_id, 
                    channel_id, 
                    base_username, 
                    interval
                )
                if success:
                    self.LOGGER.info(f"Resumed channel rotation for {channel_id} (User: {user_id})")
                else:
                    self.LOGGER.warning(f"Failed to resume channel {channel_id} (User: {user_id}): {result}")
        except Exception as e:
            self.LOGGER.error(f"Error resuming channels: {e}")

link_changer = LinkChanger()

