class EIPNoCommandError(Exception):
    pass


class ConnectionError(Exception):
    """
    generic connection error
    """
    pass


class EIPClientError(Exception):
    """
    base EIPClient exception
    """
    def __str__(self):
        if len(self.args) >= 1:
            return repr(self.args[0])
        else:
            return ConnectionError


class UnrecoverableError(EIPClientError):
    """
    we cannot do anything about it, sorry
    """
    # XXX we should catch this and raise
    # to qtland, so we emit signal
    # to translate whatever kind of error
    # to user-friendly msg in dialog.
    pass
