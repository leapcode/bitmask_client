"""
Exception attributes and their meaning/uses
-------------------------------------------

* critical:    if True, will abort execution prematurely,
               after attempting any cleaning
               action.

* failfirst:   breaks any error_check loop that is examining
               the error queue.

* message:     the message that will be used in the __repr__ of the exception.

* usermessage: the message that will be passed to user in ErrorDialogs
               in Qt-land.
"""
from leap.util.translations import translate


class LeapException(Exception):
    """
    base LeapClient exception
    sets some parameters that we will check
    during error checking routines
    """

    critical = False
    failfirst = False
    warning = False


class CriticalError(LeapException):
    """
    we cannot do anything about it
    """
    critical = True
    failfirst = True


# In use ???
# don't thing so. purge if not...

class MissingConfigFileError(Exception):
    pass


class ImproperlyConfigured(Exception):
    pass


# NOTE: "Errors" (context) has to be a explicit string!


class InterfaceNotFoundError(LeapException):
    # XXX should take iface arg on init maybe?
    message = "interface not found"
    usermessage = translate(
        "Errors",
        "Interface not found")


class NoDefaultInterfaceFoundError(LeapException):
    message = "no default interface found"
    usermessage = translate(
        "Errors",
        "Looks like your computer "
        "is not connected to the internet")


class NoConnectionToGateway(CriticalError):
    message = "no connection to gateway"
    usermessage = translate(
        "Errors",
        "Looks like there are problems "
        "with your internet connection")


class NoInternetConnection(CriticalError):
    message = "No Internet connection found"
    usermessage = translate(
        "Errors",
        "It looks like there is no internet connection.")
    # and now we try to connect to our web to troubleshoot LOL :P


class CannotResolveDomainError(LeapException):
    message = "Cannot resolve domain"
    usermessage = translate(
        "Errors",
        "Domain cannot be found")


class TunnelNotDefaultRouteError(CriticalError):
    message = "Tunnel connection dissapeared. VPN down?"
    usermessage = translate(
        "Errors",
        "The Encrypted Connection was lost. Shutting down...")
