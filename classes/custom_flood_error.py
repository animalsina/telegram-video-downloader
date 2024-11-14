"""
CustomFloodError class

"""
class CustomFloodError(Exception):
    """
    CustomFloodError class
    """
    def __init__(self, message, *args):
        """
        Initialize the CustomFloodError
        """
        super().__init__(message, *args)
        self.message = message

    def __str__(self):
        """
        Return the string representation of the CustomFloodError
        """
        return f"CustomFloodError: {self.message}"
