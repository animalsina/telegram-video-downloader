# == ENG

## Rules

All rules are saved in the `rules` folder.

Rules are information passed during file movement or in certain specific situations to indicate how the program should behave.

You can find an example rule in [hello-world.rule](/rules/hello-world.rule).

The available commands are as follows:
- `set:chat:id` - Chat ID
- `set:chat:title` - Chat title
- `set:chat:name` - Chat name or username


- `use:message:filename` - Use the file name


- `on:message:pattern` - Regex pattern
- `action:message:translate` - Use the regex response to create the new name


- `on:folder:pattern` - Folder regex pattern
- `action:folder:completed` - Custom destination folder, depends on the folder pattern

### Details

`on:message:pattern` and `action:message:translate` must be placed in succession and can only be used once per rule.

`on:folder:pattern` and `action:folder:completed` must be placed in succession and can only be used once per rule.

The following commands can be omitted from the rule:
`on:folder:pattern` - If the pattern is missing, the message pattern will be used.
`set:chat:id`, `set:chat:title`, and `set:chat:name` - You can use one or all three. However, for username and ID, these are unique data, and ambiguity is unlikely. Using all three might be counterproductive.

`use:message:filename` - Can be omitted, and will not force the use of the filename instead of the name for the rule.


#### File Management

With `on:message:pattern`, you can create a pattern for a text, allowing you to have many videos to download with names like "2024-04-01 Video Festa", and obviously different dates for each video. You can create a regex like:
`^(\d{4}-\d{2}-\d{2})\s+Video\s(.+)$`, which will allow you to capture the date and the text after "Video".
Then, adding something like `{3} in date {2}/{1}/{0}` to `action:message:translate` will give you a name like "Festa in data 01/04/2024" for all files, where the date and name after "Video" are inserted based on the filename.

For videos, the main name is retrieved from the caption associated with the video:

================== \
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
Video \
================== \
Caption

---
#### Folder Management

If the name is not present, the name captured is the file name, but if even this is missing, no name will be added, and the video will not be captured. In this case, you can associate a name by responding to the video with a title. \
However, there should always be a name.

If the destination folder is different, and we want to make it dynamic, we will use: \
`on:folder:pattern` and `action:folder:completed` \

This time, we need to know that the folder will be based on the name already assigned to the file, so what is translated by `action:message:translate` (if present), otherwise, it will translate the original filename. \

In `action:folder:completed`, the folder should be described differently from the file name; values will be assigned by using, for example, #0, #1, #2.

Example using the previously translated name:
`on:folder:pattern="(\d{2}/\d{2}/\d{4})"` and adding `action:folder:completed="#0_#1_#2"` will result in a destination folder like:
`"./02_04_2024/<filename>"`, which will organize all files into a folder with the same date, or you can just specify the year and include all videos in the 2024 folder. Note that the completion folder name may have a relative path starting from the project root or an absolute path starting from your machine's root.

---

#### Chat and Priority Management

`set:chat:id`, `set:chat:title`, and `set:chat:name` allow you to localize the rule for a specific chat. 
For example, if the videos come from a chat other than the personal one, we can recognize the chat by its title, username, or ID if we have it. This allows us to isolate the rule so that it doesn't conflict with others. Furthermore, rules that have one of these 3 elements active are prioritized over others.

---

#### Use filename

`use:message:filename` is a "True" or "False" directive that forces the retrieval of the video title from its filename.

Note: The filename is not always present in the message, and if it's not, the video name associated with the caption will still be retrieved if available.

---

## Keep in mind:

All rules requiring regex can be tested via various online tools, and you should be cautious when using them to avoid undesirable situations.

Feel free to check out: [Wiki](https://en.wikipedia.org/wiki/Regular_expression)

---

# == ITA

## Regole

Tutte le regole vengono salvate nella cartella `rules`

Le regole sono delle informazioni che vengono passate durante lo spostamendo del file o in alcune situazioni particolari
per indicare come deve comportarsi il programma.

E' possibile trovare una regola d'esempio su [hello-world.rule](/rules/hello-world.rule)

I comandi disponibili sono i seguenti:
- `on:message:pattern` - Pattern in regex
- `set:chat:id` - ID chat
- `set:chat:title` - Titolo chat
- `set:chat:name` - Nome o username chat
- `use:message:filename` - Utilizza il nome del file
- `on:folder:pattern` - regex cartella
- `action:message:translate` - Utilizza la risposta di regex per creare il nuovo nome
- `action:folder:completed` - Cartella di destinazione personalizzata, dipende dal folder pattern

### Dettagli

`on:message:pattern` e `action:message:translate` vanno messi in successione e possono essere utilizzati solo una volta per regola.

`on:folder:pattern` e `action:folder:completed`  vanno messi in successione e possono essere utilizzati solo una volta per regola.

Possono essere omessi i seguenti comandi dalla regola:
`on:folder:pattern` - Se manca il pattern utilizzato è quello del message
`set:chat:id`, `set:chat:title` e `set:chat:name` - E' possibile utilizzarne una sola o tutte e tre, ma tendenzialmente
per username e id si tratta di un dato univoco dove non è quindi possibile trovare ambiguità, quindi utilizzarle tutte e tre potrebbe essere controproducente.

`use:message:filename` - Può essere omesso, e non forzerà l'utilizzo del filename invece che il nome per la regola.


#### Gestione file

Con `on:message:pattern` è possibile creare un pattern per un testo, ammettendo quindi di avere tanti video da scaricare
con nome "2024-04-01 Video Festa" e ovviamente diverse date per ogni video, possiamo creare un regex di questo tipo:
`^(\d{4}-\d{2}-\d{2})\s+Video\s(.+)$`, questo mi permetterà di avere come valori la data e il testo dopo Video,
A questo punto aggiungendo a `action:message:translate` qualcosa del tipo "{3} in data {2}/{1}/{0}" otterrò un nome che sarà
"Festa in data 01/04/2024" per tutti i file, dove la data e il nome dopo "Video" saranno inseriti sulla base del nome.

Dai video il nome principale viene recuperato dal nome del caption associato al video:

================== \
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
Video \
================== \
Caption

---
#### Gestione Cartelle

Nel caso il nome non fosse presente, il nome che viene catturato è quello del file, ma se anche questo
non fosse presente, non verrà aggiunto alcun nome e il video non verrà catturato, in quel caso è possibile
associare un nome rispondendo al video con un titolo. \
Tendenzialmente comunque dovrebbe sempre esserci un nome.

Se la cartella di destinazione è diversa, ad esempio vogliamo rendere dinamica anche quella, utilizzeremo: \
`on:folder:pattern` e `action:folder:completed` \

questa volta però dobbiamo sapere che la cartella si baserà sul nome già assegnato al file, quindi quello che viene tradotto
da `action:message:translate` se presente, altrimenti tradurrà il nome originale del file. \

In `action:folder:completed` la cartella deve essere descritta diversamente rispetto al nome del file,
i valori verranno assegnati mettendo ad esempio #0, #1, #2

Esempio prendendo come riferimento il nome già tradotto precedentemente:
`on:folder:pattern="(\d{2}/\d{2}/\d{4})"` aggiungerò `action:folder:completed="#0_#1_#2"` per ottenere una cartella di destinazione
"./02_04_2024/<nome_file>" in questo modo ordinerai tutti i file all'interno di una cartella con la stessa data, oppure
indichi solo l'anno e verranno inclusi tutti i video all'interno della cartella 2024, attenzione che il nome della cartella di completamento
puà avere path relativa che parte dalla root del progetto, oppure assoluta che parte dal root della tua macchina.

---

#### Gestione Chat e priorità

`set:chat:id`, `set:chat:title` e `set:chat:name` permettono di localizzare la regola solo per una chat specifica
ad esempio, se i video provengono da una chat diversa da quella personale ad esempio, possiamo riconoscere la chat
dal suo titolo, dal suo username o dal suo id se ne siamo in possesso, questo ci permette di isolare la regola
in modo che non vada in conflitto con le altre, inoltre le regole che hanno uno di questi 3 elementi attivi
viene messa in cima rispetto alle altre.

---

#### Use filename

`use:message:filename` è una direttiva "True" o "False" che permette di forzare il recupero del titolo del video dal suo nome file.

Attenzione: non sempre è presente nel messaggio il nome del file, e se questo non è presente verrà comunque recuperato il nome
del video associato ad esempio come caption se presente.

---

## Tenere bene a mente che:

Tutte le regole che richiedono regex possono essere testate tramite i vari siti presenti in giro, e si deve fare attenzione
nell'utilizzarle per evitare situazioni spiacevoli.

Informatevi pure: [Wiki](https://it.wikipedia.org/wiki/Espressione_regolare)