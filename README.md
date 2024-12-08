# Telegram Video Downloader v2.4.0


# == ENG

## Description
This Python script uses the [Telethon](https://github.com/LonamiWebs/Telethon) library to download videos from Telegram's "Saved Messages" and manage their download and relocation status. If the message containing the video lacks a name, the script will look for a name in the subsequent message. Additionally, the script handles folder permissions and uses a lock file to prevent simultaneous executions. The script now includes configurable options for file validation based on size, improved progress reporting, support for resuming interrupted downloads, and the ability to use a custom configuration file.

## Requirements
- Python 3.9 or higher

## Useful Readme
- [Commands](/README-commands.md)
- [Rules](/README-rules.md)

## Installation
1. Clone this repository:
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. Create an account and get the data to add to the config file: [Link MyTelegram App](https://my.telegram.org/apps)

3. Create a configuration file `tg-config.txt` with the following information:
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

    [groups]
    # Key = ChannelID
    personal=me
    ```

   Example configuration:
    ```ini
    [telegram]
    api_id=120398
    api_hash=123098104981209481
    phone=123123123
    download_folder=tg-video
    completed_folder=tg-video-completed
    session_name=session_name
    max_simultaneous_file_to_download=1
    max_download_size_request_limit_kb=8388608

    [groups]
    # Key = ChannelID
    personal=me
    ```

   - `api_id`: Your Telegram API ID.
   - `api_hash`: Your Telegram API Hash.
   - `phone`: Your phone number used for Telegram login.
   - `download_folder`: The folder where videos will be initially saved.
   - `completed_folder`: The folder where videos will be moved after successful download.
   - `min_valid_file_size_mb`: The minimum file size in megabytes to consider a file valid. Files smaller than this size will be considered corrupted and re-downloaded.
   - `session_name`: The name of the session file used for Telegram login.
   - `max_simultaneous_file_to_download`: The maximum number of files to download simultaneously.
   - `max_download_size_request_limit_kb`: The maximum limit size in kilobytes for the download request.

## Usage
1. Ensure you have created and configured the `tg-config.txt` file as described above. [Link MyTelegram App](https://my.telegram.org/apps)
2. Run the script with the default configuration file:
    ```bash
    python run.py
    ```
3. To use a custom configuration file, pass the filename as a parameter:
    ```bash
    python run.py tg-config-2.txt
    ```

## Notes
- Videos are saved in the specified folder and moved to a completion folder once successfully downloaded.
- If a message does not contain text, the script will attempt to get a name from the next message.
- The script supports configurable minimum file size validation. Files smaller than the configured size will be flagged as corrupted and re-downloaded.
- The script includes support for resuming interrupted downloads, ensuring that partial downloads can continue from where they left off.
- To use a different configuration file, provide the filename as a parameter when running the script. If no parameter is given, `tg-config.txt` is used by default.
- Progress updates are provided during downloads, showing the percentage of completion.

## License
Distributed under the [MIT License](https://opensource.org/licenses/MIT).

# == ITA

## Descrizione
Questo script Python utilizza la libreria [Telethon](https://github.com/LonamiWebs/Telethon) per scaricare video dai "Messaggi Salvati" di Telegram e gestire il loro stato di download e spostamento. Se il messaggio contenente il video non ha un nome, lo script cerca un nome nel messaggio successivo. Inoltre, lo script gestisce i permessi delle cartelle e utilizza un file di lock per prevenire esecuzioni simultanee. Lo script ora include opzioni configurabili per la validazione dei file basata sulla dimensione, un miglioramento nella segnalazione del progresso, il supporto per il resume dei download interrotti e la possibilità di utilizzare un file di configurazione personalizzato.

## Requisiti
- Python 3.9 o superiore

## Readme utili
- [Comandi](/README-commands.md)
- [Regole](/README-rules.md)

## Installazione
1. Clona questo repository:
    ```bash
    git clone https://github.com/animalsina/telegram-video-downloader.git
    cd telegram-video-downloader
    ```

2. Crea un account e recupera i dati da aggiungere nel file config: [Link MyTelegram App](https://my.telegram.org/apps)

3. Crea un file di configurazione `tg-config.txt` con le seguenti informazioni:
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

    [groups]
    # Key = ChannelID
    personal=me
    ```

   Esempio di configurazione:
    ```ini
    [telegram]
    api_id=120398
    api_hash=123098104981209481
    phone=123123123
    download_folder=tg-video
    completed_folder=tg-video-completed
    session_name=session_name
    max_simultaneous_file_to_download=1
    max_download_size_request_limit_kb=8388608

    [groups]
    # Key = ChannelID
    personal=me
    ```

   - `api_id`: Il tuo ID API di Telegram.
   - `api_hash`: Il tuo Hash API di Telegram.
   - `phone`: Il tuo numero di telefono utilizzato per il login su Telegram.
   - `download_folder`: La cartella in cui i video saranno inizialmente salvati.
   - `completed_folder`: La cartella in cui i video saranno spostati dopo il download riuscito.
   - `min_valid_file_size_mb`: La dimensione minima del file in megabyte per considerare valido un file. I file più piccoli di questa dimensione saranno considerati corrotti e riscaricati.
   - `session_name`: Il nome del file di sessione utilizzato per il login su Telegram.
   - `max_simultaneous_file_to_download`: Il numero massimo di file da scaricare simultaneamente.
   - `max_download_size_request_limit_kb`: La dimensione massima per una richiesta di download in kilobytes.

## Uso
1. Assicurati di aver creato e configurato il file `tg-config.txt` come descritto sopra. [Link MyTelegram App](https://my.telegram.org/apps)
2. Esegui lo script con il file di configurazione predefinito:
    ```bash
    python run.py
    ```
3. Per utilizzare un file di configurazione personalizzato, passa il nome del file come parametro:
    ```bash
    python run.py tg-config-2.txt
    ```

## Note
- I video vengono salvati nella cartella specificata e spostati in una cartella di completamento una volta scaricati con successo.
- Se un messaggio non contiene testo, lo script tenterà di ottenere un nome dal messaggio successivo.
- Lo script supporta la validazione della dimensione minima del file configurabile. I file più piccoli della dimensione configurata saranno considerati corrotti e riscaricati.
- Lo script include ora il supporto per il resume dei download interrotti, garantendo che i download parziali possano continuare da dove erano stati interrotti.
- Per utilizzare un file di configurazione diverso, fornisci il nome del file come parametro durante l'esecuzione dello script. Se non viene fornito alcun parametro, verrà utilizzato `tg-config.txt` come predefinito.
- Durante i download vengono forniti aggiornamenti sul progresso, mostrando la percentuale di completamento.

## Licenza
Distribuito con licenza [MIT](https://opensource.org/licenses/MIT).
