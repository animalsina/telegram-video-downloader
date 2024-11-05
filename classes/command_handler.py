"""
CommandHandler
"""
import inspect
import re

COMMAND_PREFIX = "."  # prefisso dei comandi

class CommandHandler:
    """
    CommandHandler
    """
    def __init__(self):
        self.commands = {}

    def add_command(self, command, callback, args=None):
        """Aggiungi un comando all'elenco dei comandi."""
        command_with_prefix = f'{COMMAND_PREFIX}{command}'
        self.commands[command_with_prefix] = {'callback': callback, 'args': args}

    def list_commands(self):
        """Restituisce l'elenco dei comandi disponibili."""
        return list(self.commands.keys())

    async def detect_and_execute(self, text, extra_args=None):
        """Esegue il comando se presente nel testo."""
        for command, details in self.commands.items():
            match = re.match(rf"^{re.escape(command)}\s*(.*)$", text)
            if match:
                args = match.group(1).strip() if match.group(1) else ""

                # Unisci args e extra_args se esistono
                if extra_args:
                    combined_args = f"{args} {extra_args}".strip()
                else:
                    combined_args = args

                callback = details['callback']
                num_params = len(inspect.signature(callback).parameters)

                # Chiama il callback con o senza argomenti, a seconda di quanti ne accetta
                if num_params == 0:
                    await callback()  # Senza argomenti
                else:
                    await callback(combined_args)  # Con argomenti
                return True
        return False
