"""
Command rules
"""
import asyncio
import os

from classes.rules_message_object import RulesMessageObject
from func.main import rules_object, operation_status
from func.messages import t
from func.telegram_client import send_service_message, edit_service_message
from func.utils import sanitize_filename
from run import PERSONAL_CHAT_ID, root_dir

async def run(  # pylint: disable=unused-argument
        command: str,
        subcommand: str,
        text_input: str,
        extra_args=None,
        is_personal_chat=False,
        callback=None):
    """
    Run the command
    :param command:
    :param subcommand:
    :param text_input:
    :param extra_args:
    :param is_personal_chat:
    :param callback:
    :return:
    """
    if subcommand == 'show':
        await show(extra_args.get('source_message'))
    elif subcommand == 'edit':
        await edit(extra_args.get('source_message'))
    elif subcommand == 'delete':
        await delete(extra_args.get('source_message'))
    elif subcommand == 'add':
        await add(extra_args.get('source_message'), text_input)
    elif subcommand == 'reload':
        await reload(extra_args.get('source_message'))
    elif subcommand == 'help':
        await rules_help(extra_args.get('source_message'))


async def show(message):
    """
    Show all rules
    :param message:
    :return:
    """
    await message.delete()
    for rule in rules_object.get_rules()['message'].values():
        rules_text = (
            f"pattern: {vars(rule.pattern)}\n"
            f"translate: {rule.translate}\n"
            f"completed_folder_mask: {rule.completed_folder_mask}"
        )
        await send_service_message(PERSONAL_CHAT_ID, rules_text, 100)


async def edit(message):
    """
    Edit a rule
    :param message:
    :return:
    """
    await message.delete()
    await send_service_message(PERSONAL_CHAT_ID, t('rules_edit', 300), 300)
    for rule in rules_object.get_rules()['message'].values():
        if os.path.exists(rule.file_name):
            with open(rule.file_name, 'r', encoding='utf-8') as file:
                contenuto = file.read()
            message = await send_service_message(PERSONAL_CHAT_ID, contenuto, 300)
            operation_status.rules_registered[message.id] = rule


async def delete(message):
    """
    Delete a rule
    :param message:
    :return:
    """
    await message.delete()
    time_to_delete = 100
    await send_service_message(PERSONAL_CHAT_ID, t('rules_delete', time_to_delete), time_to_delete)

    for rule in rules_object.get_rules()['message'].values():
        message = await send_service_message(PERSONAL_CHAT_ID, rule.file_name, time_to_delete)
        operation_status.rules_registered[message.id] = rule
    operation_status.can_delete_rules = True

    async def disable_delete_rules():
        await asyncio.sleep(time_to_delete)
        if operation_status.can_delete_rules is True:
            operation_status.can_delete_rules = False
            await send_service_message(PERSONAL_CHAT_ID, t('rules_delete_canceled'), 10)

    asyncio.create_task(disable_delete_rules())


async def add(message, text):
    """
    Add a rule
    :param message:
    :param text:
    :return:
    """
    rule_name = sanitize_filename(text).strip()
    path = os.path.join(root_dir, 'rules', f"{rule_name}.rule")
    if rule_name == '':
        await edit_service_message(message, t('rule_name_empty'))
        return
    if len(rule_name) > 100:
        await edit_service_message(message, t('rule_name_too_long', 100))
        return
    if len(rule_name) < 3:
        await edit_service_message(message, t('rule_name_too_short', 3))
        return
    if os.path.exists(path):
        await edit_service_message(message, t('rule_already_exist', path))
        return
    with open(path, 'w', encoding='utf-8') as file:
        file.write(t('rule_start_text', rule_name))
    await edit_service_message(message, t('rule_created', rule_name))
    rule_message = await send_service_message(PERSONAL_CHAT_ID, t('rule_start_text', rule_name), 300)
    operation_status.rules_registered[rule_message.id] = RulesMessageObject({
            'file_name': path
    })
    rules_object.reload_rules()


async def reload(message):
    """
    Reload rules
    :param message:
    :return:
    """
    rules_object.reload_rules()
    await edit_service_message(message, t('rules_reloaded'))


async def rules_help(message):
    """
    Show help
    :param message:
    :return:
    """
    await message.delete()
    rules_examples = {
        'use:message:filename': t('use_message_filename_example'),
        'on:message:pattern': t('on_message_pattern_example'),
        'action:message:translate': t('action_message_translate_example'),
        'on:folder:pattern': t('on_folder_pattern_example'),
        'set:chat:id': t('set_chat_id_example'),
        'set:chat:title': t('set_chat_title_example'),
        'set:chat:name': t('set_chat_name_example'),
        'action:folder:completed': t('action_folder_completed_example'),
    }
    rules_text = '\n'.join([f"`{key}`: {value}" for key, value in rules_examples.items()])

    await send_service_message(PERSONAL_CHAT_ID, t('rules_help', rules_text), 100)
