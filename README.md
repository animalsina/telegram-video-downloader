# Telegram Video Downloader v2.7.1

## Table of Contents / Indice
- [ENG](#--eng)
  - [Description](#description)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
  - [Notes](#notes)
  - [Useful Readme](#useful-readme)
  - [License](#license)
- [ITA](#--ita)
  - [Descrizione](#descrizione)
  - [Funzionalità](#funzionalità)
  - [Requisiti](#requisiti)
  - [Installazione](#installazione)
  - [Configurazione](#configurazione)
  - [Uso](#uso)
  - [Note](#note)
  - [Readme utili](#readme-utili)
  - [Licenza](#licenza)

---

# == ENG

## Description
Telegram Video Downloader is a Python script that automates the download and management of video files from your Telegram "Saved Messages" or custom groups/channels, using the [Telethon](https://github.com/LonamiWebs/Telethon) library. It is designed for reliability, flexibility, and ease of use, supporting features like simultaneous downloads, resuming interrupted downloads, file validation, and optional video compression.

## Features
- **Download videos** from "Saved Messages" or specified groups/channels.
- **Automatic relocation** of completed downloads to a separate folder.
- **Configurable minimum file size**: re-download corrupted/incomplete files.
- **Simultaneous downloads**: control max concurrent downloads.
- **Resume support**: continue partial downloads on restart.
- **Optional video compression** (beta): save disk space.
- **Disk space monitoring**: halt downloads if disk is nearly full.
- **Progress updates**: real-time download percentage.
- **Flexible configuration**: via `tg-config.txt`, supports multiple profiles.
- **Command-line commands and rules**: see [Commands](/README-commands.md) and [Rules](/README-rules.md).

## Requirements
- Python 3.9 or higher
- [Telethon](https://github.com/LonamiWebs/Telethon) (see `requirements.txt` for full dependencies)

## Installation

1. **Clone this repository:**
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. **(Recommended) Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. **Get your Telegram API credentials:**  
   Register your app at [my.telegram.org/apps](https://my.telegram.org/apps) to obtain `api_id` and `api_hash`.

2. **Create a configuration file `tg-config.txt`** in the project root with the following format:

    ```ini
    [telegram]
    api_id=YOUR_API_ID
    api_hash=YOUR_API_HASH
    phone=YOUR_PHONE_NUMBER
    download_folder=YOUR_DOWNLOAD_FOLDER
    completed_folder=YOUR_COMPLETED_FOLDER
    min_valid_file_size_mb=10
    session_name=YOUR_SESSION_NAME
    max_simultaneous_file_to_download=2
    max_download_size_request_limit_kb=8388608
    enable_video_compression=0
    compression_ratio=10
    disk_space_limit_percentage=90

    [groups]
    # Key = ChannelID or nickname
    personal=me
    ```

   **Sample configuration:**
    ```ini
    [telegram]
    api_id=120398
    api_hash=123098104981209481
    phone=123123123
    download_folder=tg-video
    completed_folder=tg-video-completed
    min_valid_file_size_mb=10
    session_name=session_name
    max_simultaneous_file_to_download=1
    max_download_size_request_limit_kb=8388608
    enable_video_compression=0
    compression_ratio=28
    disk_space_limit_percentage=90

    [groups]
    personal=me
    movies_group=-1001234567890
    ```

   **Parameter meanings:**
   - `api_id`, `api_hash`, `phone`: Your Telegram app credentials and phone for login.
   - `download_folder`: Where videos are saved initially.
   - `completed_folder`: Where videos are moved after successful download.
   - `min_valid_file_size_mb`: Minimum file size (MB) to consider a file valid.
   - `session_name`: Name for Telethon session file.
   - `max_simultaneous_file_to_download`: Max downloads at once (integer).
   - `max_download_size_request_limit_kb`: Max size per download request (KB).
   - `enable_video_compression`: 0 = off, 1 = on (beta).
   - `compression_ratio`: Compression ratio for video (1-100).
   - `disk_space_limit_percentage`: Max disk usage (%) for downloads.
   - `[groups]`: Map a key to a Telegram channel/group ID or "me" for "Saved Messages".

## Usage

1. Ensure you've created and configured `tg-config.txt` as described above.
2. Run the script (default config file):
    ```bash
    python run.py
    ```
3. To use a custom configuration file:
    ```bash
    python run.py tg-config-2.txt
    ```

## Notes

- Videos are saved in the specified download folder, then moved to the completed folder after successful download.
- If a message has no text, the script attempts to use the next message for a filename.
- Supports configurable minimum file size: files below threshold are considered corrupted and re-downloaded.
- Supports resuming interrupted downloads.
- To use a different config file, supply it as an argument (`python run.py custom-config.txt`).
- Progress bar shows download percentage.
- Full command list and rules: [Commands](/README-commands.md), [Rules](/README-rules.md).
- **Security:** Your Telegram credentials are required but not shared or uploaded anywhere.

## Useful Readme
- [Commands](/README-commands.md)
- [Rules](/README-rules.md)

## License
Distributed under the [MIT License](https://opensource.org/licenses/MIT).

---

# == ITA

## Descrizione
Telegram Video Downloader è uno script Python che automatizza il download e la gestione di file video dai "Messaggi Salvati" di Telegram o da gruppi/canali personalizzati, utilizzando la libreria [Telethon](https://github.com/LonamiWebs/Telethon). Progettato per essere affidabile, flessibile e facile da usare, supporta download simultanei, resume, validazione file e compressione video opzionale.

## Funzionalità
- **Scarica video** da "Messaggi Salvati" o gruppi/canali specificati.
- **Spostamento automatico** dei video scaricati in una cartella separata.
- **Validazione configurabile** della dimensione minima del file: i file ritenuti corrotti vengono riscaricati.
- **Download simultanei**: puoi impostare il numero massimo di download paralleli.
- **Supporto resume**: riprende download interrotti.
- **Compressione video opzionale** (beta): risparmia spazio su disco.
- **Controllo spazio disco**: i download vengono bloccati se il disco è quasi pieno.
- **Barra di progresso**: mostra la percentuale di download.
- **Configurazione flessibile**: tramite `tg-config.txt`, supporta più profili.
- **Comandi e regole da riga di comando**: vedi [Comandi](/README-commands.md) e [Regole](/README-rules.md).

## Requisiti
- Python 3.9 o superiore
- [Telethon](https://github.com/LonamiWebs/Telethon) (vedi `requirements.txt` per le dipendenze)

## Installazione

1. **Clona il repository:**
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. **(Consigliato) Crea e attiva un ambiente virtuale:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Su Windows: venv\Scripts\activate
    ```

3. **Installa le dipendenze:**
    ```bash
    pip install -r requirements.txt
    ```

## Configurazione

1. **Recupera le credenziali API di Telegram:**  
   Registra la tua app su [my.telegram.org/apps](https://my.telegram.org/apps) per ottenere `api_id` e `api_hash`.

2. **Crea un file di configurazione `tg-config.txt`** nella cartella principale con questo formato:

    ```ini
    [telegram]
    api_id=YOUR_API_ID
    api_hash=YOUR_API_HASH
    phone=YOUR_PHONE_NUMBER
    download_folder=YOUR_DOWNLOAD_FOLDER
    completed_folder=YOUR_COMPLETED_FOLDER
    min_valid_file_size_mb=10
    session_name=YOUR_SESSION_NAME
    max_simultaneous_file_to_download=2
    max_download_size_request_limit_kb=8388608
    enable_video_compression=0
    compression_ratio=10
    disk_space_limit_percentage=90

    [groups]
    # Key = ChannelID o nickname
    personal=me
    ```

   **Esempio di configurazione:**
    ```ini
    [telegram]
    api_id=120398
    api_hash=123098104981209481
    phone=123123123
    download_folder=tg-video
    completed_folder=tg-video-completed
    min_valid_file_size_mb=10
    session_name=session_name
    max_simultaneous_file_to_download=1
    max_download_size_request_limit_kb=8388608
    enable_video_compression=0
    compression_ratio=28
    disk_space_limit_percentage=90

    [groups]
    personal=me
    movies_group=-1001234567890
    ```

   **Significato parametri:**
   - `api_id`, `api_hash`, `phone`: Credenziali Telegram e numero di telefono per il login.
   - `download_folder`: Dove vengono salvati i video inizialmente.
   - `completed_folder`: Dove vengono spostati i video dopo il download.
   - `min_valid_file_size_mb`: Dimensione minima (MB) per considerare valido un file.
   - `session_name`: Nome del file di sessione Telethon.
   - `max_simultaneous_file_to_download`: Max download in parallelo (intero).
   - `max_download_size_request_limit_kb`: Limite dimensione richiesta download (KB).
   - `enable_video_compression`: 0 = disattiva, 1 = attiva (beta).
   - `compression_ratio`: Rapporto di compressione video (1-100).
   - `disk_space_limit_percentage`: Percentuale max di utilizzo disco per i download.
   - `[groups]`: Mappa una chiave a un ID di canale/gruppo Telegram o "me" per "Messaggi Salvati".

## Uso

1. Assicurati di aver creato e configurato `tg-config.txt` come sopra.
2. Esegui lo script (file di configurazione predefinito):
    ```bash
    python run.py
    ```
3. Per usare un file di configurazione diverso:
    ```bash
    python run.py tg-config-2.txt
    ```

## Note

- I video vengono salvati nella cartella download e poi spostati in quella di completamento.
- Se un messaggio non contiene testo, lo script tenta di usare il messaggio successivo per il nome file.
- Supporta la validazione configurabile della dimensione minima: i file sotto soglia vengono riscaricati.
- Supporta il resume di download interrotti.
- Per usare un file di config diverso, specifica il nome come argomento (`python run.py custom-config.txt`).
- La barra di progresso mostra la percentuale di download.
- Elenco completo comandi e regole: [Comandi](/README-commands.md), [Regole](/README-rules.md).
- **Sicurezza:** Le credenziali Telegram sono richieste ma non vengono condivise o caricate online.

## Readme utili
- [Comandi](/README-commands.md)
- [Regole](/README-rules.md)

## Licenza
Distribuito con licenza [MIT](https://opensource.org/licenses/MIT).
