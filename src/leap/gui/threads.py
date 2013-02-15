from PyQt4 import QtCore


class FunThread(QtCore.QThread):

    def __init__(self, fun=None, parent=None):

        QtCore.QThread.__init__(self, parent)
        self.exiting = False
        self.fun = fun

    def __del__(self):
        self.exiting = True
        self.wait()

    def run(self):
        if self.fun:
            self.fun()

    def begin(self):
        self.start()
