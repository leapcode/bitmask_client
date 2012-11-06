"""
classes used in progress pages
from first run wizard
"""
try:
    from collections import OrderedDict
except ImportError:
    # We must be in 2.6
    from leap.util.dicts import OrderedDict
#import time

from PyQt4 import QtCore
from PyQt4 import QtGui

from leap.baseapp.mainwindow import FunThread

from leap.gui import mainwindow_rc

CHECKMARK_IMG = ":/images/checked.png"


class ImgWidget(QtGui.QWidget):

    # XXX move to widgets

    def __init__(self, parent=None, img=None):
        super(ImgWidget, self).__init__(parent)
        self.pic = QtGui.QPixmap(img)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawPixmap(0, 0, self.pic)


class ProgressStep(object):
    """
    Data model for sequential steps
    to be used in a progress page in
    connection wizard
    """
    NAME = 0
    DONE = 1

    def __init__(self, stepname, done, index=None):
        """
        @param step: the name of  the step
        @type step: str
        @param done: whether is completed or not
        @type done: bool
        """
        self.index = int(index) if index else 0
        self.name = unicode(stepname)
        self.done = bool(done)

    @classmethod
    def columns(self):
        return ('name', 'done')


class ProgressStepContainer(object):
    """
    a container for ProgressSteps objects
    access data in the internal dict
    """

    def __init__(self):
        self.dirty = False
        self.steps = {}

    def step(self, identity):
        return self.step.get(identity)

    def addStep(self, step):
        self.steps[step.index] = step

    def removeStep(self, step):
        del self.steps[step.index]
        del step
        self.dirty = True

    def removeAllSteps(self):
        for item in iter(self):
            self.removeStep(item)

    @property
    def columns(self):
        return ProgressStep.columns()

    def __len__(self):
        return len(self.steps)

    def __iter__(self):
        for step in self.steps.values():
            yield step


class StepsTableWidget(QtGui.QTableWidget):
    """
    initializes a TableWidget
    suitable for our display purposes, like removing
    header info and grid display
    """

    def __init__(self, parent=None):
        super(StepsTableWidget, self).__init__(parent)

        # remove headers and all edit/select behavior
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(
            QtGui.QAbstractItemView.NoSelection)
        width = self.width()
        # WTF? Here init width is 100...
        # but on populating is 456... :(

        # XXX do we need this initial?
        print 'init table. width=%s' % width
        self.horizontalHeader().resizeSection(0, width * 0.7)

        # this disables the table grid.
        # we should add alignment to the ImgWidget (it's top-left now)
        self.setShowGrid(False)

        # XXX change image for done to rc

        # Note about the "done" status painting:
        #
        # XXX currently we are setting the CellWidget
        # for the whole table on a per-row basis
        # (on add_status_line method on ValidationPage).
        # However, a more generic solution might be
        # to implement a custom Delegate that overwrites
        # the paint method (so it paints a checked tickmark if
        # done is True and some other thing if checking or false).
        # What we have now is quick and works because
        # I'm supposing that on first fail we will
        # go back to previous wizard page to signal the failure.
        # A more generic solution could be used for
        # some failing tests if they are not critical.


class ValidationPage(QtGui.QWizardPage):
    """
    class to be used as an intermediate
    between two pages in a wizard.
    shows feedback to the user and goes back if errors,
    goes forward if ok.
    initializePage triggers a one shot timer
    that calls do_checks.
    Derived classes should implement
    _do_checks and
    _do_validation
    """

    # signals

    stepChanged = QtCore.pyqtSignal([str, int])

    def __init__(self, parent=None):
        super(ValidationPage, self).__init__(parent)

        self.steps = ProgressStepContainer()
        self.progress = QtGui.QProgressBar(self)

        # steps table widget
        self.stepsTableWidget = StepsTableWidget(self)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.progress)
        layout.addWidget(self.stepsTableWidget)

        self.setLayout(layout)
        self.layout = layout

        self.timer = QtCore.QTimer()

        # connect the new step status
        # signal to status handler
        self.stepChanged.connect(
            self.onStepStatusChanged)

        self.errors = OrderedDict()

    def populateStepsTable(self):
        # from examples,
        # but I guess it's not needed to re-populate
        # the whole table.
        table = self.stepsTableWidget
        table.setRowCount(len(self.steps))
        columns = self.steps.columns
        table.setColumnCount(len(columns))

        for row, step in enumerate(self.steps):
            item = QtGui.QTableWidgetItem(step.name)
            item.setData(QtCore.Qt.UserRole,
                         long(id(step)))
            table.setItem(row, columns.index('name'), item)
            table.setItem(row, columns.index('done'),
                          QtGui.QTableWidgetItem(step.done))
        self.resizeTable()
        self.update()

    def clearTable(self):
        # ??? -- not sure what's the difference
        #self.stepsTableWidget.clear()
        self.stepsTableWidget.clearContents()

    def resizeTable(self):
        # resize first column to ~80%
        table = self.stepsTableWidget
        FIRST_COLUMN_PERCENT = 0.75
        width = table.width()
        print 'populate table. width=%s' % width
        table.horizontalHeader().resizeSection(0, width * FIRST_COLUMN_PERCENT)

    def onStepStatusChanged(self, status, progress=None):
        if status not in ("head_sentinel", "end_sentinel"):
            self.add_status_line(status)
        if progress:
            self.progress.setValue(progress)
            self.progress.update()

    def add_status_line(self, message):
        print 'adding status line...'
        index = len(self.steps)
        step = ProgressStep(message, False, index=index)
        self.steps.addStep(step)
        self.populateStepsTable()
        table = self.stepsTableWidget

        # setting cell widget.
        # see note on StepsTableWidget about plans to
        # change this for a better solution.

        table.setCellWidget(
            index - 1,
            ProgressStep.DONE,
            ImgWidget(img=CHECKMARK_IMG))
        table.update()

    def go_back(self):
        self.wizard().back()

    def go_next(self):
        self.wizard().next()

    def initializePage(self):
        self.steps.removeAllSteps()
        self.clearTable()
        self.resizeTable()
        self.timer.singleShot(0, self.do_checks)

    def do_checks(self):
        """
        launches a thread to do the checks
        """
        signal = self.stepChanged
        self.checks = FunThread(
            self._do_checks(update_signal=signal))
        self.checks.finished.connect(self._do_validation)
        self.checks.begin()
        print 'check thread started!'
        print 'waiting for it to terminate...'
        self.checks.wait()
