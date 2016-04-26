class SRPAuthenticationError(Exception):
    """
    Exception raised for authentication errors
    """
    pass


class SRPAuthConnectionError(SRPAuthenticationError):
    """
    Exception raised when there's a connection error
    """
    pass


class SRPAuthBadStatusCode(SRPAuthenticationError):
    """
    Exception raised when we received an unknown bad status code
    """
    pass


class SRPAuthNoSalt(SRPAuthenticationError):
    """
    Exception raised when we don't receive the salt param at a
    specific point in the auth process
    """
    pass


class SRPAuthNoB(SRPAuthenticationError):
    """
    Exception raised when we don't receive the B param at a specific
    point in the auth process
    """
    pass


class SRPAuthBadDataFromServer(SRPAuthenticationError):
    """
    Generic exception when we receive bad data from the server.
    """
    pass


class SRPAuthBadUserOrPassword(SRPAuthenticationError):
    """
    Exception raised when the user provided a bad password to auth.
    """
    pass


class SRPAuthVerificationFailed(SRPAuthenticationError):
    """
    Exception raised when we can't verify the SRP data received from
    the server.
    """
    pass


class SRPAuthNoSessionId(SRPAuthenticationError):
    """
    Exception raised when we don't receive a session id from the
    server.
    """
    pass
