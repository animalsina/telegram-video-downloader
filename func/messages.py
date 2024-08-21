"""
This module contains functions for retrieving localized messages based on the language key.
"""

def get_message(key, language):
    """
    Retrieve a dictionary of localized messages based on the provided language.

    Args:
        key (str): The key for the message.
        language (str): The language code ('en' for English, 'it' for Italian).

    Returns:
        dict: A dictionary of localized messages corresponding to the language.
    """
    messages = {
        'en': {
            'start_connection': "Starting connection to the client...",
            'connection_success': "Connection successful.",
            'retrieving_messages': "Retrieving messages...",
            'found_videos': "Found {} videos.",
            'error_message': "Error message deleted.",
            'starting_download': "⬇️ Starting download: {}",
            'download_started': "⬇️ Downloading: {}%",
            'corrupted_file': "The file '{}' is corrupted. Re-downloading...",
            'download_complete': (
                "✅ Download completed and moved: {}\nCompleted"
            ),
            'error_move_file': "❌ Error moving file: {}",
            'not_found_file': "❌ File Not Found: {}",
            'error_download': "❌ Error downloading video '{}': {}",
            'permission_error': "Permission error: {}",
            'script_running': "Script already running.",
            'ready_to_move': "🔔 File ready to move: {}",
            'file_mismatch_error': "‼️ File {} size mismatch - I will delete temp file and retry.",
            'rate_limit_exceeded_error': "‼️ Rate limit exceeded. Waiting for {} seconds before retrying...",
            'file_system_error': "‼️ File system error: {}",
            'all_attempts_failed': "‼️ All retry attempts failed - {} - retry on next check."
        },
        'it': {
            'start_connection': "Inizio connessione al client...",
            'connection_success': "Connessione avvenuta con successo.",
            'retrieving_messages': "Recupero dei messaggi...",
            'found_videos': "Trovati {} video.",
            'error_message': "Messaggio di errore eliminato.",
            'starting_download': "️⬇️ Inizio download: {}",
            'download_started': "⬇️ Scaricando: {}%",
            'corrupted_file': "Il file '{}' è corrotto. Riscaricando...",
            'download_complete': (
                "✅ Download completato e spostato: {}\nCompletato"
            ),
            'error_move_file': "❌ Errore durante lo spostamento del file: {}",
            'not_found_file': "❌ File non trovato: {}",
            'error_download': "❌ Errore durante il download del video '{}': {}",
            'permission_error': "Errore di permesso: {}",
            'script_running': "Script già in esecuzione.",
            'ready_to_move': "🔔 File pronto per essere spostato: {}",
            'file_mismatch_error': "‼️ Grandezza del file {} non corrisponde - Sarà cancellato e riscaricato.",
            'rate_limit_exceeded_error': "‼️ Superato il limite. Attendi {} secondi prima di riprovare...",
            'file_system_error': "‼️ Errore file system: {}",
            'all_attempts_failed': "‼️ Tutti i tentativi sono falliti - {} - Riprovo al prossimo controllo."
        }
    }
    # Restituisce il dizionario di messaggi per la lingua richiesta, con default a inglese
    return messages.get(language, messages['en'])
