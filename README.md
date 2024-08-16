# == ENG
# Telegram Video Downloader

## Description
This Python script uses the [Telethon](https://github.com/LonamiWebs/Telethon) library to download videos from Telegram's "Saved Messages" and manage their download and relocation status. If the message containing the video lacks a name, the script will look for a name in the subsequent message. Additionally, the script handles folder permissions and uses a lock file to prevent simultaneous executions. The script now includes configurable options for file validation based on size and improved progress reporting.

## Requirements
- Python 3.7 or higher
- Telethon
- tqdm

## Installation
1. Clone this repository:
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. Install dependencies:
    ```bash
    pip install telethon tqdm
    ```

3. Create an account and get the data to add to the config file: [Link MyTelegram App](https://my.telegram.org/apps) 

4. Create a configuration file `tg-config.txt` with the following information:
    ```txt
    api_id=YOUR_API_ID
    api_hash=YOUR_API_HASH
    phone=YOUR_PHONE_NUMBER
    download_folder=YOUR_DOWNLOAD_FOLDER
    completed_folder=YOUR_COMPLETED_FOLDER
    check_file=YOUR_CHECK_FILE
    min_valid_file_size_mb=10
    session_name=YOUR_SESSION_NAME
    ```

    - `api_id`: Your Telegram API ID.
    - `api_hash`: Your Telegram API Hash.
    - `phone`: Your phone number used for Telegram login.
    - `download_folder`: The folder where videos will be initially saved.
    - `completed_folder`: The folder where videos will be moved after successful download.
    - `check_file`: The file used to keep track of downloaded videos.
    - `min_valid_file_size_mb`: The minimum file size in megabytes to consider a file valid. Files smaller than this size will be considered corrupted and re-downloaded.
    - `session_name`: The name of the session file used for Telegram login.

## Usage
1. Ensure you have created and configured the `tg-config.txt` file as described above. [Link MyTelegram App](https://my.telegram.org/apps)
2. Run the script:
    ```bash
    python run.py
    ```

## Notes
- The script downloads videos only from "Saved Messages".
- Videos are saved in the specified folder and moved to a completion folder once successfully downloaded.
- If a message does not contain text, the script will attempt to get a name from the next message.
- The script now supports configurable minimum file size validation. Files smaller than the configured size will be flagged as corrupted and re-downloaded.
- Progress updates are provided during downloads, showing the percentage of completion.

## License
Distributed under the [MIT License](https://opensource.org/licenses/MIT).

# == ITA
# Telegram Video Downloader

## Descrizione
Questo script Python utilizza la libreria [Telethon](https://github.com/LonamiWebs/Telethon) per scaricare video dai "Messaggi Salvati" di Telegram e gestire il loro stato di download e spostamento. Se il messaggio contenente il video non ha un nome, lo script cerca un nome nel messaggio successivo. Inoltre, lo script gestisce i permessi delle cartelle e utilizza un file di lock per prevenire esecuzioni simultanee. Lo script ora include opzioni configurabili per la validazione dei file basata sulla dimensione e un miglioramento nella segnalazione del progresso.

## Requisiti
- Python 3.7 o superiore
- Telethon
- tqdm

## Installazione
1. Clona questo repository:
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. Installa le dipendenze:
    ```bash
    pip install telethon tqdm
    ```

3. Crea un account e recupera i dati da aggiungere nel file config: [Link MyTelegram App](https://my.telegram.org/apps) 

4. Crea un file di configurazione `tg-config.txt` con le seguenti informazioni:
    ```txt
    api_id=YOUR_API_ID
    api_hash=YOUR_API_HASH
    phone=YOUR_PHONE_NUMBER
    download_folder=YOUR_DOWNLOAD_FOLDER
    completed_folder=YOUR_COMPLETED_FOLDER
    check_file=YOUR_CHECK_FILE
    min_valid_file_size_mb=10
    session_name=YOUR_SESSION_NAME
    ```

    - `api_id`: Il tuo ID API di Telegram.
    - `api_hash`: Il tuo Hash API di Telegram.
    - `phone`: Il tuo numero di telefono utilizzato per il login su Telegram.
    - `download_folder`: La cartella in cui i video saranno inizialmente salvati.
    - `completed_folder`: La cartella in cui i video saranno spostati dopo il download riuscito.
    - `check_file`: Il file usato per tenere traccia dei video scaricati.
    - `min_valid_file_size_mb`: La dimensione minima del file in megabyte per considerare valido un file. I file più piccoli di questa dimensione saranno considerati corrotti e riscaricati.
    - `session_name`: Il nome del file di sessione utilizzato per il login su Telegram.

## Uso
1. Assicurati di aver creato e configurato il file `tg-config.txt` come descritto sopra. [Link MyTelegram App](https://my.telegram.org/apps)
2. Esegui lo script:
    ```bash
    python run.py
    ```

## Note
- Lo script scarica video solo dai "Messaggi Salvati".
- I video vengono salvati nella cartella specificata e spostati in una cartella di completamento una volta scaricati con successo.
- Se un messaggio non contiene testo, lo script tenterà di ottenere un nome dal messaggio successivo.
- Lo script ora supporta la validazione della dimensione minima del file configurabile. I file più piccoli della dimensione configurata saranno considerati corrotti e riscaricati.
- Durante i download vengono forniti aggiornamenti sul progresso, mostrando la percentuale di completamento.

## Licenza
Distribuito con licenza [MIT](https://opensource.org/licenses/MIT).

