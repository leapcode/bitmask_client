from PyQt4 import QtCore


class FunThread(QtCore.QThread):

    def __init__(self, fun, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.fun = fun

    def run(self):
        if self.fun:
            self.fun()

    def begin(self):
        self.start()
