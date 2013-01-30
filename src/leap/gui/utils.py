"""
utility functions to work with gui objects
"""
from PyQt4 import QtCore


def layout_widgets(layout):
    """
    return a generator with all widgets in a layout
    """
    return (layout.itemAt(i) for i in range(layout.count()))


DELAY_MSECS = 50


def delay(obj, method_str=None, call_args=None):
    """
    Triggers a function or slot with a small delay.
    this is a mainly a hack to get responsiveness in the ui
    in cases in which the event loop freezes and the task
    is not heavy enough to setup a processing queue.
    """
    if callable(obj) and not method_str:
        fun = lambda: obj()

    if method_str:
        invoke = QtCore.QMetaObject.invokeMethod
        if call_args:
            fun = lambda: invoke(obj, method_str, call_args)
        else:
            fun = lambda: invoke(obj, method_str)

    QtCore.QTimer().singleShot(DELAY_MSECS, fun)
