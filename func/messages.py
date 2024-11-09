"""
This module contains functions for retrieving localized messages based on the language key.
"""
import locale

def get_system_language():
    """
    Determine the system's default language based on locale settings.
    If the system language starts with 'it' (indicating Italian), return 'it'.
    Otherwise, default to English ('en').
    """
    lang, _ = locale.getlocale()
    if lang.startswith('it'):
        return 'it'
    return 'en'

def get_message(language: str | None = None):
    """
    Retrieve a dictionary of localized messages based on the provided language.

    Args:
        key (str): The key for the message.
        language (str): The language code ('en' for English, 'it' for Italian).

    Returns:
        dict: A dictionary of localized messages corresponding to the language.
    """


    if language is None:
        language = get_system_language()

    lang_messages = {
        'en': {
            'start_connection': "Starting connection to the client...",
            'connection_success': "Connection successful.",
            'retrieving_messages': "Retrieving messages from: {}...",
            'found_videos': "Found {} videos.",
            'error_message': "Error message deleted.",
            'starting_download': "⬇️ Starting download: {}",
            'download_started': "⬇️ Downloading: {}%",
            'corrupted_file': "‼️ The file '{}' is corrupted. Re-downloading...",
            'download_complete': (
                "✅ Download completed and moved: {} - Completed"
            ),
            'error_move_file': "❌ Error moving file: {}",
            'not_found_file': "❌ File Not Found: {}",
            'error_download': "❌ Error downloading video '{}': {}",
            "download_video": "🔔 Downloading video in progress...",
            'permission_error': "Permission error: {}",
            'script_running': "Script already running.",
            'ready_to_move': "🔔 File ready to move: {}",
            'already_downloaded': "File already downloaded: {}",
            'file_mismatch_error': "‼️ File {} size mismatch - I will delete temp file and retry.",
            'empty_reference_specify_name':
                ("‼️ This video does not have a name. Please specify one by"
                 " replying to the video with the correct file name."),
            'rate_limit_exceeded_error': (
                "‼️ Rate limit exceeded. Waiting for {} seconds before retrying..."
            ),
            'file_system_error': "‼️ File system error: {}",
            'all_attempts_failed': "‼️ All retry attempts failed - {} - retry on next check.",
            'video_saved_and_moved': (
                "🔔 Video is saved and moved in {}"
            ),
            'no_message_found': "‼️ No message found",
            'cant_compress_file': "‼️ Can't compress the file {}",
            'start_compress_file': "🗜️ Start compression of the file {}",
            'complete_compress_file': "✅ Complete compression of the file {}",
            'trace_compress_action': "🗜️ estimated missing time to complete the compression: {}",
            'download_stopped': "Download stopped",
            'program_start': "Program is ready!",
            'download_enabled': "Download enabled",
            'download_disabled': "Download disabled",
            'program_quit': "Program quit",
            'cancel_download': "Download canceled",
        },
        'it': {
            'start_connection': "Inizio connessione al client...",
            'connection_success': "Connessione avvenuta con successo.",
            'retrieving_messages': "Recupero dei messaggi da: {}...",
            'found_videos': "Trovati {} video.",
            'error_message': "Messaggio di errore eliminato.",
            'starting_download': "️⬇️ Inizio download: {}",
            'download_started': "⬇️ Scaricando: {}%",
            'corrupted_file': "‼️ Il file '{}' è corrotto. Verrà riscaricato...",
            'download_complete': (
                "✅ Download completato e spostato: {} - Completato"
            ),
            'error_move_file': "❌ Errore durante lo spostamento del file: {}",
            'not_found_file': "❌ File non trovato: {}",
            'error_download': "❌ Errore durante il download del video '{}': {}",
            'permission_error': "Errore di permesso: {}",
            'script_running': "Script già in esecuzione.",
            'ready_to_move': "🔔 File pronto per essere spostato: {}",
            'already_downloaded': "File già scaricato: {}",
            'empty_reference_specify_name':
                "‼️ Questo video non ha un nome. Specificane uno rispondendo"
                " a questo video con il nome del file corretto.",
            'file_mismatch_error': (
                "‼️ Grandezza del file {} non corrisponde - Sarà cancellato e riscaricato."
            ),
            'rate_limit_exceeded_error': (
                "‼️ Superato il limite. Attendi {} secondi prima di riprovare..."
            ),
            'file_system_error': "‼️ Errore file system: {}",
            'all_attempts_failed': (
                "‼️ Tutti i tentativi sono falliti - {} - Riprovo al prossimo controllo."
            ),
            'video_saved_and_moved': (
                "🔔 Il video è stato salvato e spostato su {}"
            ),
            'no_message_found': "‼️ Nessun messaggio trovato",
            "download_video": "🔔 Scaricamento video in corso...",
            'cant_compress_file': "‼️ Impossibile comprimere il file {}",
            'start_compress_file': "🗜️ Inizio compressione del file {}",
            'complete_compress_file': "✅ Completamento compressione del file {}",
            'trace_compress_action': "🗜️ tempo mancante stimato per compressione: {}",
            'download_stopped': "Download fermato",
            'program_start': "Programma pronto!",
            'download_enabled': "Download abilitato",
            'download_disabled': "Download disabilitato",
            'program_quit': "Programma terminato",
            'cancel_download': "Download annullato",
        }
    }
    # Restituisce il dizionario di messaggi per la lingua richiesta, con default a inglese
    return lang_messages.get(language, lang_messages['en'])

def t(key: str, *args):
    """
    Retrieve a message based on its key and arguments.
    If the message is not found, return the key as a string.
    """
    messages = get_message()

    if key not in messages:
        return key

    message = messages[key]

    if args is None:
        return message

    if len(args) == 1:
        sanitized_value = str(args[0]).replace('{', '').replace('}', '')
        message = message.replace('{}', sanitized_value)
    else:
        for i, value in enumerate(args):
            sanitized_value = str(value).replace('{', '').replace('}', '')
            message = message.replace(f'{{{i}}}', sanitized_value)

    return message
