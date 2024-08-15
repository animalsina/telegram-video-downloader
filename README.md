# == ENG
# Telegram Video Downloader

## Description
This Python script uses the [Telethon](https://github.com/LonamiWebs/Telethon) library to download videos from Telegram's "Saved Messages" and manage their download and relocation status. If the message containing the video lacks a name, the script will look for a name in the subsequent message. Additionally, the script handles folder permissions and uses a lock file to prevent simultaneous executions.

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

3. Create an account and gets the data to add in the config file: [Link MyTelegram App](https://my.telegram.org/apps) 


4. Create a configuration file `tg-config.txt` with the following information:
    ```txt
    api_id=YOUR_API_ID
    api_hash=YOUR_API_HASH
    phone=YOUR_PHONE_NUMBER
    download_folder=YOUR_DOWNLOAD_FOLDER
    completed_folder=YOUR_COMPLETED_FOLDER
    check_file=YOUR_CHECK_FILE
    ```

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

## License
Distributed under the [MIT License](https://opensource.org/licenses/MIT).


# == ITA
# Telegram Video Downloader

## Descrizione
Questo script Python utilizza la libreria [Telethon](https://github.com/LonamiWebs/Telethon) per scaricare video dai "Messaggi Salvati" di Telegram e gestire il loro stato di download e spostamento. Se il messaggio contenente il video non ha un nome, lo script cerca un nome nel messaggio successivo. Inoltre, lo script gestisce i permessi delle cartelle e utilizza un file di lock per prevenire esecuzioni simultanee.

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
    ```

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

## Licenza
Distribuito con licenza [MIT](https://opensource.org/licenses/MIT).

