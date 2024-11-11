"""
Module for save video info in JSON files with all useful info
"""
import os
from typing import List, Union

from telethon.errors import ChatForwardsRestrictedError
from telethon.tl.patched import Message
from telethon.tl.types import DocumentAttributeFilename, DocumentAttributeVideo, MessageMediaDocument, Channel

from classes.object_data import ObjectData
from classes.string_builder import TYPE_DELETED, TYPE_COMPLETED, TYPE_ACQUIRED, TYPE_COMPRESSED
from func.utils import (sanitize_filename, default_video_message, remove_markdown,
                        video_data_file_exists_by_video_id,
                        video_data_file_exists_by_ref_msg_id,
                        is_video_file, save_video_data, sanitize_video_name)
from run import LOG_IN_PERSONAL_CHAT, PERSONAL_CHAT_ID


async def save_video_data_action() -> None:
    """
    Action for save videos in JSON files with all useful info
    """
    videos: List[Union[MessageMediaDocument, Message, {'chat_name': str}]] = await collect_videos()

    videos.reverse()
    videos.sort(key=lambda msg: not msg.pinned)

    print("Save video info in files")
    for video in videos:
        await acquire_video(video)


async def acquire_video(message: Union[MessageMediaDocument, Message]):
    """Acquire Video"""
    document = getattr(message, 'document')
    video: Union[MessageMediaDocument, Message, {'chat_name': str}] | None = None
    if hasattr(document, 'attributes') and not video_data_file_exists_by_ref_msg_id(message.id):
        if any(isinstance(attr, DocumentAttributeVideo) for attr
               in document.attributes):
            video = message
        else:
            file_name = get_file_name_from_message(message)
            if file_name and is_video_file(file_name):
                video = message

    if video is None:
        return None

    contains_link = any(link in message.text for link in
                        [TYPE_ACQUIRED, TYPE_DELETED, TYPE_COMPLETED, TYPE_COMPRESSED])
    if message.text and contains_link is True:  # Ignore already acquired videos
        return None

    chat_name = getattr(video, 'chat_name') if hasattr(video, 'chat_name') else None
    video_data = await process_video(video, chat_name)
    if video_data and save_video_data(video_data, ObjectData(**video_data), get_video_data_keys()):
        print(f"Video saved: {video_data['original_video_name']}")
        if video_data["is_forward_chat_protected"] is not True:
            await video.delete()


async def collect_videos() -> List[Union[MessageMediaDocument, Message]]:
    """ Collect video messages from all messages. """
    from func.main import all_messages
    videos: List[Union[MessageMediaDocument, Message]] = []
    for message in all_messages:
        if isinstance(message, Message) is not True:
            continue
        document = getattr(message, 'document')
        text = getattr(message, 'text', '')
        contains_link = any(link in text for link in
                            [TYPE_ACQUIRED, TYPE_DELETED, TYPE_COMPLETED, TYPE_COMPRESSED])
        if text and contains_link is True:  # Ignore already acquired videos
            continue
        if hasattr(document, 'attributes') and not video_data_file_exists_by_ref_msg_id(message.id):
            if any(isinstance(attr, DocumentAttributeVideo) for attr
                   in document.attributes):
                videos.append(message)
            else:
                file_name = get_file_name_from_message(message)
                if file_name and is_video_file(file_name):
                    videos.append(message)
    return videos


def get_file_name_from_message(message):
    """ Extracts the file name from a message's media attributes. """
    for attr in message.media.document.attributes:
        if isinstance(attr, DocumentAttributeFilename):
            return sanitize_filename(attr.file_name)
    return None


async def process_video(video: Union[Message, MessageMediaDocument], chat_name: str):
    """
    Process a video message and return the video data dictionary.
    Will recreate the video message and save the video data to a JSON file.
    """
    from func.main import rules_object
    video_data = initialize_video_data(video, chat_name)

    video_name = await get_video_name(video)
    if video_name is None:
        return None

    video_data['original_video_name'] = video_name

    forward = video.forward
    chat_name = None
    chat_title = None
    chat_id = None

    if hasattr(forward, 'chat') and isinstance(forward.chat, Channel):
        chat_name = forward.chat.username
        chat_title = forward.chat.title
        chat_id = forward.chat_id
    elif hasattr(forward, 'sender') and hasattr(forward.sender, 'bot') and forward.sender.bot is True:
        chat_name = forward.sender.username
        chat_title = forward.sender.first_name
        chat_id = forward.sender.id

    video_name = rules_object.apply_rules(
        'translate', video_name, video_object=ObjectData(**{
            'chat_id': chat_id,
            'chat_name': chat_name,
            'chat_title': chat_title,
            'video_id': video_data["video_id"],
            'file_name': await get_file_name(video, False),
        }))
    video_data["video_name"] = video_name
    video_data["video_name_cleaned"] = sanitize_video_name(video_name)
    video_data["file_name"] = (await get_file_name(video, True)
                               or sanitize_filename(video_name) + ".mp4")

    if video.forward is not None:
        video_data['chat_name'] = chat_name
        video_data['chat_id'] = chat_id
        video_data['chat_title'] = chat_title
        if isinstance(video.forward.chat, Channel):
            video_data['forward_message_id'] = video.forward.channel_post

    if video_data["file_name"] is None:
        print("Error: file_name is None. Unable to determine the file path.")
        return None

    set_additional_video_data(video_data, video)

    if video_data_file_exists_by_video_id(str(video_data["video_id"])):
        return None

    if hasattr(video, 'noforwards') and video.noforwards is True:
        video_data["is_forward_chat_protected"] = True

    message = await send_video_to_chat(video_data, video)
    video_data["message_id_reference"] = message.id if message else video.id

    return video_data


def initialize_video_data(video: Union[Message, MessageMediaDocument], chat_name: str):
    """ Initialize a dictionary to hold video data. """
    return {
        "id": video.id,
        "video_id": video.id,
        "video_text": video.text,
        "pinned": video.pinned,
        "completed": False,
        "video_attribute": None,
        "is_forward_chat_protected": False,
    }


async def get_video_name(video):
    """ Get the video name from replies or message text. """
    from func.main import replies_msg
    video_name = None

    if len(replies_msg) > 0:
        video_name = await get_video_name_from_replies(video)

    if video_name is None:
        video_name = await get_video_name_from_text(video)

    return remove_markdown(video_name) if video_name else None


async def get_video_name_from_replies(video: Message):
    """ Extract video name from reply messages. """
    from func.main import replies_msg
    for reply_msg in replies_msg:
        if reply_msg.reply_to_msg_id == video.id:
            message_title = sanitize_filename(reply_msg.text.split("\n")[0].strip())
            if (message_title and not any(
                    icon in message_title for icon in
                    ["⬇️", "‼️", "🔔", "❌", "✅", "🗜️"]
            )):
                await reply_msg.delete()
                return message_title
    return None


async def get_video_name_from_text(video):
    """ Extract video name from the video text. """
    full_msg_rows = video.text.split("\n")
    msg1 = full_msg_rows[0].strip() if len(full_msg_rows) > 0 else ""
    msg2 = full_msg_rows[1].strip() if len(full_msg_rows) > 1 else ""
    msg3 = full_msg_rows[2].strip() if len(full_msg_rows) > 2 else ""
    return sanitize_filename(msg1 + msg2 + msg3) if video.text else None


async def get_file_name(video, with_extension: bool = False):
    """ Determine the file name based on video attributes. """
    file_name = None
    video_message_document_attributes = video.media.document.attributes

    for attr in video_message_document_attributes:
        if isinstance(attr, DocumentAttributeFilename):
            file_name = sanitize_filename(attr.file_name)

    if file_name is not None:
        if with_extension:
            return file_name
        return sanitize_filename(file_name.rsplit(".", 1)[0].strip())

    return file_name


def set_additional_video_data(video_data, video):
    """ Set additional data for the video. """
    from func.main import configuration
    video_data["file_path"] = os.path.join(configuration.download_folder, video_data["file_name"])
    video_data["video_attribute"] = get_video_attribute(video)


def get_video_attribute(video):
    """ Get the video attribute if available. """
    for attr in video.media.document.attributes:
        if isinstance(attr, DocumentAttributeVideo):
            return {"w": attr.w, "h": attr.h}
    return None


async def send_video_to_chat(video_data, video):
    """ Send the video to the specified chat and return the sent message. """
    from func.main import client
    try:
        if LOG_IN_PERSONAL_CHAT:
            return await client.send_file(
                PERSONAL_CHAT_ID,
                video.media,
                caption=default_video_message(ObjectData(**video_data)),
                parse_mode="Markdown",
            )
    except ChatForwardsRestrictedError:
        return await handle_forward_chat_protected(video_data, video)


async def handle_forward_chat_protected(video_data, video):
    """ Handle the case where forwarding is restricted. """
    from func.main import client

    if LOG_IN_PERSONAL_CHAT:
        return await client.send_message(
            PERSONAL_CHAT_ID,
            default_video_message(ObjectData(
                **{
                    "video_name": video_data['video_name_cleaned'],
                    "file_name": video_data["file_name"],
                    "video_attribute": video_data.get("video_attribute"),
                    "pinned": video.pinned,
                    "is_forward_chat_protected": video_data['is_forward_chat_protected']
                }
            )),
        )


def get_video_data_keys():
    """ Get the keys to save in video data. """
    return [
        "id",
        "video_id",
        "video_text",
        "video_name",
        "file_name",
        "file_path",
        "chat_id",
        "chat_name",
        "chat_title",
        "forward_message_id"
        "video_attribute",
        "pinned",
        "message_id_reference",
        "video_name_cleaned",
        "is_forward_chat_protected",
    ]
