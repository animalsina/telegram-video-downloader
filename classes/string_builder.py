LINE_FOR_VIDEO_NAME = 1
LINE_FOR_FILE_NAME = 2
LINE_FOR_FILE_SIZE = 3
LINE_FOR_FILE_DIMENSION = 4
LINE_FOR_PINNED_VIDEO = 5
LINE_FOR_LABEL = 6
LINE_FOR_INFO_DATA = 7
LINE_FOR_SHOW_LAST_ERROR = 9

TYPE_ACQUIRED = '🟢'
TYPE_DELETED = '❌'
TYPE_COMPLETED = '✅'


class StringBuilder:
    def __init__(self, initial_text=None):
        self.lines = []
        if initial_text:
            self.add_text(initial_text)  # Aggiungi il testo iniziale se fornito

    def add_text(self, text):
        # Aggiunge un testo tutto in una volta, suddividendolo in righe
        self.lines = text.splitlines() + self.lines

    def edit_in_line(self, new_line, line_number):
        # Assicurati che ci siano abbastanza righe
        while len(self.lines) < line_number:
            self.lines.append("")

        # Modifica la linea specificata
        self.lines[line_number - 1] = new_line

    def define_label(self, label_type):
        self.edit_in_line(label_type, LINE_FOR_LABEL)

    def get_label(self):
        return self.get_line(LINE_FOR_LABEL)

    def is_label(self, label_type):
        return self.get_label() == label_type

    def get_line(self, line_number):
        lines = self.string.splitlines()
        # Controlla se la riga esiste, altrimenti restituisci una stringa vuota
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        else:
            return ""

    @property
    def string(self):
        return "\n".join(self.lines)