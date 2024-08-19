def get_message(key, language):
    messages = {
        'en': {
            'start_connection': "Starting connection to the client...",
            'connection_success': "Connection successful.",
            'retrieving_messages': "Retrieving messages...",
            'found_videos': "Found {} videos.",
            'error_message': "Error message deleted.",
            'starting_download': "Starting download: {}",
            'download_started': "⬇️ Downloading: {}%",
            'corrupted_file': "The file '{}' is corrupted. Re-downloading...",
            'download_complete': "✅ Download completed and moved: {}\nCompleted",
            'error_move_file': "❌ Error moving file: {}",
            'not_found_file': "❌ File Not Found: {}",
            'error_download': "❌ Error downloading video '{}': {}",
            'permission_error': "Permission error: {}",
            'script_running': "Script already running."
        },
        'it': {
            'start_connection': "Inizio connessione al client...",
            'connection_success': "Connessione avvenuta con successo.",
            'retrieving_messages': "Recupero dei messaggi...",
            'found_videos': "Trovati {} video.",
            'error_message': "Messaggio di errore eliminato.",
            'starting_download': "Inizio download: {}",
            'download_started': "⬇️ Scaricando: {}%",
            'corrupted_file': "Il file '{}' è corrotto. Riscaricando...",
            'download_complete': "✅ Download completato e spostato: {}\nCompletato",
            'error_move_file': "❌ Errore durante lo spostamento del file: {}",
            'not_found_file': "❌ File non trovato: {}",
            'error_download': "❌ Errore durante il download del video '{}': {}",
            'permission_error': "Errore di permesso: {}",
            'script_running': "Script già in esecuzione."
        }
    }
    return messages.get(language, messages['en'])  # Default to English if the language is not supported
