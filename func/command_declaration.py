"""
Command declaration
"""
from classes.string_builder import LINE_FOR_VIDEO_NAME
from func.messages import t
from func.utils import add_line_to_text, save_video_data, get_video_object_by_message_id_reference


async def command_declaration():
    """
    Command declaration
    """

    def set_quit_program():
        from func.main import operation_status
        operation_status.quit_program = True

    def set_download_start():
        from func.main import operation_status
        operation_status.start_download = True
        operation_status.interrupt = False

    def set_download_stop():
        from func.main import operation_status
        operation_status.start_download = False
        operation_status.interrupt = True

    async def rename(message, new_name):
        from func.utils import sanitize_video_name
        from run import PERSONAL_CHAT_ID
        from func.main import client
        video_name_cleaned = sanitize_video_name(new_name)
        reply_message = await client.get_messages(
            PERSONAL_CHAT_ID,
            ids=message.reply_to.reply_to_msg_id)
        _, video_object = get_video_object_by_message_id_reference(reply_message.id)
        await add_line_to_text(
            reply_message.id,
            new_name,
            LINE_FOR_VIDEO_NAME,
            True
        )
        save_video_data({'video_name': new_name,
                         'video_name_cleaned': video_name_cleaned},
                        video_object,
                        ['video_name'])
        video_object.video_name = new_name
        await message.delete()

    from func.main import command_handler
    command_handler.add_command(["help", "command", "commands"], t('command_help'))
    command_handler.add_command(
        "quit",
        t('command_quit'),
        args={},
        callback=set_quit_program
    )
    command_handler.add_command("status", t('command_status'))
    command_handler.add_command(
        ["download:on", "download:start", "dl:start", "dl:on"],
        t('command_download_start'),
        args={},
        callback=set_download_start
    )
    command_handler.add_command(
        ["download:off", "download:stop", "dl:off", "dl:stop"],
        t('command_download_stop'),
        args={},
        callback=set_download_stop
    )
    command_handler.add_command("rules:show", t('command_rules_show'))
    command_handler.add_command("rules:edit", t('command_rules_edit'))
    command_handler.add_command("rules:delete", t('command_rules_delete'))
    command_handler.add_command("rules:add", t('command_rules_add'))
    command_handler.add_command("rules:reload", t('command_rules_reload'))
    command_handler.add_command(
        ["download:rename", "download:rn", "dl:rn", "dl:rename"],
        t('command_rename'),
        args={
            'needs_reply': True
        },
        callback=rename,
    )
    command_handler.add_command(
        ["download:target", "download:destination", "dl:target", "dl:destination", "dl:dir"],
        t('command_stop'),
        args={
            'needs_reply': True
        },
    )
