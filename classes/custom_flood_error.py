"""
CustomFloodError class

"""
class CustomFloodError(Exception):
    """
    CustomFloodError class
    """
    def __init__(self, message="Too many requests, please try again later.", *args, **kwargs):
        # Chiamata al costruttore della classe base
        super().__init__(message, *args, **kwargs)
        self.message = message

    def __str__(self):
        # Rappresentazione dell'errore con il messaggio personalizzato
        return f"CustomFloodError: {self.message}"