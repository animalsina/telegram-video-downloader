from telethon import TelegramClient
from telethon.errors import FloodWaitError
from tqdm import tqdm
import mimetypes
import time
import os
import asyncio
import csv
import collections

from func.utils import update_file_info, release_lock, is_file_corrupted, save_downloaded_file, move_file, remove_file_info

# Buffer per memorizzare i dati di velocità
speed_samples = collections.deque(maxlen=100)  # Mantieni solo gli ultimi 100 campioni

def calculate_download_speed(current, last_current, time_elapsed):
    """Calcola la velocità di download."""
    if time_elapsed <= 0:
        return 0
    return (current - last_current) / time_elapsed

def create_telegram_client(session_name, api_id, api_hash):
    return TelegramClient(session_name, api_id, api_hash)

async def update_download_message(message, percent, video_name, time_remaining_formatted):
    await message.edit(f"⬇️ Download '{video_name}': {percent:.2f}% completato.\nTempo rimanente: {time_remaining_formatted}")

def format_time(seconds):
    """Formatta il tempo in secondi in una stringa leggibile come hh:mm:ss."""
    if seconds <= 0 or seconds == float('inf'):
        return "Calculating..."

    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

def save_progress(file_path, progress):
    with open(f"{file_path}.progress", 'w') as f:
        f.write(str(progress))

def load_progress(file_path):
    try:
        with open(f"{file_path}.progress", 'r') as f:
            return int(f.read())
    except ValueError:
        # Gestisci il caso in cui il contenuto non è convertibile in int
        return 0
    except FileNotFoundError:
        return 0

async def download_with_retry(client, message, file_path, status_message, file_name, video_name, messages, lock_file, check_file, completed_folder, retry_attempts=5):
    attempt = 0
    last_update_time = time.time()
    last_current = 0
    file_size = message.media.document.size
    file_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'file_info.csv')
    temp_file_path = f"{file_path}.temp"
    progress_file_path = f"{file_path}.progress"

    # Prima di iniziare controlla se il file progress/temp esiste, se non esiste andiamo a rimuovere la riga
    if os.path.exists(temp_file_path) is False or os.path.exists(progress_file_path) is False:
        remove_file_info(file_info_path, file_name)

    # Scrivi le informazioni iniziali sul file CSV
    update_file_info(file_info_path, file_name, 'downloading', file_size)

    while attempt < retry_attempts:
        try:
            progress = load_progress(file_path) if os.path.exists(progress_file_path) else 0

            # Controlla se esiste il file temporaneo e se è vuoto, rimuovi entrambi
            if os.path.exists(temp_file_path) and os.path.getsize(temp_file_path) == 0:
                os.remove(temp_file_path)
                os.remove(progress_file_path)
                progress = 0

            # Download con progresso
            with tqdm(total=file_size, initial=progress, desc=f"Downloading {message.id} - {file_name} - {video_name}", unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                async def progress_callback(current, total):
                    nonlocal last_update_time
                    nonlocal last_current
                    file_size = message.file.size
                    progress = load_progress(file_path)

                    if total is not None:
                        percent_complete = (current / total) * 100
                        current_time = time.time()

                        # Calcola il tempo trascorso
                        time_elapsed = current_time - last_update_time

                        # Calcola la velocità di download
                        download_speed = calculate_download_speed(current, last_current, time_elapsed)

                        if download_speed > 0:
                            time_remaining = (total - current) / download_speed
                        else:
                            time_remaining = float('inf')

                        # Aggiungi la velocità al buffer di campioni
                        speed_samples.append(download_speed)

                        # Calcola la velocità media per una stima più precisa
                        if speed_samples:
                            average_speed = sum(speed_samples) / len(speed_samples)
                            time_remaining = (total - current) / average_speed if average_speed > 0 else float('inf')
                        else:
                            average_speed = 0

                        if current_time - last_update_time >= 3:
                            time_remaining_formatted = format_time(time_remaining)
                            await update_download_message(status_message, percent_complete, video_name, time_remaining_formatted)
                            last_update_time = current_time
                            last_current = current

                        pbar.update(current - pbar.n)
                        pbar.total = total
                        pbar.n = current

                        # Salva il progresso corrente
                        save_progress(file_path, current)

                # Scarica il media nel file temporaneo usando iter_download
                async with client.iter_download(message.media, offset=progress, request_size=64 * 1024) as download_iter:
                    with open(temp_file_path, 'ab') as f:
                        async for chunk in download_iter:
                            f.write(chunk)
                            await progress_callback(f.tell(), file_size)

            temp_file_size = os.path.getsize(temp_file_path)

            tolerance = 5  # Tolleranza in byte, puoi cambiarla a seconda delle tue necessità

            # Verifica se il file temporaneo è completo e poi spostalo al percorso finale
            if abs(temp_file_size - file_size) <= tolerance:
                os.rename(temp_file_path, file_path)
                os.remove(progress_file_path)
                print(f"Downloaded video to: {file_path}")
                status_message = await client.send_message('me',f"🔔 File ready to move: {file_name}")
                print(f"File ready to move: {file_name}")

                if(os.path.exists(file_path)):
                    if not is_file_corrupted(file_path, file_info_path):
                            save_downloaded_file(check_file, file_name)
                            mime_type, _ = mimetypes.guess_type(file_path)
                            extension = mimetypes.guess_extension(mime_type) if mime_type else ''
                            completed_file_path = os.path.join(completed_folder, video_name + extension)

                            if move_file(file_path, completed_file_path, messages):
                                await status_message.edit(messages['download_complete'].format(video_name))
                            else:
                                await status_message.edit(messages['error_move_file'].format(video_name))
                    else:
                        await status_message.edit(messages['corrupted_file'].format(file_name))
                    update_file_info(file_info_path, file_name, 'completed', file_size)
                return
            else:
                await status_message.edit(f"‼️ File {video_name} size mismatch - I will delete temp file and retry.")
                os.remove(temp_file_path)
                os.remove(progress_file_path)
                raise Exception(f"File {video_name} size mismatch - I will delete temp file and retry.")

        except FloodWaitError as e:
            wait_time = e.seconds + 10  # Aggiungi un buffer di tempo per sicurezza
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await status_message.edit(f"‼️ Rate limit exceeded. Waiting for {wait_time} seconds before retrying...")
            await asyncio.sleep(wait_time)
            attempt += 1

        except Exception as e:
            update_file_info(file_info_path, file_name, f'error: {str(e)}', file_size)
            await status_message.edit(f"‼️ error {str(e)}")
            break

        finally:
            release_lock(lock_file)

    else:
        print("All retry attempts failed.")
        await status_message.edit(f"‼️ All retry attempts failed - {video_name} - retry on next check.")
        release_lock(lock_file)
