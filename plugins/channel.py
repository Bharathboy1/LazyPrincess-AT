import pymongo
from pyrogram import Client, filters
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, ADMINS, CHANNELS, CUSTOM_FILE_CAPTION
from database.ia_filterdb import save_file
import asyncio
import random
from utils import get_size
from pyrogram.errors import FloodWait


media_filter = filters.document | filters.video | filters.audio

myclient = pymongo.MongoClient(DATABASE_URI)
db = myclient[DATABASE_NAME]
col = db[COLLECTION_NAME]

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    await save_file(media)

@Client.on_message(filters.command("savefile") & filters.user(ADMINS))
async def start(client, message):
    try:
        for file_type in ("document", "video", "audio"):
            media = getattr(message.reply_to_message, file_type, None)
            if media is not None:
                break
        else:
            return

        media.file_type = file_type
        media.caption = message.reply_to_message.caption
        await save_file(media)
        await message.reply_text("Saved In DB")
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")


@Client.on_message(filters.command("sendall") & filters.user(ADMINS))
async def x(app, msg):
    args = msg.text.split(maxsplit=1)
    if len(args) == 1:
        return await msg.reply_text("Give Chat ID Also Where To Send Files")
    args = args[1]
    try:
        args = int(args)
    except Exception:
        return await msg.reply_text("Chat Id must be an integer not a string")

    jj = await msg.reply_text("Processing...")
    documents = col.find({})
    last_msg = col.find_one({'_id': 'last_msg'})
    if not last_msg:
        col.update_one({'_id': 'last_msg'}, {'$set': {'index': 0}}, upsert=True)
        last_msg = 0
    else:
        last_msg = last_msg.get('index', 0)
    id_list = [{'id': document['_id'], 'file_name': document.get('file_name', 'N/A'), 'file_caption': document.get('caption', 'N/A'), 'file_size': document.get('file_size', '0')} for document in documents]
    await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}")

    # Batch processing variables
    batch_size = 100
    num_batches = (len(id_list) + batch_size - 1) // batch_size

    # Process files in batches starting from the last message index
    for batch in range(last_msg // batch_size, num_batches):
        start_index = batch * batch_size
        end_index = min((batch + 1) * batch_size, len(id_list))
        batch_files = id_list[start_index:end_index]

        batch_num = batch + 1
        current_batch_files = len(batch_files)
        total_files = len(id_list)
        await jj.edit(f"Found {total_files} Files In The DB Starting To Send In Chat {args}\nProcessing Batch {batch_num}/{num_batches}\nCurrent Batch Files: {current_batch_files}")

        start_index_within_batch = last_msg - start_index
        for j, i in enumerate(batch_files[start_index_within_batch:], start=start_index_within_batch):
            try:
                try:
                    await app.send_video(
                        msg.chat.id,
                        i['id'],
                        caption=CUSTOM_FILE_CAPTION.format(
                            file_name=i['file_name'],
                            file_caption=i['file_caption'],
                            file_size=get_size(int(i['file_size']))
                        )
                    )
                except Exception as e:
                    print(e)
                    await app.send_document(
                        msg.chat.id,
                        i['id'],
                        caption=CUSTOM_FILE_CAPTION.format(
                            file_name=i['file_name'],
                            file_caption=i['file_caption'],
                            file_size=get_size(int(i['file_size']))
                        )
                    )
                await jj.edit(f"Found {total_files} Files In The DB Starting To Send In Chat {args}\nProcessing Batch {batch_num}/{num_batches}\nCurrent Batch Files: {current_batch_files}\nProcessed Files: {j+1}/{current_batch_files}")
                col.update_one({'_id': 'last_msg'}, {'$set': {'index':start_index + j+1}}, upsert=True)
                await asyncio.sleep(random.randint(4, 5))
            except FloodWait as e:
                print(f"Sleeping for {e.value} seconds.")
                await asyncio.sleep(e.value)
            except Exception as e:
                print(e)

    await jj.delete()
    await msg.reply_text("Completed")


'''@Client.on_message(filters.command("sendall") & filters.user(ADMINS))
async def x(app, msg):
    args = msg.text.split(maxsplit=1)
    if len(args) == 1:
        return await msg.reply_text("Give Chat ID Also Where To Send Files")
    args = args[1]
    try:
        args = int(args)
    except Exception:
        return await msg.reply_text("Chat Id must be an integer not a string")
    jj = await msg.reply_text("Processing...")
    documents = col.find({})
    last_msg = col.find_one({'_id': 'last_msg'})
    if not last_msg:
        col.update_one({'_id': 'last_msg'}, {'$set': {'index': 0}}, upsert=True)
        last_msg = 0
    else:
        last_msg = last_msg.get('index', 0)
    id_list = [{'id': document['_id'], 'file_name': document.get('file_name', 'N/A'), 'file_caption': document.get('caption', 'N/A'), 'file_size': document.get('file_size', 'N/A')} for document in documents]
    await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}")
    for j, i in enumerate(id_list[last_msg:], start=last_msg):
        try:
            try:
                await app.send_video(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=get_size(int(i['file_size']))))
            except Exception as e:
                print(e)
                await app.send_document(msg.chat.id, i['id'], caption=CUSTOM_FILE_CAPTION.format(file_name=i['file_name'], file_caption=i['file_caption'], file_size=get_size(int(i['file_size']))))
            await jj.edit(f"Found {len(id_list)} Files In The DB Starting To Send In Chat {args}\nProcessed: {j+1}")
            col.update_one({'_id': 'last_msg'}, {'$set': {'index': j}}, upsert=True)
            await asyncio.sleep(random.randint(1, 3))
        except FloodWait as e:
            print(f"Sleeping for {e.x} seconds.")
            await asyncio.sleep(e.x)
        except Exception as e:
            print(e)
    await jj.delete()
    await msg.reply_text("Completed")'''

@Client.on_message(filters.command("sendkey") & filters.user(ADMINS))
async def send_messages_with_keyword(app, msg):
    try:
        keywords = msg.command[1].split("-")
    except IndexError:
        await msg.reply_text("Please provide keyword(s) to search for in the file names.")
        return
    regex_pattern = "|".join(keywords)
    documents = col.find({"file_name": {"$regex": '|'.join(keywords)}})
    
    id_list = [
        {
            'id': document['_id'],
            'file_name': document.get('file_name', 'N/A'),
            'file_caption': document.get('caption', 'N/A'),
            'file_size': document.get('file_size', '0')
        } 
        for document in documents
    ]
    
    for j, i in enumerate(id_list):
        try:
            try:
                await app.send_video(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            except Exception as e:
                print(e)
                await app.send_document(
                    msg.chat.id,
                    i['id'],
                    caption=CUSTOM_FILE_CAPTION.format(
                        file_name=i['file_name'],
                        file_caption=i['file_caption'],
                        file_size=get_size(int(i['file_size']))
                    )
                )
            
            await asyncio.sleep(random.randint(3,6))
        except FloodWait as e:
            print(f"Sleeping for {e.value} seconds.")
            await asyncio.sleep(e.value)
        except Exception as e:
            print(e)
            #await jj.delete()
            await msg.reply_text("An error occurred while sending messages.")
            break
    
    await msg.reply_text("Completed")




