#!/usr/bin/env python3
"""
Telegram Album Forwarder - Handles grouped photos properly
Forwards grouped photos as album with caption
"""

import asyncio
import re
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

# ==================== CONFIGURATION ====================
SESSION_STRING = "1BVtsOMcBu6bihZu3OaaV3vOT4m9rVou4N3tBCXQln9Q8Y8dFyEDx39jdORRKB_RbNcZnwEJOsUbkmbdeVS714MA1Wq4N4cahQe5VB0fMJ2OguvJlL_CR0tPxSQHiTE35eH5UZ_lnO9axALK97tda_4OMQEoumpMjsn4m7rAVRJe6I8Rzh_QY8Q15nLPDQWdoX65Z1btEaWVmiL4kfPnxfBHBpdE9H3qFEaj9nWZ8IZslrqfcK0o0NCrf1-9CbQE_HxNg8C-2nK-2sQrPuNRLxt74gAFWGXf1wPEOJPvEW3ud6jmiuMyqwJwPQ-ZAN6jOlIcKfvsKluxCIZ1rzJ2y5YShos_TJ4I="
API_ID = 33414516
API_HASH = "039a444a191332110ea64aa42f17cfaa"

# Group IDs
SOURCE_CHAT_ID = -1002380114448  # Source group to monitor
TARGET_CHAT_ID = -1003867541352  # Target group to forward to

# Username replacement configuration
OLD_USERNAME = "cashxcore"  # Case insensitive
NEW_USERNAME = "@InfoXCashReal"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

class AlbumForwarder:
    def __init__(self):
        self.client = None
        self.processed_ids = set()
        
    async def start(self):
        """Start the bot"""
        print("=" * 60)
        print("🤖 TELEGRAM ALBUM FORWARDER")
        print("=" * 60)
        print(f"Source: {SOURCE_CHAT_ID}")
        print(f"Target: {TARGET_CHAT_ID}")
        print(f"Replace: @{OLD_USERNAME} → {NEW_USERNAME}")
        print("Special: Handles grouped photos as albums")
        print("=" * 60)
        
        try:
            # Create client
            self.client = TelegramClient(
                StringSession(SESSION_STRING),
                API_ID,
                API_HASH
            )
            
            # Connect
            await self.client.connect()
            
            # Check authorization
            if not await self.client.is_user_authorized():
                print("❌ Session invalid!")
                return
            
            me = await self.client.get_me()
            print(f"✅ Connected as: {me.first_name}")
            
            # TEST: Forward ONLY LAST 1 MESSAGE
            print("\n🔧 TESTING: Forwarding last message...")
            await self.forward_last_message()
            
            print("\n✅ Test complete! Now waiting for NEW messages...")
            print("=" * 60)
            
            # Setup handler for NEW messages only
            self.setup_handler()
            
            # Keep running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def forward_last_message(self):
        """Forward ONLY the last 1 message for testing"""
        try:
            # Get the VERY LAST message
            last_message = None
            async for message in self.client.iter_messages(
                SOURCE_CHAT_ID, 
                limit=5  # Get 5, filter for non-self
            ):
                if not message.out:  # Skip own messages
                    last_message = message
                    break
            
            if not last_message:
                print("⚠️ No recent message found to forward")
                return
            
            print(f"📥 Found last message (ID: {last_message.id})")
            
            # Check if it's part of a grouped album
            if last_message.grouped_id:
                print(f"📸 This is part of a photo album (Group ID: {last_message.grouped_id})")
                await self.process_grouped_album(last_message)
            else:
                # Single message
                await self.process_single_message(last_message)
            
            print("✅ Test forward successful!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    def setup_handler(self):
        """Setup handler for NEW messages only"""
        
        @self.client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
        async def handler(event):
            message = event.message
            
            # Skip if it's my own message
            if message.out:
                return
            
            # Skip if already processed
            if message.id in self.processed_ids:
                return
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] 🎯 NEW MESSAGE DETECTED (ID: {message.id})")
            
            # Check if grouped photo
            if message.grouped_id:
                print(f"[{timestamp}] 📸 Grouped photo detected (Group ID: {message.grouped_id})")
                await self.process_grouped_album(message)
            else:
                # Single message
                await self.process_single_message(message)
            
            # Mark as processed
            self.processed_ids.add(message.id)
    
    async def process_grouped_album(self, first_message):
        """Process grouped photos (album)"""
        try:
            group_id = first_message.grouped_id
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"[{timestamp}] 🔍 Looking for other photos in this album...")
            
            # Collect all photos in this album
            album_photos = []
            
            # First, add the current message
            if first_message.media and isinstance(first_message.media, MessageMediaPhoto):
                album_photos.append(first_message)
                self.processed_ids.add(first_message.id)
            
            # Look for other photos in the same group (recent messages)
            async for message in self.client.iter_messages(
                SOURCE_CHAT_ID,
                limit=10  # Check last 10 messages
            ):
                if (message.id != first_message.id and 
                    message.grouped_id == group_id and
                    message.media and isinstance(message.media, MessageMediaPhoto) and
                    message.id not in self.processed_ids):
                    
                    album_photos.append(message)
                    self.processed_ids.add(message.id)
            
            # Sort by message ID (chronological order)
            album_photos.sort(key=lambda x: x.id)
            
            print(f"[{timestamp}] 📊 Found {len(album_photos)} photos in album")
            
            if len(album_photos) == 0:
                print(f"[{timestamp}] ⚠️ No photos found in album")
                return
            
            # Get caption from first photo (usually contains caption for whole album)
            caption_text = ""
            for photo_msg in album_photos:
                if photo_msg.text or photo_msg.message:
                    caption_text = photo_msg.text or photo_msg.message
                    break
            
            # Replace username in caption
            new_caption = self.replace_username(caption_text)
            
            if caption_text:
                print(f"[{timestamp}] 📝 Album caption: {caption_text[:100]}")
                if new_caption != caption_text:
                    print(f"[{timestamp}] 🔄 Modified: {new_caption[:100]}")
            
            # Download all photos
            photo_files = []
            for i, photo_msg in enumerate(album_photos, 1):
                try:
                    print(f"[{timestamp}] ⬇️ Downloading photo {i}/{len(album_photos)}...")
                    file_path = await self.client.download_media(photo_msg.media)
                    
                    if file_path:
                        photo_files.append(file_path)
                        print(f"[{timestamp}] ✅ Photo {i} downloaded")
                    else:
                        print(f"[{timestamp}] ⚠️ Failed to download photo {i}")
                        
                except Exception as e:
                    print(f"[{timestamp}] ❌ Error photo {i}: {str(e)[:50]}")
            
            # Send as album
            if photo_files:
                try:
                    print(f"[{timestamp}] 📤 Sending {len(photo_files)} photos as album...")
                    
                    # Send all photos together as album
                    await self.client.send_file(
                        TARGET_CHAT_ID,
                        photo_files,
                        caption=new_caption if new_caption else None
                    )
                    
                    print(f"[{timestamp}] ✅ Album sent successfully ({len(photo_files)} photos)")
                    
                    # Clean up downloaded files
                    await self.cleanup_files(photo_files)
                    
                except Exception as e:
                    print(f"[{timestamp}] ❌ Album error: {str(e)[:50]}")
                    # Try sending individually
                    await self.send_photos_individually(photo_files, new_caption)
            else:
                print(f"[{timestamp}] ⚠️ No photos downloaded, sending caption only")
                if new_caption:
                    await self.client.send_message(TARGET_CHAT_ID, new_caption)
            
            print("-" * 50)
            
        except Exception as e:
            print(f"❌ Album processing error: {e}")
    
    async def send_photos_individually(self, photo_files, caption_text):
        """Send photos one by one if album fails"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Trying individual photo sends...")
            
            for i, file_path in enumerate(photo_files, 1):
                try:
                    # First photo gets caption, others don't
                    current_caption = caption_text if i == 1 else None
                    
                    await self.client.send_file(
                        TARGET_CHAT_ID,
                        file_path,
                        caption=current_caption
                    )
                    print(f"[{timestamp}] ✅ Photo {i} sent")
                    
                    # Clean up
                    import os
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # Small delay between sends
                    if i < len(photo_files):
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    print(f"[{timestamp}] ❌ Error sending photo {i}: {str(e)[:50]}")
                    
        except Exception as e:
            print(f"❌ Individual send error: {e}")
    
    async def process_single_message(self, message):
        """Process single message (not grouped)"""
        try:
            # Get text/caption
            text = message.text or message.message or ""
            new_text = self.replace_username(text)
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check media
            if message.media and isinstance(message.media, MessageMediaPhoto):
                print(f"[{timestamp}] 📸 Single photo")
                
                if text:
                    print(f"    Text: {text[:100]}")
                
                try:
                    # Download and send
                    file_path = await self.client.download_media(message.media)
                    
                    if file_path:
                        await self.client.send_file(
                            TARGET_CHAT_ID,
                            file_path,
                            caption=new_text if new_text else None
                        )
                        print(f"[{timestamp}] ✅ Photo sent")
                        
                        # Cleanup
                        import os
                        os.remove(file_path)
                    else:
                        if new_text:
                            await self.client.send_message(TARGET_CHAT_ID, new_text)
                            print(f"[{timestamp}] ✅ Text sent (photo failed)")
                            
                except Exception as e:
                    print(f"[{timestamp}] ⚠️ Photo error: {e}")
                    if new_text:
                        await self.client.send_message(TARGET_CHAT_ID, new_text)
                        
            elif message.media:
                # Other media types (video, document, etc.)
                print(f"[{timestamp}] 📦 Other media")
                
                if text:
                    print(f"    Text: {text[:100]}")
                
                try:
                    file_path = await self.client.download_media(message.media)
                    
                    if file_path:
                        await self.client.send_file(
                            TARGET_CHAT_ID,
                            file_path,
                            caption=new_text if new_text else None
                        )
                        print(f"[{timestamp}] ✅ Media sent")
                        
                        import os
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            
                except Exception as e:
                    print(f"[{timestamp}] ⚠️ Media error: {e}")
                    if new_text:
                        await self.client.send_message(TARGET_CHAT_ID, new_text)
                        
            else:
                # Text message
                if text:
                    print(f"[{timestamp}] 💬 Text message")
                    print(f"    Text: {text[:100]}")
                    
                    await self.client.send_message(
                        TARGET_CHAT_ID,
                        new_text
                    )
                    print(f"[{timestamp}] ✅ Text sent")
                else:
                    print(f"[{timestamp}] ⏭️ Skipping empty message")
            
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ Processing error: {e}")
    
    def replace_username(self, text):
        """Replace @cashxcore with @InfoXCashReal"""
        if not text:
            return text
        
        # Case insensitive replacement
        pattern = r'@' + re.escape(OLD_USERNAME)
        new_text = re.sub(pattern, NEW_USERNAME, text, flags=re.IGNORECASE)
        
        if text != new_text:
            print(f"🔄 Replaced: @{OLD_USERNAME} → {NEW_USERNAME}")
        
        return new_text
    
    async def cleanup_files(self, file_paths):
        """Clean up downloaded files"""
        import os
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    async def stop(self):
        """Stop the bot"""
        if self.client:
            await self.client.disconnect()
        print("\n🛑 Bot stopped")

async def main():
    bot = AlbumForwarder()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped by user")
        await bot.stop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        await bot.stop()

if __name__ == "__main__":
    # Run
    asyncio.run(main())