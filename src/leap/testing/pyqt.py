from PyQt4 import QtCore

_oldConnect = QtCore.QObject.connect
_oldDisconnect = QtCore.QObject.disconnect
_oldEmit = QtCore.QObject.emit


def _wrapConnect(callableObject):
    """
    Returns a wrapped call to the old version of QtCore.QObject.connect
    """
    @staticmethod
    def call(*args):
        callableObject(*args)
        _oldConnect(*args)
    return call


def _wrapDisconnect(callableObject):
    """
    Returns a wrapped call to the old version of QtCore.QObject.disconnect
    """
    @staticmethod
    def call(*args):
        callableObject(*args)
        _oldDisconnect(*args)
    return call


def enableSignalDebugging(**kwargs):
    """
    Call this to enable Qt Signal debugging. This will trap all
    connect, and disconnect calls.
    """

    f = lambda *args: None
    connectCall = kwargs.get('connectCall', f)
    disconnectCall = kwargs.get('disconnectCall', f)
    emitCall = kwargs.get('emitCall', f)

    def printIt(msg):
        def call(*args):
            print msg, args
        return call
    QtCore.QObject.connect = _wrapConnect(connectCall)
    QtCore.QObject.disconnect = _wrapDisconnect(disconnectCall)

    def new_emit(self, *args):
        emitCall(self, *args)
        _oldEmit(self, *args)

    QtCore.QObject.emit = new_emit
