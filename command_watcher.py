"""
Command watcher module for run the program
"""
import asyncio
import os
import sys

from telethon import events

from classes.command_handler import CommandHandler, COMMAND_PREFIX
from func.config import load_configuration
from func.telegram_client import create_telegram_client
from func.utils import save_video_data

# Configurazione
CHECK_INTERVAL = 5  # intervallo in secondi per il controllo dei messaggi

# Add the 'func' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

root_dir = os.path.dirname(os.path.abspath(__file__))

configuration = load_configuration()
client = create_telegram_client(configuration.session_name, configuration.api_id, configuration.api_hash)
command_handler = CommandHandler()

PERSONAL_CHAT_ID = 'me'
LOG_IN_PERSONAL_CHAT = False

async def list_commands():
    """
    List commands
    """
    commands = command_handler.list_commands()
    text = f'Lista comandi: {", ".join(commands)}'
    if LOG_IN_PERSONAL_CHAT is True:
        await client.send_message(PERSONAL_CHAT_ID, text)

async def stop_download():
    """
    Stop download
    """
    file_path = os.path.join(root_dir, '.stop')
    if not os.path.exists(file_path):
        with open(file_path, 'a', encoding='utf-8'):
            pass

# TODO: completare questa funzione aggiungendo i dati dal file video data associato.
#   passa come argomento il target.
async def rename_video_data_file(target):
    """
    Rename video data file
    """
    save_video_data({}, target)

command_handler.add_command("list", list_commands)
command_handler.add_command("stop", stop_download)
command_handler.add_command("rename", rename_video_data_file)

async def get_user_id():
    """
    Get user id
    """
    me = await client.get_me()
    print("ID Utente:", me.id)
    return me.id

async def monitor_chat():
    """
    Monitor chat
    """
    await client.start(configuration.phone)
    user_id = await get_user_id()

    #@client.on(events.NewMessage(chats=user_id)) # noqa: F811
    async def message_handler(event):
        message = event.message
        text = message.message
        if text.startswith(COMMAND_PREFIX):
            print(f"Rilevato comando: {text}")
            if not await command_handler.detect_and_execute(text, {'target': message}):
                if LOG_IN_PERSONAL_CHAT is True:
                    await message.edit(f'Il comando {text} non esiste')
                print("Comando non riconosciuto.")
            else:
                if LOG_IN_PERSONAL_CHAT is True:
                    await message.delete()

    client.add_event_handler(message_handler, events.NewMessage(chats=user_id))

    print(f"In ascolto dei comandi nella chat '{PERSONAL_CHAT_ID}'...")
    while True:
        await asyncio.sleep(CHECK_INTERVAL)

# Avvio del programma
if __name__ == "__main__":
    asyncio.run(monitor_chat())
