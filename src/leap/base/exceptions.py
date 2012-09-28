class MissingConfigFileError(Exception):
    pass


class ImproperlyConfigured(Exception):
    pass


class NoDefaultInterfaceFoundError(Exception):
    message = "no default interface found"
    usermessage = "Looks like your computer is not connected to the internet"


class InterfaceNotFoundError(Exception):
    # XXX should take iface arg on init maybe?
    message = "interface not found"


class NoConnectionToGateway(Exception):
    message = "no connection to gateway"
    usermessage = "Looks like there are problems with your internet connection"


class NoInternetConnection(Exception):
    message = "No Internet connection found"


class TunnelNotDefaultRouteError(Exception):
    message = "VPN Maybe be down."
