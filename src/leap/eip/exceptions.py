class EIPClientError(Exception):
    """
    base EIPClient exception
    """
    # Should inherit from LeapException
    # and move basic attrs there
    critical = False

    #def __str__(self):
        #if len(self.args) >= 1:
            #return repr(self.args[0])
        #else:
            #return ConnectionError


class CriticalError(EIPClientError):
    """
    we cannot do anything about it, sorry
    """
    critical = True


class EIPNoPolkitAuthAgentAvailable(CriticalError):
    message = "No polkit authentication agent could be found"
    usermessage = ("We could not find any authentication "
                   "agent in your system.<br/>"
                   "Make sure you have "
                   "<b>polkit-gnome-authentication-agent-1</b> "
                   "running and try again.")

# Errors needing some work


class EIPNoPkexecAvailable(Exception):
    pass


class EIPInitNoProviderError(Exception):
    pass


class EIPInitBadProviderError(Exception):
    pass


class EIPInitNoKeyFileError(Exception):
    pass


class EIPInitBadKeyFilePermError(Exception):
    pass


class EIPNoCommandError(Exception):
    pass

# Errors that probably we don't need anymore


class MissingSocketError(Exception):
    pass


class ConnectionRefusedError(Exception):
    pass




class EIPMissingDefaultProvider(Exception):
    pass


class EIPConfigurationError(Exception):
    pass
