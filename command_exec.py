import asyncio
import os
import sys

from telethon import events

from func.command import CommandHandler, COMMAND_PREFIX
from func.config import load_configuration
from func.telegram_client import create_telegram_client
from func.utils import save_pickle_data

# Configurazione
CHECK_INTERVAL = 5  # intervallo in secondi per il controllo dei messaggi

# Add the 'func' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'func'))

root_dir = os.path.dirname(os.path.abspath(__file__))

configuration = load_configuration()
client = create_telegram_client(configuration.session_name, configuration.api_id, configuration.api_hash)
command_handler = CommandHandler()

async def list_commands():
    commands = command_handler.list_commands()
    text = f'Lista comandi: {", ".join(commands)}'
    await client.send_message('me', text)

async def stop_download():
    file_path = os.path.join(root_dir, '.stop')
    if not os.path.exists(file_path):
        open(file_path, 'a').close()

# TODO: completare questa funzione aggiungendo i dati dal file pickle associato.
#   passa come argomento il target.
async def rename_pickle_file(target):
    from run import VideoData
    save_pickle_data(VideoData(**{}), target)

command_handler.add_command("list", list_commands)
command_handler.add_command("stop", stop_download)
command_handler.add_command("rename", rename_pickle_file)

async def get_user_id():
    me = await client.get_me()
    print("ID Utente:", me.id)
    return me.id

async def monitor_chat():
    await client.start(configuration.phone)
    user_id = await get_user_id()

    @client.on(events.NewMessage(chats=user_id))
    async def message_handler(event):
        message = event.message
        text = message.message
        if text.startswith(COMMAND_PREFIX):
            print(f"Rilevato comando: {text}")
            if not await command_handler.detect_and_execute(text, {target: message}):
                await message.edit(f'Il comando {text} non esiste')
                print("Comando non riconosciuto.")
            else:
                await message.delete()

    print(f"In ascolto dei comandi nella chat 'me'...")
    while True:
        await asyncio.sleep(CHECK_INTERVAL)

# Avvio del programma
if __name__ == "__main__":
    asyncio.run(monitor_chat())
