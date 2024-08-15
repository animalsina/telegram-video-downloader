from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from tqdm import tqdm
import os
import shutil
import traceback
import sys

# Funzione per caricare le configurazioni dal file
def load_config(file_path):
    config = {}
    with open(file_path, 'r') as f:
        for line in f:
            key, value = line.strip().split('=', 1)
            config[key] = value
    return config

# Funzione per verificare i permessi della cartella
def check_folder_permissions(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    if not os.path.isdir(folder_path):
        raise PermissionError(f"{folder_path} is not a directory.")
    if not os.access(folder_path, os.W_OK):
        raise PermissionError(f"Permission denied: {folder_path}")

# Carica le configurazioni
config = load_config('tg-config.txt')
api_id = config.get('api_id')
api_hash = config.get('api_hash')
phone = config.get('phone')
download_folder = config.get('download_folder', 'tg-video')
completed_folder = config.get('completed_folder', 'tg-video-completed')
check_file = config.get('check_file', 'downloaded_files.txt')
lock_file = 'script.lock'

# Crea e verifica le cartelle
check_folder_permissions(download_folder)
check_folder_permissions(completed_folder)

# Carica l'elenco dei file già scaricati
def load_downloaded_files():
    if os.path.exists(check_file):
        with open(check_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()

# Salva un file nell'elenco dei file scaricati
def save_downloaded_file(file_name):
    with open(check_file, 'a') as f:
        f.write(file_name + '\n')

# Funzione per gestire il lock file
def acquire_lock():
    if os.path.exists(lock_file):
        print("Script già in esecuzione.")
        sys.exit()
    open(lock_file, 'w').close()

def release_lock():
    if os.path.exists(lock_file):
        os.remove(lock_file)

# Funzione per spostare un file gestendo i cross-device link
def move_file(src, dest):
    try:
        shutil.move(src, dest)  # Usa shutil.move che gestisce il cross-device link
        print(f"Video salvato e spostato in: {dest}")
        return True
    except Exception as e:
        print(f"Errore durante lo spostamento del file '{os.path.basename(src)}': {e}")
        return False

# Funzione per verificare se un file è corrotto o incompleto
def is_file_corrupted(file_path):
    if os.path.exists(file_path):
        if os.path.getsize(file_path) < 1000:  # Considera file più piccoli di 1KB come corrotti
            return True
    return False

# Funzione per ottenere il nome del video
def get_video_name(message, all_messages):
    if message.text:
        return message.text.split('\n')[0].strip()
    
    # Trova l'indice del messaggio corrente nella lista di tutti i messaggi
    try:
        current_index = all_messages.index(message)
    except ValueError:
        print(f"Impossibile trovare il messaggio corrente nella lista di tutti i messaggi.")
        return None

    # Ottieni il messaggio precedente se esiste
    if current_index > 0:
        prev_message = all_messages[current_index - 1]
        print(f"Debug - Previous Message ID: {prev_message.id}")
        print(f"Debug - Previous Message Text: {prev_message.text}")
        print(f"Debug - Previous Message Type: {prev_message.__class__.__name__}")

        if prev_message.text:
            video_name = prev_message.text.split('\n')[0].strip()
            return ''.join(c for c in video_name if c.isalnum() or c in (' ', '_', '-')).rstrip()
        else:
            print(f"Il messaggio precedente non contiene testo. Il video verrà ignorato.")
            return None
    else:
        print(f"Nessun messaggio precedente disponibile. Il video verrà ignorato.")
        return None

# Crea un client Telegram
client = TelegramClient('session_name', api_id, api_hash)

async def main():
    try:
        print("Inizio connessione al client...")
        await client.start(phone)
        print("Connessione avvenuta con successo.")

        # Recupera tutti i messaggi dai "Messaggi Salvati"
        all_messages = []
        print("Recupero dei messaggi...")
        async for message in client.iter_messages('me', limit=100):
            all_messages.append(message)
        
        # Filtra solo i video
        messages = [msg for msg in all_messages if msg.document and any(isinstance(attr, DocumentAttributeVideo) for attr in msg.document.attributes)]
        print(f"Trovati {len(messages)} video.")

        # Carica i file già scaricati
        downloaded_files = load_downloaded_files()

        # Crea una progress bar
        for message in tqdm(messages, desc="Downloading Videos"):
            # Ottieni il nome del video, cercando nel messaggio corrente o precedente
            video_name = get_video_name(message, all_messages)

            if not video_name:
                print(f"Impossibile ottenere il nome per il video nel messaggio {message.id}. Il video verrà ignorato.")
                continue

            file_path = os.path.join(download_folder, f"{video_name}.mp4")
            completed_file_path = os.path.join(completed_folder, f"{video_name}.mp4")

            # Verifica se il file è già stato scaricato e spostato
            if video_name in downloaded_files:
                if os.path.exists(completed_file_path):
                    print(f"Il video '{video_name}' è già stato scaricato e spostato. Salto il download.")
                    continue
                else:
                    print(f"Il video '{video_name}' è stato scaricato ma non spostato. Riprovando lo spostamento...")

            # Se il file esiste ma è corrotto, riscaricalo
            if os.path.exists(file_path) and is_file_corrupted(file_path):
                print(f"Il file '{file_path}' è corrotto. Verrà riscaricato.")
                os.remove(file_path)

            # Scarica il video e mostra il progresso (se non già scaricato o se corrotto)
            if not os.path.exists(file_path):
                print(f"Scarico il video: {file_path}")
                with tqdm(total=100, desc=f"Downloading {video_name}", unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                    async def progress_callback(current, total):
                        pbar.update(current - pbar.n)
                        if total:
                            pbar.total = total
                            pbar.n = current

                    await client.download_media(message, file_path, progress_callback=progress_callback)

            # Prova a spostare il file completato nella cartella dei file completati
            if move_file(file_path, completed_file_path):
                save_downloaded_file(video_name)

    except PermissionError as e:
        print(f"Errore di permesso: {e}")
    except Exception as e:
        print("Si è verificato un errore:")
        print(e)
        traceback.print_exc()
    finally:
        release_lock()

if __name__ == "__main__":
    acquire_lock()
    with client:
        client.loop.run_until_complete(main())

