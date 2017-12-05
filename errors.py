class Error(Exception):
    """Base class for GhoST exceptions."""
    pass

class CommandError(Error):
    """Exception raised whenever there is an issue running a command via subprocess

    Attributes:
        message -- explanation of the error. Typically this is just the stderr output
    """

    def __init__(self, message):
        self.message = message

