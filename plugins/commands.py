import asyncio 
from pyrogram import Client, filters, enums
from config import LOG_CHANNEL, API_ID, API_HASH
from plugins.database import db
from plugins.link_changer import link_changer
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

LOG_TEXT = """<b>#NewUser
    
ID - <code>{}</code>

Nᴀᴍᴇ - {}</b>
"""

@Client.on_message(filters.command('start'))
async def start_message(c, m):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id, m.from_user.first_name)
        await c.send_message(LOG_CHANNEL, LOG_TEXT.format(m.from_user.id, m.from_user.mention))
    
    await m.reply_photo(f"https://te.legra.ph/file/119729ea3cdce4fefb6a1.jpg",
        caption=f"<b>Hello {m.from_user.mention} 👋\n\nI Am Public Link Auto-Changer Bot. I Can Automatically Change Your Channel Public Links.\n\nUse /help to see all commands.</b>",
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@Tech_VJ')
            ],[
                InlineKeyboardButton("❣️ ᴅᴇᴠᴇʟᴏᴘᴇʀ", url='https://t.me/Kingvj01'),
                InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ", url='https://t.me/VJ_Botz')
            ]]
        )
    )

@Client.on_message(filters.command('help') & filters.private)
async def help_command(client, message):
    help_text = """<b>📚 Available Commands:</b>

<b>/login</b> - Login with your Telegram account
<b>/logout</b> - Logout current account
<b>/logoutall</b> - Logout all accounts

<b>/pubchannel</b> - Add channel for auto link rotation
  Usage: /pubchannel <channel_id> <base_username> <interval>
  Example: /pubchannel -1001234567890 mybase 3600

<b>/list</b> - Show all active channels
<b>/status</b> - Check current login status
<b>/showlogin</b> - Show logged in accounts

<b>/stop</b> - Stop link changing for a channel
  Usage: /stop <channel_id>

<b>/resume</b> - Resume link changing for a channel
  Usage: /resume <channel_id>

<b>Parameters:</b>
• channel_id: Your channel's ID (negative number)
• base_username: Base username without suffix (e.g., 'mybase')
• interval: Time in seconds between link changes (e.g., 3600 for 1 hour)
"""
    await message.reply(help_text)

@Client.on_message(filters.command('pubchannel') & filters.private)
async def add_pubchannel(client, message):
    try:
        parts = message.command
        if len(parts) < 4:
            await message.reply("<b>Usage: /pubchannel <channel_id> <base_username> <interval>\n\nExample: /pubchannel -1001234567890 mybase 3600</b>")
            return
        
        channel_id = int(parts[1])
        base_username = parts[2]
        interval = int(parts[3])
        
        user_id = message.from_user.id
        user_session = await db.get_session(user_id)
        
        if not user_session:
            await message.reply("<b>You must /login first before adding channels.</b>")
            return
        
        # NOTE: Channel access verification is now implicitly handled by the link_changer.
        # The rotation task will fail and log an error if the user's session lacks admin rights.
        # We will proceed with adding the channel and starting the task.
        
        # Add to database
        await db.add_channel(user_id, channel_id, base_username, interval)
        
        # Start rotation
        success, result = await link_changer.start_channel_rotation(user_id, channel_id, base_username, interval)
        
        if success:
            await message.reply(f"<b>✅ Channel added successfully!\n\nChannel ID: {channel_id}\nBase Username: {base_username}\nInterval: {interval}s\n\nLink rotation started!</b>")
        else:
            await message.reply(f"<b>❌ Error starting rotation:</b> {result}")
    except ValueError:
        await message.reply("<b>Invalid parameters. Make sure channel_id and interval are numbers.</b>")
    except Exception as e:
        await message.reply(f"<b>Error:</b> {str(e)}")

@Client.on_message(filters.command('list') & filters.private)
async def list_channels(client, message):
    user_id = message.from_user.id
    channels = await db.get_user_channels(user_id)
    
    if not channels:
        await message.reply("<b>You have no active channels. Use /pubchannel to add one.</b>")
        return
    
    text = "<b>📋 Your Active Channels:\n\n</b>"
    for i, ch in enumerate(channels, 1):
        text += f"<b>{i}. Channel ID:</b> <code>{ch['channel_id']}</code>\n"
        text += f"   <b>Base Username:</b> {ch['base_username']}\n"
        text += f"   <b>Interval:</b> {ch['interval']}s\n"
        text += f"   <b>Status:</b> {'🟢 Active' if ch['is_active'] else '🔴 Stopped'}\n\n"
    
    await message.reply(text)

@Client.on_message(filters.command('status') & filters.private)
async def status_command(client, message):
    user_id = message.from_user.id
    user_session = await db.get_session(user_id)
    
    if user_session:
        await message.reply("<b>✅ You are logged in and ready to use the bot.</b>")
    else:
        await message.reply("<b>❌ You are not logged in. Use /login to get started.</b>")

@Client.on_message(filters.command('showlogin') & filters.private)
async def show_login(client, message):
    users = await db.get_all_users()
    logged_in = []
    async for user in users:
        if user.get('session'):
            logged_in.append(f"<code>{user['id']}</code> - {user['name']}")
    
    if logged_in:
        text = f"<b>👥 Logged In Accounts ({len(logged_in)}):\n\n</b>"
        text += "\n".join(logged_in)
        await message.reply(text)
    else:
        await message.reply("<b>No accounts logged in.</b>")

@Client.on_message(filters.command('stop') & filters.private)
async def stop_channel(client, message):
    try:
        parts = message.command
        if len(parts) < 2:
            await message.reply("<b>Usage: /stop <channel_id></b>")
            return
        
        channel_id = int(parts[1])
        user_id = message.from_user.id
        
        # Stop rotation
        success, result = await link_changer.stop_channel_rotation(user_id, channel_id)
        
        if success:
            # db.stop_channel is now handled inside link_changer.stop_channel_rotation
            await message.reply(f"<b>✅ Link rotation stopped for channel {channel_id}</b>")
        else:
            await message.reply(f"<b>❌ Error:</b> {result}")
    except ValueError:
        await message.reply("<b>Invalid channel ID.</b>")
    except Exception as e:
        await message.reply(f"<b>Error:</b> {str(e)}")

@Client.on_message(filters.command('resume') & filters.private)
async def resume_channel(client, message):
    try:
        parts = message.command
        if len(parts) < 2:
            await message.reply("<b>Usage: /resume <channel_id></b>")
            return
        
        channel_id = int(parts[1])
        user_id = message.from_user.id
        
        channel = await db.get_channel(channel_id)
        if not channel:
            await message.reply("<b>Channel not found.</b>")
            return
        
        # Resume rotation
        success, result = await link_changer.resume_channel_rotation(
            user_id, 
            channel_id, 
            channel['base_username'], 
            channel['interval']
        )
        
        if success:
            await message.reply(f"<b>✅ Link rotation resumed for channel {channel_id}</b>")
        else:
            await message.reply(f"<b>❌ Error:</b> {result}")
    except ValueError:
        await message.reply("<b>Invalid channel ID.</b>")
    except Exception as e:
        await message.reply(f"<b>Error:</b> {str(e)}")

@Client.on_message(filters.command('logoutall') & filters.private)
async def logout_all(client, message):
    users = await db.get_all_users()
    count = 0
    async for user in users:
        if user.get('session'):
            await db.set_session(user['id'], None)
            count += 1
    
    await message.reply(f"<b>✅ Logged out {count} accounts.</b>")
                   
