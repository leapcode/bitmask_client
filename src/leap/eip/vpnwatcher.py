"""generic watcher object that keeps track of connection status"""
# This should be deprecated in favor of daemon mode + management
# interface. But we can leave it here for debug purposes.


class EIPConnectionStatus(object):
    """
    Keep track of client (gui) and openvpn
    states.

    These are the OpenVPN states:
    CONNECTING    -- OpenVPN's initial state.
    WAIT          -- (Client only) Waiting for initial response
                     from server.
    AUTH          -- (Client only) Authenticating with server.
    GET_CONFIG    -- (Client only) Downloading configuration options
                     from server.
    ASSIGN_IP     -- Assigning IP address to virtual network
                     interface.
    ADD_ROUTES    -- Adding routes to system.
    CONNECTED     -- Initialization Sequence Completed.
    RECONNECTING  -- A restart has occurred.
    EXITING       -- A graceful exit is in progress.

    We add some extra states:

    DISCONNECTED  -- GUI initial state.
    UNRECOVERABLE -- An unrecoverable error has been raised
                     while invoking openvpn service.
    """
    CONNECTING = 1
    WAIT = 2
    AUTH = 3
    GET_CONFIG = 4
    ASSIGN_IP = 5
    ADD_ROUTES = 6
    CONNECTED = 7
    RECONNECTING = 8
    EXITING = 9

    # gui specific states:
    UNRECOVERABLE = 11
    DISCONNECTED = 0

    def __init__(self, callbacks=None):
        """
        EIPConnectionStatus is initialized with a tuple
        of signals to be triggered.
        :param callbacks: a tuple of (callable) observers
        :type callbacks: tuple
        """
        # (callbacks to connect to signals in Qt-land)
        self.current = self.DISCONNECTED
        self.previous = None
        self.callbacks = callbacks

    def get_readable_status(self):
        # XXX DRY status / labels a little bit.
        # think we'll want to i18n this.
        human_status = {
            0: 'disconnected',
            1: 'connecting',
            2: 'waiting',
            3: 'authenticating',
            4: 'getting config',
            5: 'assigning ip',
            6: 'adding routes',
            7: 'connected',
            8: 'reconnecting',
            9: 'exiting',
            11: 'unrecoverable error',
        }
        return human_status[self.current]

    def get_state_icon(self):
        """
        returns the high level icon
        for each fine-grain openvpn state
        """
        connecting = (self.CONNECTING,
                      self.WAIT,
                      self.AUTH,
                      self.GET_CONFIG,
                      self.ASSIGN_IP,
                      self.ADD_ROUTES)
        connected = (self.CONNECTED,)
        disconnected = (self.DISCONNECTED,
                        self.UNRECOVERABLE)

        # this can be made smarter,
        # but it's like it'll change,
        # so +readability.

        if self.current in connecting:
            return "connecting"
        if self.current in connected:
            return "connected"
        if self.current in disconnected:
            return "disconnected"

    def set_vpn_state(self, status):
        """
        accepts a state string from the management
        interface, and sets the internal state.
        :param status: openvpn STATE (uppercase).
        :type status: str
        """
        if hasattr(self, status):
            self.change_to(getattr(self, status))

    def set_current(self, to):
        """
        setter for the 'current' property
        :param to: destination state
        :type to: int
        """
        self.current = to

    def change_to(self, to):
        """
        :param to: destination state
        :type to: int
        """
        if to == self.current:
            return
        changed = False
        from_ = self.current
        self.current = to

        # We can add transition restrictions
        # here to ensure no transitions are
        # allowed outside the fsm.

        self.set_current(to)
        changed = True

        #trigger signals (as callbacks)
        #print('current state: %s' % self.current)
        if changed:
            self.previous = from_
            if self.callbacks:
                for cb in self.callbacks:
                    if callable(cb):
                        cb(self)


def status_watcher(cs, line):
    """
    a wrapper that calls to ConnectionStatus object
    :param cs: a EIPConnectionStatus instance
    :type cs: EIPConnectionStatus object
    :param line: a single line of the watched output
    :type line: str
    """
    #print('status watcher watching')

    # from the mullvad code, should watch for
    # things like:
    # "Initialization Sequence Completed"
    # "With Errors"
    # "Tap-Win32"

    if "Completed" in line:
        cs.change_to(cs.CONNECTED)
        return

    if "Initial packet from" in line:
        cs.change_to(cs.CONNECTING)
        return
